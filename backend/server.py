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

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

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

# Company info for invoices
COMPANY_INFO = {
    "name": "JABA DRIVER",
    "legal_name": "GREVIN Jahid Baptiste (EI)",
    "address": "49 Boulevard Marc Chagall, 93600 Aulnay-sous-Bois",
    "siret": "941 473 217 00011",
    "email": "jabadriver93@gmail.com"
}

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    # Invoice fields
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    final_price: Optional[float] = None
    invoice_details: Optional[str] = None
    invoice_generated: bool = False

class StatusUpdate(BaseModel):
    status: str

class AdminLogin(BaseModel):
    password: str

class InvoiceCreate(BaseModel):
    final_price: float
    invoice_details: Optional[str] = None

# Helper: Generate invoice number
async def generate_invoice_number():
    year = datetime.now().year
    # Find the last invoice number for this year
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

# Helper: Generate PDF invoice
def generate_invoice_pdf(reservation: dict, invoice_number: str, invoice_date: str, final_price: float, invoice_details: str = None):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Colors
    dark_color = HexColor("#0a0a0a")
    accent_color = HexColor("#7dd3fc")
    gray_color = HexColor("#64748b")
    light_gray = HexColor("#f1f5f9")
    
    # Header background
    c.setFillColor(dark_color)
    c.rect(0, height - 120, width, 120, fill=True, stroke=False)
    
    # Company name
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 28)
    c.drawString(40, height - 50, "JABA DRIVER")
    
    # Subtitle
    c.setFont("Helvetica", 10)
    c.setFillColor(accent_color)
    c.drawString(40, height - 70, "Service VTC Premium")
    
    # FACTURE title
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 24)
    c.drawRightString(width - 40, height - 50, "FACTURE")
    
    # Invoice number and date
    c.setFont("Helvetica", 11)
    c.setFillColor(HexColor("#94a3b8"))
    c.drawRightString(width - 40, height - 75, f"N° {invoice_number}")
    c.drawRightString(width - 40, height - 92, f"Date: {invoice_date}")
    
    # Reset for body
    y = height - 160
    
    # Seller info
    c.setFillColor(dark_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "VENDEUR")
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray_color)
    c.drawString(40, y, COMPANY_INFO["name"])
    y -= 14
    c.drawString(40, y, COMPANY_INFO["legal_name"])
    y -= 14
    c.drawString(40, y, COMPANY_INFO["address"])
    y -= 14
    c.drawString(40, y, f"SIRET: {COMPANY_INFO['siret']}")
    y -= 14
    c.drawString(40, y, f"Email: {COMPANY_INFO['email']}")
    
    # Client info
    y = height - 160
    c.setFillColor(dark_color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(320, y, "CLIENT")
    y -= 18
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray_color)
    c.drawString(320, y, reservation.get("name", ""))
    y -= 14
    if reservation.get("email"):
        c.drawString(320, y, reservation.get("email", ""))
        y -= 14
    c.drawString(320, y, reservation.get("phone", ""))
    
    # Separator line
    y = height - 290
    c.setStrokeColor(light_gray)
    c.setLineWidth(1)
    c.line(40, y, width - 40, y)
    
    # Prestation section
    y -= 30
    c.setFillColor(dark_color)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "PRESTATION")
    
    y -= 25
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Transport de personnes – VTC")
    
    y -= 20
    c.setFont("Helvetica", 10)
    c.setFillColor(gray_color)
    
    # Date/Time
    c.drawString(40, y, f"Date: {reservation.get('date', '')} à {reservation.get('time', '')}")
    y -= 16
    
    # Departure
    c.drawString(40, y, f"Départ: {reservation.get('pickup_address', '')}")
    y -= 16
    
    # Arrival
    c.drawString(40, y, f"Arrivée: {reservation.get('dropoff_address', '')}")
    y -= 16
    
    # Distance / Duration
    distance = reservation.get('distance_km')
    duration = reservation.get('duration_min')
    if distance or duration:
        info_parts = []
        if distance:
            info_parts.append(f"Distance: {distance} km")
        if duration:
            info_parts.append(f"Durée: {int(duration)} min")
        c.drawString(40, y, " | ".join(info_parts))
        y -= 16
    
    # Passengers
    c.drawString(40, y, f"Passagers: {reservation.get('passengers', 1)}")
    y -= 16
    
    # Reference
    ref_id = reservation.get('id', '')[:8].upper()
    c.drawString(40, y, f"Référence: #{ref_id}")
    
    # Invoice details (supplements)
    if invoice_details:
        y -= 25
        c.setFillColor(dark_color)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(40, y, "Détails / Suppléments:")
        y -= 16
        c.setFont("Helvetica", 10)
        c.setFillColor(gray_color)
        # Handle multiline
        for line in invoice_details.split('\n'):
            c.drawString(40, y, line.strip())
            y -= 14
    
    # Total box
    y -= 40
    c.setFillColor(light_gray)
    c.roundRect(40, y - 60, width - 80, 70, 10, fill=True, stroke=False)
    
    c.setFillColor(dark_color)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(60, y - 25, "TOTAL TTC")
    
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(dark_color)
    c.drawRightString(width - 60, y - 30, f"{final_price:.2f} €")
    
    # TVA mention
    y -= 85
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(gray_color)
    c.drawString(40, y, "TVA non applicable – art. 293 B du CGI")
    
    # Footer
    c.setFillColor(light_gray)
    c.rect(0, 0, width, 50, fill=True, stroke=False)
    
    c.setFillColor(gray_color)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 30, f"{COMPANY_INFO['name']} - {COMPANY_INFO['legal_name']} - SIRET: {COMPANY_INFO['siret']}")
    c.drawCentredString(width / 2, 18, f"{COMPANY_INFO['address']} - {COMPANY_INFO['email']}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# Email functions
async def send_confirmation_email(reservation: Reservation):
    if not reservation.email:
        return
    
    price_display = ""
    if reservation.estimated_price:
        price_display = f"""
            <tr>
                <td style="padding: 10px 0; color: #94A3B8; font-size: 14px;">Prix estimé</td>
                <td style="padding: 10px 0; color: #0F172A; font-weight: 600; font-size: 18px;">{int(reservation.estimated_price)}€</td>
            </tr>
        """
    
    html_content = f"""
    <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #0a0a0a; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">JABA DRIVER</h1>
            <p style="margin: 10px 0 0 0; font-size: 14px; color: #7dd3fc;">Service VTC Premium</p>
        </div>
        <div style="padding: 30px; background-color: #F8FAFC;">
            <h2 style="color: #0a0a0a; margin-top: 0;">Confirmation de réservation</h2>
            <p style="color: #64748B;">Bonjour <strong>{reservation.name}</strong>,</p>
            <p style="color: #64748B;">Votre réservation a bien été enregistrée.</p>
            
            <div style="background-color: white; padding: 20px; border-radius: 12px; margin: 20px 0;">
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8; font-size: 14px;">Date & Heure</td>
                        <td style="padding: 10px 0; color: #0a0a0a; font-weight: 600;">{reservation.date} à {reservation.time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8; font-size: 14px;">Départ</td>
                        <td style="padding: 10px 0; color: #0a0a0a;">{reservation.pickup_address}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8; font-size: 14px;">Arrivée</td>
                        <td style="padding: 10px 0; color: #0a0a0a;">{reservation.dropoff_address}</td>
                    </tr>
                    {price_display}
                </table>
            </div>
            
            <p style="color: #64748B; font-size: 14px;">Merci de votre confiance !</p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [reservation.email],
            "subject": f"JABA DRIVER - Confirmation de votre réservation du {reservation.date}",
            "html": html_content
        }
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"Confirmation email sent to {reservation.email}")
    except Exception as e:
        logger.error(f"Failed to send confirmation email: {str(e)}")

async def send_driver_alert(reservation: Reservation):
    if not DRIVER_EMAIL:
        return
    
    price_info = ""
    if reservation.estimated_price:
        distance_str = f"{reservation.distance_km:.1f} km" if reservation.distance_km else "N/A"
        duration_str = f"{int(reservation.duration_min)} min" if reservation.duration_min else "N/A"
        price_info = f"""
            <div style="background-color: #7dd3fc; color: #0a0a0a; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center;">
                <p style="margin: 0; font-size: 14px;">Prix estimé</p>
                <p style="margin: 5px 0 0 0; font-size: 28px; font-weight: bold;">{int(reservation.estimated_price)}€</p>
                <p style="margin: 5px 0 0 0; font-size: 12px;">{distance_str} • {duration_str}</p>
            </div>
        """
    
    html_content = f"""
    <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #7dd3fc; color: #0a0a0a; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">🚗 NOUVELLE RÉSERVATION</h1>
        </div>
        <div style="padding: 30px; background-color: #F8FAFC;">
            {price_info}
            <div style="background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="color: #0a0a0a; margin-top: 0;">Client</h3>
                <p style="margin: 5px 0;"><strong>Nom:</strong> {reservation.name}</p>
                <p style="margin: 5px 0;"><strong>Téléphone:</strong> <a href="tel:{reservation.phone}" style="color: #7dd3fc;">{reservation.phone}</a></p>
                {f'<p style="margin: 5px 0;"><strong>Email:</strong> {reservation.email}</p>' if reservation.email else ''}
            </div>
            
            <div style="background-color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                <h3 style="color: #0a0a0a; margin-top: 0;">Course</h3>
                <p style="margin: 5px 0;"><strong>Date:</strong> {reservation.date} à {reservation.time}</p>
                <p style="margin: 5px 0;"><strong>Départ:</strong> {reservation.pickup_address}</p>
                <p style="margin: 5px 0;"><strong>Arrivée:</strong> {reservation.dropoff_address}</p>
                <p style="margin: 5px 0;"><strong>Passagers:</strong> {reservation.passengers}</p>
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
    <div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background-color: #0a0a0a; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">JABA DRIVER</h1>
            <p style="margin: 10px 0 0 0; font-size: 14px; color: #7dd3fc;">Service VTC Premium</p>
        </div>
        <div style="padding: 30px; background-color: #F8FAFC;">
            <h2 style="color: #0a0a0a; margin-top: 0;">Votre facture</h2>
            <p style="color: #64748B;">Bonjour <strong>{reservation.get('name', '')}</strong>,</p>
            <p style="color: #64748B;">Veuillez trouver ci-joint votre facture n° <strong>{invoice_number}</strong> pour un montant de <strong>{final_price:.2f} €</strong>.</p>
            <p style="color: #64748B;">Merci pour votre confiance !</p>
            <p style="color: #64748B; margin-top: 30px;">Cordialement,<br/>JABA DRIVER</p>
        </div>
    </div>
    """
    
    # Encode PDF as base64
    pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
    
    params = {
        "from": SENDER_EMAIL,
        "to": [client_email],
        "subject": f"JABA DRIVER - Facture {invoice_number}",
        "html": html_content,
        "attachments": [
            {
                "filename": f"facture_{invoice_number}.pdf",
                "content": pdf_base64
            }
        ]
    }
    
    await asyncio.to_thread(resend.Emails.send, params)
    logger.info(f"Invoice email sent to {client_email}")

# Routes
@api_router.get("/")
async def root():
    return {"message": "JABA DRIVER API"}

@api_router.post("/reservations", response_model=Reservation)
async def create_reservation(input: ReservationCreate):
    reservation_dict = input.model_dump()
    reservation = Reservation(**reservation_dict)
    
    doc = reservation.model_dump()
    await db.reservations.insert_one(doc)
    
    asyncio.create_task(send_confirmation_email(reservation))
    asyncio.create_task(send_driver_alert(reservation))
    
    return reservation

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
        raise HTTPException(status_code=400, detail=f"Statut invalide")
    
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
        return {"success": True, "message": "Connexion réussie"}
    raise HTTPException(status_code=401, detail="Mot de passe incorrect")

# Invoice endpoints
@api_router.post("/reservations/{reservation_id}/invoice")
async def create_invoice(reservation_id: str, invoice_data: InvoiceCreate):
    """Generate invoice for a reservation"""
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    # Validate final price
    if invoice_data.final_price < 10:
        raise HTTPException(status_code=400, detail="Le prix minimum est de 10€")
    
    # Generate invoice number if not exists
    invoice_number = reservation.get("invoice_number")
    if not invoice_number:
        invoice_number = await generate_invoice_number()
    
    invoice_date = datetime.now().strftime("%d/%m/%Y")
    
    # Update reservation with invoice data
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
        "final_price": invoice_data.final_price,
        "message": "Facture générée"
    }

@api_router.get("/reservations/{reservation_id}/invoice/pdf")
async def download_invoice_pdf(reservation_id: str):
    """Download invoice PDF"""
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
    """Send invoice by email to client"""
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
        "Distance (km)", "Durée (min)", "Prix estimé (€)", 
        "N° Facture", "Prix final (€)", "Créé le"
    ])
    
    for r in reservations:
        writer.writerow([
            r.get("id", ""),
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
            r.get("created_at", "")
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
