from fastapi import FastAPI, APIRouter, HTTPException, Query
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
from datetime import datetime, timezone
import io
import csv
import resend
import base64
from urllib.parse import quote

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
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
DRIVER_EMAIL = os.environ.get('DRIVER_EMAIL', '')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Pricing configuration
AIRPORT_SURCHARGE = 10.0  # Supplément aéroport en euros

# Company info
COMPANY_INFO = {
    "name": "JABA DRIVER",
    "legal_name": "GREVIN Jahid Baptiste (EI)",
    "address": "49 Boulevard Marc Chagall, 93600 Aulnay-sous-Bois",
    "siret": "941 473 217 00011",
    "email": "jabadriver93@gmail.com",
    "phone": "06 XX XX XX XX"
}

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Helper functions
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
    c.drawString(40, y, f"Exploitant: {COMPANY_INFO['legal_name']}")
    y -= 14
    c.drawString(40, y, f"Statut: VTC — Transport de personnes sur réservation")
    y -= 14
    c.drawString(40, y, f"Adresse: {COMPANY_INFO['address']}")
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
    
    # Price box
    final_price = reservation.get('final_price') or reservation.get('estimated_price')
    price_label = "Prix convenu" if reservation.get('final_price') else "Prix estimé"
    
    c.setFillColor(accent)
    c.roundRect(40, y - 45, 200, 50, 8, fill=True, stroke=False)
    c.setFillColor(dark)
    c.setFont("Helvetica", 10)
    c.drawString(55, y - 15, price_label)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(55, y - 40, f"{int(final_price) if final_price else '--'} €")
    
    c.setFillColor(gray)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(260, y - 25, "Tarif fixé avant prise en charge")
    c.drawString(260, y - 37, "conformément à la réglementation VTC.")
    
    y -= 70
    
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
    c.drawCentredString(width / 2, 20, f"{COMPANY_INFO['name']} — {COMPANY_INFO['legal_name']} — SIRET: {COMPANY_INFO['siret']}")
    c.drawCentredString(width / 2, 10, f"{COMPANY_INFO['address']}")
    
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
    c.drawString(40, y, COMPANY_INFO["address"])
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
    c.drawCentredString(width / 2, 30, f"{COMPANY_INFO['name']} - {COMPANY_INFO['legal_name']} - SIRET: {COMPANY_INFO['siret']}")
    c.drawCentredString(width / 2, 18, f"{COMPANY_INFO['address']} - {COMPANY_INFO['email']}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ============================================
# EMAIL FUNCTIONS
# ============================================
async def send_confirmation_email(reservation: Reservation, bon_commande_pdf: bytes = None):
    if not reservation.email:
        return
    
    price_display = ""
    if reservation.estimated_price:
        price_display = f"""
            <tr>
                <td style="padding: 10px 0; color: #94A3B8;">Prix estimé</td>
                <td style="padding: 10px 0; color: #0F172A; font-weight: 600;">{int(reservation.estimated_price)}€</td>
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
            <p>Votre réservation a bien été enregistrée. Vous trouverez ci-joint votre bon de commande.</p>
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
        
        if bon_commande_pdf:
            params["attachments"] = [{
                "filename": f"bon_commande_{reservation.id[:8].upper()}.pdf",
                "content": base64.b64encode(bon_commande_pdf).decode('utf-8')
            }]
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Confirmation email sent to {reservation.email}")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {str(e)}")

async def send_driver_alert(reservation: Reservation, bon_commande_pdf: bytes = None):
    if not DRIVER_EMAIL:
        return
    
    price_info = ""
    if reservation.estimated_price:
        distance_str = f"{reservation.distance_km:.1f} km" if reservation.distance_km else "N/A"
        duration_str = f"{int(reservation.duration_min)} min" if reservation.duration_min else "N/A"
        price_info = f"""
            <div style="background: #7dd3fc; color: #0a0a0a; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Prix estimé</p>
                <p style="margin: 5px 0 0 0; font-size: 28px; font-weight: bold;">{int(reservation.estimated_price)}€</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">{distance_str} • {duration_str}</p>
            </div>
        """
    
    # Generate Google Maps URL
    origin_encoded = quote(reservation.pickup_address)
    destination_encoded = quote(reservation.dropoff_address)
    maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin_encoded}&destination={destination_encoded}"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #7dd3fc; color: #0a0a0a; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">🚗 NOUVELLE RÉSERVATION</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            {price_info}
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
        
        if bon_commande_pdf:
            params["attachments"] = [{
                "filename": f"bon_commande_{reservation.id[:8].upper()}.pdf",
                "content": base64.b64encode(bon_commande_pdf).decode('utf-8')
            }]
        
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Driver alert sent to {DRIVER_EMAIL}")
    except Exception as e:
        logger.error(f"Failed to send driver alert: {str(e)}")

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
async def create_reservation(input: ReservationCreate):
    reservation_dict = input.model_dump()
    reservation = Reservation(**reservation_dict)
    
    # Generate bon de commande automatically
    reservation_data = reservation.model_dump()
    bon_commande_pdf = generate_bon_commande_pdf(reservation_data)
    
    # Update reservation with bon de commande info
    reservation_data["bon_commande_generated"] = True
    reservation_data["bon_commande_date"] = datetime.now(timezone.utc).isoformat()
    
    await db.reservations.insert_one(reservation_data)
    
    # Send emails with bon de commande attached
    reservation_obj = Reservation(**reservation_data)
    asyncio.create_task(send_confirmation_email(reservation_obj, bon_commande_pdf))
    asyncio.create_task(send_driver_alert(reservation_obj, bon_commande_pdf))
    
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

@api_router.post("/admin/login")
async def admin_login(login: AdminLogin):
    if login.password == ADMIN_PASSWORD:
        return {"success": True}
    raise HTTPException(status_code=401, detail="Mot de passe incorrect")

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
