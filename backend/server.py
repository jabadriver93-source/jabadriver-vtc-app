from fastapi import FastAPI, APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse, Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import io
import csv
import resend
import base64
from urllib.parse import quote
import re

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Resend setup
resend.api_key = os.environ.get('RESEND_API_KEY', '')
SENDER_EMAIL_NEW = os.environ.get('SENDER_EMAIL_NEW', 'JabaDriver <noreply@jabadriver.fr>')
SENDER_EMAIL = SENDER_EMAIL_NEW  # Utilise SENDER_EMAIL_NEW comme source
DRIVER_EMAIL = os.environ.get('DRIVER_EMAIL', '')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Stripe configuration
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY', '')

# Pricing configuration
AIRPORT_SURCHARGE = 10.0  # Supplément aéroport en euros

# Company info
COMPANY_INFO = {
    "name": "JABADRIVER",
    "legal_name": "JABADRIVER",
    "siret": "941 473 217 00011",
    "email": "contact@jabadriver.fr",
    "phone": "06 XX XX XX XX"
}

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Log email configuration at startup
logger.info("=" * 80)
logger.info("EMAIL CONFIGURATION:")
logger.info(f"  RESEND_API_KEY present: {bool(resend.api_key)}")
logger.info(f"  RESEND_API_KEY length: {len(resend.api_key) if resend.api_key else 0}")
logger.info(f"  SENDER_EMAIL: {SENDER_EMAIL}")
logger.info(f"  DRIVER_EMAIL: {DRIVER_EMAIL}")
logger.info("=" * 80)

# Booking delay configuration (hours)
MIN_BOOKING_DELAY_HOURS = 6

# Helper functions
def validate_booking_delay(date_str: str, time_str: str) -> tuple[bool, str]:
    """Validate that booking is at least MIN_BOOKING_DELAY_HOURS in advance"""
    try:
        booking_datetime = datetime.fromisoformat(f"{date_str}T{time_str}")
        min_booking_time = datetime.now() + timedelta(hours=MIN_BOOKING_DELAY_HOURS)
        
        if booking_datetime < min_booking_time:
            return False, f"Les réservations doivent être effectuées au minimum {MIN_BOOKING_DELAY_HOURS} heures à l'avance."
        return True, ""
    except Exception as e:
        logger.error(f"Error validating booking delay: {e}")
        return False, "Date ou heure invalide"

def detect_airport(address: str) -> bool:
    """Détecte si l'adresse contient un aéroport"""
    if not address:
        return False
    
    address_lower = address.lower()
    airport_keywords = [
        'aéroport', 'aeroport', 'airport',
        'cdg', 'charles de gaulle', 'charles-de-gaulle',
        'orly',
        'beauvais', 'tillé'
    ]
    
    return any(keyword in address_lower for keyword in airport_keywords)

def calculate_price_with_surcharge(estimated_price: float, pickup_address: str, dropoff_address: str, apply_surcharge: bool = True) -> dict:
    """Calcule le prix avec supplément aéroport si applicable"""
    base_price = estimated_price or 0.0
    airport_surcharge = 0.0
    is_airport_trip = False
    
    if apply_surcharge and (detect_airport(pickup_address) or detect_airport(dropoff_address)):
        is_airport_trip = True
        airport_surcharge = AIRPORT_SURCHARGE
    
    final_price = base_price + airport_surcharge
    
    return {
        'base_price': base_price,
        'airport_surcharge': airport_surcharge,
        'is_airport_trip': is_airport_trip,
        'final_price': final_price
    }

def extract_city_department(address: str) -> str:
    """Extract city and department from full address for privacy in WhatsApp message"""
    if not address:
        return "Non spécifié"
    
    parts = address.split(',')
    postal_match = re.search(r'\b(\d{5})\b', address)
    
    if postal_match:
        postal = postal_match.group(1)
        dept = postal[:2]
        for i, part in enumerate(parts):
            if postal in part:
                city_part = part.strip()
                city = re.sub(r'\d{5}', '', city_part).strip()
                if city:
                    return f"{city} ({dept})"
                elif i > 0:
                    return f"{parts[i-1].strip()} ({dept})"
    
    if len(parts) >= 2:
        return parts[-1].strip()
    
    words = address.split()
    if len(words) >= 2:
        return ' '.join(words[-2:])
    
    return address

# Models
class ReservationCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    pickup_address: str
    dropoff_address: str
    date: str
    time: str
    passengers: int = 1
    luggage: Optional[str] = None
    notes: Optional[str] = None
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None
    estimated_price: Optional[float] = None

class Reservation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    email: Optional[str] = None
    pickup_address: str
    dropoff_address: str
    date: str
    time: str
    passengers: int = 1
    luggage: Optional[str] = None
    notes: Optional[str] = None
    status: str = "nouvelle"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None
    estimated_price: Optional[float] = None
    # Pricing breakdown
    base_price: Optional[float] = None
    airport_surcharge: Optional[float] = None
    is_airport_trip: bool = False
    # Invoice fields
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    final_price: Optional[float] = None
    invoice_details: Optional[str] = None
    invoice_generated: bool = False
    # Bon de commande fields
    bon_commande_generated: bool = False
    bon_commande_date: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str

class AdminLogin(BaseModel):
    password: str

class InvoiceCreate(BaseModel):
    final_price: float
    invoice_details: Optional[str] = None

class AirportSurchargeUpdate(BaseModel):
    is_airport_trip: bool
    airport_surcharge: Optional[float] = None

# ============================================
# PDF GENERATION - BON DE COMMANDE VTC
# ============================================
def generate_bon_commande_pdf(reservation: dict):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Colors
    dark = HexColor("#0a0a0a")
    accent = HexColor("#7dd3fc")
    gray = HexColor("#64748b")
    light_gray = HexColor("#f1f5f9")
    
    y = height - 40
    
    # Header
    c.setFillColor(dark)
    c.rect(0, height - 100, width, 100, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 24)
    c.drawString(40, height - 45, "BON DE COMMANDE VTC")
    
    c.setFont("Helvetica", 11)
    c.setFillColor(accent)
    c.drawString(40, height - 65, "Réservation préalable — Transport de personnes")
    
    # Reference box
    c.setFillColor(HexColor("#1a1a1a"))
    c.roundRect(width - 200, height - 90, 180, 70, 5, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", 9)
    c.drawString(width - 190, height - 45, "N° Bon de commande")
    c.setFont("Helvetica-Bold", 11)
    ref_id = reservation.get('id', '')[:8].upper()
    c.drawString(width - 190, height - 62, f"#{ref_id}")
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    created = reservation.get('created_at', '')
    if created:
        try:
            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            c.drawString(width - 190, height - 78, dt.strftime("%d/%m/%Y à %H:%M"))
        except:
            c.drawString(width - 190, height - 78, created[:16])
    
    y = height - 130
    
    # Section: ENTREPRISE
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "ENTREPRISE")
    y -= 5
    c.setStrokeColor(accent)
    c.setLineWidth(2)
    c.line(40, y, 140, y)
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, f"Nom commercial: ")
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(130, y, COMPANY_INFO["name"])
    y -= 14
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, "Exploitant: EVTC093250520")
    y -= 14
    c.drawString(40, y, f"Statut: VTC — Transport de personnes sur réservation")
    y -= 14
    c.drawString(40, y, f"Email: {COMPANY_INFO['email']} | SIRET: {COMPANY_INFO['siret']}")
    y -= 20
    
    # TVA mention
    c.setFillColor(HexColor("#fef3c7"))
    c.roundRect(40, y - 20, width - 80, 24, 4, fill=True, stroke=False)
    c.setFillColor(HexColor("#92400e"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y - 13, "TVA non applicable — article 293 B du CGI")
    y -= 45
    
    # Section: CLIENT
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "CLIENT")
    y -= 5
    c.setStrokeColor(accent)
    c.line(40, y, 100, y)
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, f"Nom: ")
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(75, y, reservation.get('name', ''))
    y -= 14
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, f"Téléphone: {reservation.get('phone', '')}")
    y -= 14
    if reservation.get('email'):
        c.drawString(40, y, f"Email: {reservation.get('email', '')}")
        y -= 14
    y -= 15
    
    # Section: DÉTAILS COURSE
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "DÉTAILS DE LA COURSE")
    y -= 5
    c.setStrokeColor(accent)
    c.line(40, y, 200, y)
    y -= 18
    
    # Course box
    c.setFillColor(light_gray)
    c.roundRect(40, y - 100, width - 80, 105, 8, fill=True, stroke=False)
    
    box_y = y - 15
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(dark)
    c.drawString(55, box_y, f"Date: {reservation.get('date', '')} à {reservation.get('time', '')}")
    box_y -= 20
    
    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#16a34a"))
    c.drawString(55, box_y, "●")
    c.setFillColor(dark)
    c.drawString(70, box_y, f"Départ: {reservation.get('pickup_address', '')}")
    box_y -= 16
    
    c.setFillColor(HexColor("#dc2626"))
    c.drawString(55, box_y, "●")
    c.setFillColor(dark)
    c.drawString(70, box_y, f"Arrivée: {reservation.get('dropoff_address', '')}")
    box_y -= 20
    
    c.setFillColor(gray)
    c.drawString(55, box_y, f"Passagers: {reservation.get('passengers', 1)}")
    
    distance = reservation.get('distance_km')
    duration = reservation.get('duration_min')
    if distance or duration:
        box_y -= 14
        info = []
        if distance:
            info.append(f"Distance: {distance} km")
        if duration:
            info.append(f"Durée: {int(duration)} min")
        c.drawString(55, box_y, " | ".join(info))
    
    y -= 125
    
    # Section: TARIF
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "TARIF")
    y -= 5
    c.setStrokeColor(accent)
    c.line(40, y, 85, y)
    y -= 25
    
    # Price breakdown
    base_price = reservation.get('base_price') or reservation.get('estimated_price') or 0
    airport_surcharge = reservation.get('airport_surcharge', 0)
    final_price = reservation.get('final_price') or reservation.get('estimated_price') or base_price + airport_surcharge
    is_airport_trip = reservation.get('is_airport_trip', False)
    
    # Price box with breakdown
    box_height = 65 if is_airport_trip else 50
    c.setFillColor(accent)
    c.roundRect(40, y - box_height + 5, 250, box_height, 8, fill=True, stroke=False)
    c.setFillColor(dark)
    
    price_y = y - 15
    c.setFont("Helvetica", 10)
    c.drawString(55, price_y, "Prix course:")
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(270, price_y, f"{int(base_price)} €")
    
    if is_airport_trip and airport_surcharge > 0:
        price_y -= 16
        c.setFont("Helvetica", 10)
        c.drawString(55, price_y, "Supplément aéroport:")
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(270, price_y, f"+ {int(airport_surcharge)} €")
        
        # Separator line
        price_y -= 8
        c.setStrokeColor(dark)
        c.setLineWidth(1)
        c.line(55, price_y, 270, price_y)
    
    price_y -= 16
    c.setFont("Helvetica-Bold", 11)
    c.drawString(55, price_y, "TOTAL:")
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(270, price_y - 5, f"{int(final_price)} €")
    
    c.setFillColor(gray)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(310, y - 25, "Tarif fixé avant prise en charge")
    c.drawString(310, y - 37, "conformément à la réglementation VTC.")
    
    y -= (box_height + 10)
    
    # Section: MENTIONS RÉGLEMENTAIRES
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "MENTIONS RÉGLEMENTAIRES")
    y -= 18
    
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    mentions = [
        "• Transport effectué uniquement sur réservation préalable.",
        "• Aucune prise en charge à la volée.",
        "• Tarif déterminé avant la course."
    ]
    for m in mentions:
        c.drawString(40, y, m)
        y -= 12
    
    y -= 15
    
    # Validation box
    c.setFillColor(light_gray)
    c.roundRect(40, y - 50, width - 80, 55, 6, fill=True, stroke=False)
    
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(55, y - 18, "VALIDATION")
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    c.drawString(55, y - 32, "Bon de commande généré automatiquement suite à réservation.")
    
    timestamp = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    c.drawString(55, y - 44, f"Horodatage: {timestamp} | Référence: #{ref_id}")
    
    # Footer
    c.setFillColor(dark)
    c.rect(0, 0, width, 35, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 15, f"{COMPANY_INFO['name']} — {COMPANY_INFO['legal_name']} — SIRET: {COMPANY_INFO['siret']}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ============================================
# PDF GENERATION - FACTURE
# ============================================
def generate_invoice_pdf(reservation: dict, invoice_number: str, invoice_date: str, final_price: float, invoice_details: str = None):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    dark = HexColor("#0a0a0a")
    accent = HexColor("#7dd3fc")
    gray = HexColor("#64748b")
    light_gray = HexColor("#f1f5f9")
    
    # Header
    c.setFillColor(dark)
    c.rect(0, height - 120, width, 120, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 28)
    c.drawString(40, height - 50, "JABA DRIVER")
    
    c.setFont("Helvetica", 10)
    c.setFillColor(accent)
    c.drawString(40, height - 70, "Service VTC Premium")
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(width - 40, height - 50, "FACTURE")
    
    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#94a3b8"))
    c.drawRightString(width - 40, height - 75, f"N° {invoice_number}")
    c.drawRightString(width - 40, height - 92, f"Date: {invoice_date}")
    
    y = height - 160
    
    # Seller
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "VENDEUR")
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, COMPANY_INFO["name"])
    y -= 14
    c.drawString(40, y, COMPANY_INFO["legal_name"])
    y -= 14
    c.drawString(40, y, f"SIRET: {COMPANY_INFO['siret']}")
    y -= 14
    c.drawString(40, y, f"Email: {COMPANY_INFO['email']}")
    
    # Client
    y = height - 160
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(320, y, "CLIENT")
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(320, y, reservation.get("name", ""))
    y -= 14
    if reservation.get("email"):
        c.drawString(320, y, reservation.get("email", ""))
        y -= 14
    c.drawString(320, y, reservation.get("phone", ""))
    
    y = height - 290
    c.setStrokeColor(light_gray)
    c.setLineWidth(1)
    c.line(40, y, width - 40, y)
    
    # Prestation
    y -= 30
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "PRESTATION")
    
    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Transport de personnes – VTC")
    
    y -= 20
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, f"Date: {reservation.get('date', '')} à {reservation.get('time', '')}")
    y -= 16
    c.drawString(40, y, f"Départ: {reservation.get('pickup_address', '')}")
    y -= 16
    c.drawString(40, y, f"Arrivée: {reservation.get('dropoff_address', '')}")
    y -= 16
    
    distance = reservation.get('distance_km')
    duration = reservation.get('duration_min')
    if distance or duration:
        info = []
        if distance:
            info.append(f"Distance: {distance} km")
        if duration:
            info.append(f"Durée: {int(duration)} min")
        c.drawString(40, y, " | ".join(info))
        y -= 16
    
    c.drawString(40, y, f"Passagers: {reservation.get('passengers', 1)}")
    y -= 16
    c.drawString(40, y, f"Référence: #{reservation.get('id', '')[:8].upper()}")
    
    if invoice_details:
        y -= 25
        c.setFillColor(dark)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, "Détails / Suppléments:")
        y -= 16
        c.setFont("Helvetica", 10)
        c.setFillColor(gray)
        for line in invoice_details.split('\n'):
            c.drawString(40, y, line.strip())
            y -= 14
    
    # Total
    y -= 40
    c.setFillColor(light_gray)
    c.roundRect(40, y - 60, width - 80, 70, 10, fill=True, stroke=False)
    
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y - 25, "TOTAL TTC")
    
    c.setFont("Helvetica-Bold", 28)
    c.drawRightString(width - 60, y - 30, f"{final_price:.2f} €")
    
    y -= 85
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(gray)
    c.drawString(40, y, "TVA non applicable – art. 293 B du CGI")
    
    # Footer
    c.setFillColor(light_gray)
    c.rect(0, 0, width, 50, fill=True, stroke=False)
    
    c.setFillColor(gray)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 25, f"{COMPANY_INFO['name']} - {COMPANY_INFO['legal_name']} - SIRET: {COMPANY_INFO['siret']}")
    c.drawCentredString(width / 2, 12, f"Email: {COMPANY_INFO['email']}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ============================================
# EMAIL FUNCTIONS
# ============================================
async def send_confirmation_email(reservation: Reservation):
    """Send confirmation email to client - NO PDF attachment"""
    if not reservation.email:
        logger.info("Skipping confirmation email - no client email provided")
        return
    
    logger.info(f"[EMAIL] Preparing confirmation email | To: {reservation.email} | From: {SENDER_EMAIL} | Reservation: {reservation.id[:8]}")
    
    # Build price display with breakdown
    price_display = ""
    if reservation.estimated_price or reservation.base_price:
        base_price = reservation.base_price or reservation.estimated_price
        airport_surcharge = reservation.airport_surcharge or 0
        final_price = reservation.estimated_price or (base_price + airport_surcharge)
        
        price_display = f"""
            <tr>
                <td style="padding: 10px 0; color: #94A3B8;">Prix course</td>
                <td style="padding: 10px 0; color: #0F172A; font-weight: 600;">{int(base_price)}€</td>
            </tr>
        """
        
        if reservation.is_airport_trip and airport_surcharge > 0:
            price_display += f"""
            <tr>
                <td style="padding: 10px 0; color: #94A3B8;">Supplément aéroport</td>
                <td style="padding: 10px 0; color: #0F172A; font-weight: 600;">+ {int(airport_surcharge)}€</td>
            </tr>
            <tr>
                <td style="padding: 10px 0; border-top: 1px solid #E2E8F0; color: #0F172A; font-weight: 700;">TOTAL</td>
                <td style="padding: 10px 0; border-top: 1px solid #E2E8F0; color: #0F172A; font-weight: 700;">{int(final_price)}€</td>
            </tr>
            """
        else:
            price_display += f"""
            <tr>
                <td style="padding: 10px 0; border-top: 1px solid #E2E8F0; color: #0F172A; font-weight: 700;">TOTAL</td>
                <td style="padding: 10px 0; border-top: 1px solid #E2E8F0; color: #0F172A; font-weight: 700;">{int(final_price)}€</td>
            </tr>
            """
    
    # Generate Google Maps URL
    origin_encoded = quote(reservation.pickup_address)
    destination_encoded = quote(reservation.dropoff_address)
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={destination_encoded}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background-color: #0a0a0a; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">JABA DRIVER</h1>
            <p style="color: #7dd3fc; margin: 10px 0 0 0;">Service VTC Premium</p>
        </div>
        <div style="padding: 30px; background-color: #F8FAFC;">
            <h2 style="color: #0a0a0a;">Confirmation de réservation</h2>
            <p>Bonjour <strong>{reservation.name}</strong>,</p>
            <p>Votre réservation a bien été enregistrée.</p>
            <div style="background: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
                <table style="width: 100%;">
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8;">Date & Heure</td>
                        <td style="padding: 10px 0; font-weight: 600;">{reservation.date} à {reservation.time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8;">Départ</td>
                        <td style="padding: 10px 0;">{reservation.pickup_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8;">Arrivée</td>
                        <td style="padding: 10px 0;">{reservation.dropoff_address}</td>
                    </tr>
                    {price_display}
                </table>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{maps_url}" style="display: inline-block; background-color: #7dd3fc; color: #0a0a0a; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                    📍 Voir l'itinéraire Google Maps
                </a>
            </div>
            
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 8px;">
                <h3 style="margin: 0 0 10px 0; color: #856404; font-size: 14px;">📋 Conditions de modification et d'annulation</h3>
                <ul style="margin: 0; padding-left: 20px; color: #856404; font-size: 13px; line-height: 1.6;">
                    <li>Modification gratuite jusqu'à 1 heure avant la prise en charge (selon disponibilité)</li>
                    <li>Annulation gratuite jusqu'à 1 heure avant</li>
                    <li>Annulation moins de 1 heure : frais possibles</li>
                    <li>Tolérance retard client : 5 minutes</li>
                    <li>Au-delà : attente facturée 1 € / minute</li>
                    <li>Attente maximale : 20 minutes</li>
                    <li>Après 20 minutes : course due en totalité</li>
                </ul>
                <p style="margin: 15px 0 0 0; color: #856404; font-size: 13px; font-weight: bold;">
                    Demandes uniquement via WhatsApp : 
                    <a href="https://wa.me/message/MQ6BTZ7KU26OM1" style="color: #25D366; text-decoration: underline;">Cliquez ici</a>
                </p>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    SIRET : 941 473 217 00011<br/>
                    Email : contact@jabadriver.fr
                </p>
            </div>
            
            <p>Merci de votre confiance !</p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [reservation.email],
            "subject": f"JABA DRIVER - Confirmation réservation du {reservation.date}",
            "html": html_content
        }
        # NO PDF attachment - removed
        
        logger.info(f"[EMAIL] Calling Resend API for confirmation email (no PDF) | API Key present: {bool(resend.api_key)}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Confirmation email sent successfully | To: {reservation.email} | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send confirmation email | To: {reservation.email} | Error: {str(e)}")
        logger.exception("Full exception trace:")

async def send_driver_alert(reservation: Reservation, claim_url: str = None):
    """Send alert email to admin/driver - NO PDF attachment, includes claim link"""
    if not DRIVER_EMAIL:
        logger.warning("[EMAIL] Skipping driver alert - DRIVER_EMAIL not configured")
        return
    
    logger.info(f"[EMAIL] Preparing driver alert | To: {DRIVER_EMAIL} | From: {SENDER_EMAIL} | Reservation: {reservation.id[:8]}")
    
    price_info = ""
    if reservation.estimated_price:
        distance_str = f"{reservation.distance_km:.1f} km" if reservation.distance_km else "N/A"
        duration_str = f"{int(reservation.duration_min)} min" if reservation.duration_min else "N/A"
        
        base_price = reservation.base_price or reservation.estimated_price
        airport_surcharge = reservation.airport_surcharge or 0
        final_price = reservation.estimated_price or (base_price + airport_surcharge)
        
        # Build price breakdown
        price_breakdown = f"<p style='margin: 5px 0 0 0; font-size: 28px; font-weight: bold;'>{int(final_price)}€</p>"
        if reservation.is_airport_trip and airport_surcharge > 0:
            price_breakdown = f"""
                <p style='margin: 5px 0 0 0; font-size: 14px;'>Course: {int(base_price)}€ + Aéroport: {int(airport_surcharge)}€</p>
                <p style='margin: 5px 0 0 0; font-size: 28px; font-weight: bold;'>{int(final_price)}€</p>
            """
        
        price_info = f"""
            <div style="background: #7dd3fc; color: #0a0a0a; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Prix total</p>
                {price_breakdown}
                <p style="margin: 5px 0 0 0; font-size: 12px;">{distance_str} • {duration_str}</p>
            </div>
        """
    
    # Generate Google Maps URL
    origin_encoded = quote(reservation.pickup_address)
    destination_encoded = quote(reservation.dropoff_address)
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={destination_encoded}"
    
    # Admin URL for subcontracting management
    frontend_url = os.environ.get('FRONTEND_URL', 'https://vtc-subcontract.preview.emergentagent.com')
    admin_subcontracting_url = f"{frontend_url}/admin/subcontracting"
    
    # Claim link section for subcontracting
    claim_section = ""
    whatsapp_section = ""
    
    if claim_url:
        # Extract city/department for WhatsApp message (privacy)
        pickup_city = extract_city_department(reservation.pickup_address)
        dropoff_city = extract_city_department(reservation.dropoff_address)
        price_display = int(reservation.estimated_price) if reservation.estimated_price else "N/A"
        
        # WhatsApp message format
        whatsapp_message = f"🚗 NOUVELLE COURSE — {price_display}€ — {pickup_city} → {dropoff_city} — {reservation.date} {reservation.time}\n\nLien chauffeur : {claim_url}"
        whatsapp_encoded = quote(whatsapp_message)
        whatsapp_url = f"https://wa.me/?text={whatsapp_encoded}"
        
        whatsapp_section = f"""
            <div style="background: #25D366; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <h3 style="margin: 0 0 10px 0;">📲 Partager aux chauffeurs</h3>
                <p style="margin: 0 0 15px 0; font-size: 14px;">Envoyez cette course à vos chauffeurs via WhatsApp :</p>
                <a href="{whatsapp_url}" style="display: inline-block; background-color: white; color: #25D366; padding: 14px 35px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                    📤 Partager via WhatsApp
                </a>
                <p style="margin: 15px 0 0 0; font-size: 11px; opacity: 0.9;">Cliquez pour choisir un groupe ou contact WhatsApp</p>
            </div>
        """
        
        claim_section = f"""
            <div style="background: #f59e0b; color: #0a0a0a; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <h3 style="margin: 0 0 10px 0;">🚗 Sous-traiter cette course</h3>
                <p style="margin: 0 0 15px 0; font-size: 14px;">Ou copiez ce lien manuellement :</p>
                <a href="{claim_url}" style="display: inline-block; background-color: #0a0a0a; color: #f59e0b; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; word-break: break-all;">
                    🔗 Copier le lien chauffeur
                </a>
                <p style="margin: 15px 0 0 0; font-size: 11px; color: #333;">Commission: 10% • Premier chauffeur qui paie = course attribuée</p>
            </div>
        """
    else:
        # If no claim_url provided, show button to generate one via admin panel
        claim_section = f"""
            <div style="background: #3b82f6; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <h3 style="margin: 0 0 10px 0;">🚗 Sous-traiter cette course ?</h3>
                <p style="margin: 0 0 15px 0; font-size: 14px;">Générez un lien pour vos chauffeurs partenaires</p>
                <a href="{admin_subcontracting_url}" style="display: inline-block; background-color: white; color: #3b82f6; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                    📋 Gérer la sous-traitance
                </a>
            </div>
        """
    
    # Quick action button to admin subcontracting page
    admin_action_button = f"""
        <div style="text-align: center; margin: 20px 0;">
            <a href="{admin_subcontracting_url}" style="display: inline-block; background-color: #f59e0b; color: #0a0a0a; padding: 14px 35px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                ⚡ Ouvrir Sous-traitance Admin
            </a>
        </div>
    """
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #7dd3fc; color: #0a0a0a; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">🚗 NOUVELLE RÉSERVATION</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            {price_info}
            {whatsapp_section}
            {claim_section}
            
            {admin_action_button}
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0;">Client</h3>
                <p><strong>Nom:</strong> {reservation.name}</p>
                <p><strong>Téléphone:</strong> <a href="tel:{reservation.phone}">{reservation.phone}</a></p>
                {f'<p><strong>Email:</strong> {reservation.email}</p>' if reservation.email else ''}
            </div>
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="margin-top: 0;">Course</h3>
                <p><strong>Date:</strong> {reservation.date} à {reservation.time}</p>
                <p><strong>Départ:</strong> {reservation.pickup_address}</p>
                <p><strong>Arrivée:</strong> {reservation.dropoff_address}</p>
                <p><strong>Passagers:</strong> {reservation.passengers}</p>
            </div>
            <div style="text-align: center; margin: 20px 0;">
                <a href="{maps_url}" style="display: inline-block; background-color: #0a0a0a; color: #7dd3fc; padding: 12px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
                    📍 Voir l'itinéraire Google Maps
                </a>
            </div>
            
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 8px;">
                <h3 style="margin: 0 0 10px 0; color: #856404; font-size: 14px;">📋 Conditions de modification et d'annulation</h3>
                <ul style="margin: 0; padding-left: 20px; color: #856404; font-size: 13px; line-height: 1.6;">
                    <li>Modification gratuite jusqu'à 1 heure avant la prise en charge (selon disponibilité)</li>
                    <li>Annulation gratuite jusqu'à 1 heure avant</li>
                    <li>Annulation moins de 1 heure : frais possibles</li>
                    <li>Tolérance retard client : 5 minutes</li>
                    <li>Au-delà : attente facturée 1 € / minute</li>
                    <li>Attente maximale : 20 minutes</li>
                    <li>Après 20 minutes : course due en totalité</li>
                </ul>
                <p style="margin: 15px 0 0 0; color: #856404; font-size: 13px; font-weight: bold;">
                    Demandes uniquement via WhatsApp : 
                    <a href="https://wa.me/message/MQ6BTZ7KU26OM1" style="color: #25D366; text-decoration: underline;">Cliquez ici</a>
                </p>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    SIRET : 941 473 217 00011<br/>
                    Email : contact@jabadriver.fr
                </p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [DRIVER_EMAIL],
            "subject": f"🚗 Nouvelle réservation - {reservation.name} - {reservation.date} {reservation.time}",
            "html": html_content
        }
        # NO PDF attachment - removed
        
        logger.info(f"[EMAIL] Calling Resend API for driver alert (no PDF) | API Key present: {bool(resend.api_key)}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver alert sent successfully | To: {DRIVER_EMAIL} | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver alert | To: {DRIVER_EMAIL} | Error: {str(e)}")
        logger.exception("Full exception trace:")

async def send_invoice_email(reservation: dict, pdf_data: bytes):
    client_email = reservation.get("email")
    if not client_email:
        raise ValueError("Client email not available")
    
    invoice_number = reservation.get("invoice_number", "")
    final_price = reservation.get("final_price", 0)
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #0a0a0a; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">JABA DRIVER</h1>
            <p style="color: #7dd3fc; margin: 10px 0 0 0;">Service VTC Premium</p>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <h2>Votre facture</h2>
            <p>Bonjour <strong>{reservation.get('name', '')}</strong>,</p>
            <p>Veuillez trouver ci-joint votre facture n° <strong>{invoice_number}</strong> pour un montant de <strong>{final_price:.2f} €</strong>.</p>
            <p>Merci pour votre confiance !</p>
            <p style="margin-top: 30px;">Cordialement,<br/>JABA DRIVER</p>
        </div>
    </div>
    """
    
    params = {
        "from": SENDER_EMAIL,
        "to": [client_email],
        "subject": f"JABA DRIVER - Facture {invoice_number}",
        "html": html_content,
        "attachments": [{
            "filename": f"facture_{invoice_number}.pdf",
            "content": base64.b64encode(pdf_data).decode('utf-8')
        }]
    }
    
    await asyncio.to_thread(resend.Emails.send, params)
    logger.info(f"Invoice email sent to {client_email}")

# ============================================
# ROUTES
# ============================================
@api_router.get("/")
async def root():
    return {"message": "JABA DRIVER API"}

@api_router.post("/reservations", response_model=Reservation)
async def create_reservation(input: ReservationCreate, request: Request):
    reservation_dict = input.model_dump()
    
    logger.info("=" * 80)
    logger.info("[CREATE RESERVATION] Starting reservation creation")
    logger.info(f"[CREATE RESERVATION] Client: {reservation_dict.get('name')}")
    logger.info(f"[CREATE RESERVATION] Email: {reservation_dict.get('email', 'NOT PROVIDED')}")
    
    # Validate minimum booking delay (6 hours in advance)
    date_str = reservation_dict.get('date', '')
    time_str = reservation_dict.get('time', '')
    is_valid, error_msg = validate_booking_delay(date_str, time_str)
    if not is_valid:
        logger.warning(f"[CREATE RESERVATION] ❌ Booking delay validation failed: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Calculate price with airport surcharge
    pricing = calculate_price_with_surcharge(
        estimated_price=reservation_dict.get('estimated_price', 0.0),
        pickup_address=reservation_dict.get('pickup_address', ''),
        dropoff_address=reservation_dict.get('dropoff_address', '')
    )
    
    # Add pricing breakdown to reservation
    reservation_dict['base_price'] = pricing['base_price']
    reservation_dict['airport_surcharge'] = pricing['airport_surcharge']
    reservation_dict['is_airport_trip'] = pricing['is_airport_trip']
    if pricing['is_airport_trip']:
        reservation_dict['estimated_price'] = pricing['final_price']
    
    reservation = Reservation(**reservation_dict)
    
    # Save reservation in DB FIRST (critical step)
    reservation_data = reservation.model_dump()
    await db.reservations.insert_one(reservation_data)
    logger.info(f"[CREATE RESERVATION] ✅ Reservation saved in DB | ID: {reservation.id[:8]}")
    
    reservation_obj = Reservation(**reservation_data)
    
    # Create corresponding course in subcontracting module
    claim_url = None
    try:
        from subcontracting import Course, ClaimToken, COMMISSION_RATE, CLAIM_TOKEN_EXPIRY_MINUTES
        from datetime import timedelta
        import secrets
        
        final_price = reservation_obj.estimated_price or (reservation_obj.base_price + (reservation_obj.airport_surcharge or 0))
        
        # Create course for subcontracting
        course = Course(
            client_name=reservation_obj.name,
            client_email=reservation_obj.email or "",
            client_phone=reservation_obj.phone,
            pickup_address=reservation_obj.pickup_address,
            dropoff_address=reservation_obj.dropoff_address,
            date=reservation_obj.date,
            time=reservation_obj.time,
            distance_km=reservation_obj.distance_km,
            price_total=final_price,
            notes=f"Réservation client #{reservation_obj.id[:8]} - {reservation_obj.passengers} passager(s)",
            commission_amount=round(final_price * COMMISSION_RATE, 2)
        )
        
        await db.courses.insert_one(course.model_dump())
        logger.info(f"[CREATE RESERVATION] ✅ Subcontracting course created | ID: {course.id[:8]}")
        
        # Generate claim token
        claim_token = ClaimToken(
            course_id=course.id,
            token=secrets.token_urlsafe(32),
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=CLAIM_TOKEN_EXPIRY_MINUTES)).isoformat()
        )
        await db.claim_tokens.insert_one(claim_token.model_dump())
        
        # Build claim URL
        # Get base URL from request or use default
        base_url = str(request.base_url).rstrip('/')
        if '/api' in base_url:
            base_url = base_url.split('/api')[0]
        # Use frontend URL for claim page
        frontend_url = os.environ.get('FRONTEND_URL', base_url.replace(':8001', ':3000'))
        claim_url = f"{frontend_url}/claim/{claim_token.token}"
        
        logger.info(f"[CREATE RESERVATION] ✅ Claim token generated | URL: {claim_url[:50]}...")
        
        # Link reservation to course
        await db.reservations.update_one(
            {"id": reservation.id}, 
            {"$set": {"subcontracting_course_id": course.id}}
        )
        
    except Exception as e:
        logger.error(f"[CREATE RESERVATION] ⚠️ Subcontracting setup failed: {str(e)}")
        logger.exception("Full trace:")
    
    # Send emails - NO PDF attachments
    try:
        # Email to client (no PDF)
        try:
            await send_confirmation_email(reservation_obj)
        except Exception as e:
            logger.error(f"[CREATE RESERVATION] ⚠️ Email client failed: {str(e)}")
        
        # Email to admin with claim link (no PDF)
        try:
            await send_driver_alert(reservation_obj, claim_url)
        except Exception as e:
            logger.error(f"[CREATE RESERVATION] ⚠️ Email driver failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"[CREATE RESERVATION] ⚠️ Email failed but reservation saved: {str(e)}")
        logger.exception("Full trace:")
    
    logger.info(f"[CREATE RESERVATION] ✅ Process completed")
    logger.info("=" * 80)
    
    return reservation_obj

@api_router.get("/reservations", response_model=List[Reservation])
async def get_reservations(
    date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return reservations

@api_router.get("/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    return reservation

@api_router.patch("/reservations/{reservation_id}/status")
async def update_reservation_status(reservation_id: str, update: StatusUpdate):
    valid_statuses = ["nouvelle", "confirmée", "effectuée", "annulée"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail="Statut invalide")
    
    result = await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"status": update.status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    return {"message": "Statut mis à jour", "status": update.status}

@api_router.patch("/reservations/{reservation_id}/airport-surcharge")
async def update_airport_surcharge(reservation_id: str, update: AirportSurchargeUpdate):
    # Get current reservation
    reservation = await db.reservations.find_one({"id": reservation_id})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    # Calculate new pricing
    base_price = reservation.get('base_price') or reservation.get('estimated_price', 0)
    airport_surcharge = 0.0
    
    if update.is_airport_trip:
        airport_surcharge = update.airport_surcharge if update.airport_surcharge is not None else AIRPORT_SURCHARGE
    
    new_estimated_price = base_price + airport_surcharge
    
    # Update reservation
    result = await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "is_airport_trip": update.is_airport_trip,
            "airport_surcharge": airport_surcharge,
            "estimated_price": new_estimated_price
        }}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    return {
        "message": "Supplément aéroport mis à jour",
        "is_airport_trip": update.is_airport_trip,
        "airport_surcharge": airport_surcharge,
        "estimated_price": new_estimated_price
    }

@api_router.post("/admin/login")
async def admin_login(login: AdminLogin):
    if login.password == ADMIN_PASSWORD:
        return {"success": True}
    raise HTTPException(status_code=401, detail="Mot de passe incorrect")

@api_router.post("/admin/test-email")
async def test_email_send(login: AdminLogin):
    """Route de test pour vérifier l'envoi d'email direct (sans background task)"""
    if login.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    
    logger.info("=" * 80)
    logger.info("[TEST EMAIL] Starting email test")
    logger.info(f"[TEST EMAIL] RESEND_API_KEY present: {bool(resend.api_key)}")
    logger.info(f"[TEST EMAIL] RESEND_API_KEY length: {len(resend.api_key) if resend.api_key else 0}")
    logger.info(f"[TEST EMAIL] SENDER_EMAIL: {SENDER_EMAIL}")
    logger.info(f"[TEST EMAIL] DRIVER_EMAIL: {DRIVER_EMAIL}")
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [DRIVER_EMAIL],
            "subject": "🧪 Test email - JabaDriver VTC",
            "html": "<h1>Test email</h1><p>Si vous recevez cet email, la configuration Resend fonctionne correctement.</p>"
        }
        
        logger.info(f"[TEST EMAIL] Calling Resend.Emails.send()")
        logger.info(f"[TEST EMAIL] From: {params['from']}")
        logger.info(f"[TEST EMAIL] To: {params['to']}")
        
        # Direct call (not async) for testing
        response = resend.Emails.send(params)
        
        logger.info(f"[TEST EMAIL] ✅ SUCCESS - Email sent!")
        logger.info(f"[TEST EMAIL] Resend response: {response}")
        logger.info("=" * 80)
        
        return {
            "success": True,
            "message": "Email de test envoyé avec succès",
            "resend_id": response.get('id', 'N/A'),
            "to": DRIVER_EMAIL,
            "from": SENDER_EMAIL
        }
    except Exception as e:
        logger.error(f"[TEST EMAIL] ❌ FAILED - Error: {str(e)}")
        logger.exception("[TEST EMAIL] Full exception:")
        logger.info("=" * 80)
        raise HTTPException(status_code=500, detail=f"Erreur envoi email: {str(e)}")

@api_router.get("/admin/email-debug")
async def email_debug(password: str = Query(...)):
    """Route de diagnostic email - retourne la config et teste l'envoi"""
    if password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    
    debug_info = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment_variables": {
            "SENDER_EMAIL": SENDER_EMAIL,
            "SENDER_EMAIL_NEW_from_env": os.environ.get('SENDER_EMAIL_NEW', 'NOT_SET'),
            "RESEND_API_KEY_present": bool(resend.api_key),
            "RESEND_API_KEY_length": len(resend.api_key) if resend.api_key else 0,
            "RESEND_API_KEY_first_10_chars": resend.api_key[:10] if resend.api_key else "EMPTY",
            "DRIVER_EMAIL": DRIVER_EMAIL,
        },
        "resend_test": {}
    }
    
    # Test d'envoi Resend
    try:
        test_params = {
            "from": SENDER_EMAIL,
            "to": [DRIVER_EMAIL] if DRIVER_EMAIL else ["noreply@jabadriver.fr"],
            "subject": "🔍 Email Debug Test",
            "html": "<p>Test automatique de diagnostic email</p>"
        }
        
        response = resend.Emails.send(test_params)
        
        debug_info["resend_test"] = {
            "status": "SUCCESS",
            "resend_id": response.get('id', 'N/A'),
            "from": test_params["from"],
            "to": test_params["to"],
            "response_full": str(response)
        }
    except Exception as e:
        debug_info["resend_test"] = {
            "status": "FAILED",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "from_attempted": SENDER_EMAIL,
            "to_attempted": DRIVER_EMAIL
        }
    
    return debug_info

# Bon de commande routes
@api_router.get("/reservations/{reservation_id}/bon-commande-pdf")
async def download_bon_commande(reservation_id: str):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    pdf_data = generate_bon_commande_pdf(reservation)
    filename = f"bon_commande_{reservation_id[:8].upper()}.pdf"
    
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Invoice routes
async def generate_invoice_number():
    year = datetime.now().year
    last_invoice = await db.reservations.find_one(
        {"invoice_number": {"$regex": f"^{year}-"}},
        sort=[("invoice_number", -1)]
    )
    
    if last_invoice and last_invoice.get("invoice_number"):
        try:
            last_num = int(last_invoice["invoice_number"].split("-")[1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"{year}-{new_num:05d}"

@api_router.post("/reservations/{reservation_id}/invoice")
async def create_invoice(reservation_id: str, invoice_data: InvoiceCreate):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    if invoice_data.final_price < 10:
        raise HTTPException(status_code=400, detail="Prix minimum 10€")
    
    invoice_number = reservation.get("invoice_number")
    if not invoice_number:
        invoice_number = await generate_invoice_number()
    
    invoice_date = datetime.now().strftime("%d/%m/%Y")
    
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "final_price": invoice_data.final_price,
            "invoice_details": invoice_data.invoice_details,
            "invoice_generated": True
        }}
    )
    
    return {
        "invoice_number": invoice_number,
        "invoice_date": invoice_date,
        "final_price": invoice_data.final_price
    }

@api_router.get("/reservations/{reservation_id}/invoice/pdf")
async def download_invoice_pdf(reservation_id: str):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    if not reservation.get("invoice_generated"):
        raise HTTPException(status_code=400, detail="Facture non générée")
    
    pdf_data = generate_invoice_pdf(
        reservation,
        reservation.get("invoice_number", ""),
        reservation.get("invoice_date", ""),
        reservation.get("final_price", 0),
        reservation.get("invoice_details")
    )
    
    filename = f"facture_{reservation.get('invoice_number', 'unknown')}.pdf"
    
    return Response(
        content=pdf_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.post("/reservations/{reservation_id}/invoice/send")
async def send_invoice(reservation_id: str):
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    if not reservation.get("invoice_generated"):
        raise HTTPException(status_code=400, detail="Facture non générée")
    
    if not reservation.get("email"):
        raise HTTPException(status_code=400, detail="Email client non renseigné")
    
    try:
        pdf_data = generate_invoice_pdf(
            reservation,
            reservation.get("invoice_number", ""),
            reservation.get("invoice_date", ""),
            reservation.get("final_price", 0),
            reservation.get("invoice_details")
        )
        
        await send_invoice_email(reservation, pdf_data)
        return {"message": f"Facture envoyée à {reservation.get('email')}"}
    except Exception as e:
        logger.error(f"Failed to send invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur d'envoi: {str(e)}")

@api_router.get("/reservations/export/csv")
async def export_reservations_csv(
    date: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        "ID", "Nom", "Téléphone", "Email", "Départ", "Arrivée", 
        "Date", "Heure", "Passagers", "Statut",
        "Distance", "Durée", "Prix estimé", 
        "N° Facture", "Prix final", "Créé le"
    ])
    
    for r in reservations:
        writer.writerow([
            r.get("id", "")[:8],
            r.get("name", ""),
            r.get("phone", ""),
            r.get("email", ""),
            r.get("pickup_address", ""),
            r.get("dropoff_address", ""),
            r.get("date", ""),
            r.get("time", ""),
            r.get("passengers", ""),
            r.get("status", ""),
            r.get("distance_km", ""),
            r.get("duration_min", ""),
            r.get("estimated_price", ""),
            r.get("invoice_number", ""),
            r.get("final_price", ""),
            r.get("created_at", "")[:10] if r.get("created_at") else ""
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reservations_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# ============================================
# SUBCONTRACTING MODULE
# ============================================
from subcontracting import (
    subcontracting_router, 
    driver_router, 
    admin_subcontracting_router,
    init_subcontracting,
    handle_stripe_webhook
)

# Initialize subcontracting module with database, stripe key, and email config
init_subcontracting(
    database=db, 
    stripe_key=STRIPE_API_KEY,
    admin_email=DRIVER_EMAIL,  # Admin receives driver notifications (same as DRIVER_EMAIL)
    sender_email=SENDER_EMAIL,
    frontend_url=os.environ.get('FRONTEND_URL', '')
)

# Include subcontracting routers
app.include_router(subcontracting_router)
app.include_router(driver_router)
app.include_router(admin_subcontracting_router)

# Stripe webhook route
@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request):
    return await handle_stripe_webhook(request)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
