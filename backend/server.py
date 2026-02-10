from fastapi import FastAPI, APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import io
import csv
import resend

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

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Models
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
    # New pricing fields
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
    # New pricing fields
    distance_km: Optional[float] = None
    duration_min: Optional[float] = None
    estimated_price: Optional[float] = None

class StatusUpdate(BaseModel):
    status: str

class AdminLogin(BaseModel):
    password: str

# Email functions
async def send_confirmation_email(reservation: Reservation):
    """Send confirmation email to client"""
    if not reservation.email:
        return
    
    # Format price display
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
            <p style="color: #64748B;">Votre réservation a bien été enregistrée. Voici les détails :</p>
            
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
                    <tr>
                        <td style="padding: 10px 0; color: #94A3B8; font-size: 14px;">Passagers</td>
                        <td style="padding: 10px 0; color: #0a0a0a;">{reservation.passengers}</td>
                    </tr>
                    {price_display}
                </table>
            </div>
            
            <p style="color: #64748B; font-size: 14px;">Nous vous contacterons bientôt pour confirmer votre course.</p>
            <p style="color: #64748B; font-size: 14px;">Merci de votre confiance !</p>
        </div>
        <div style="text-align: center; padding: 20px; color: #94A3B8; font-size: 12px;">
            <p>JABA DRIVER - Service VTC Premium</p>
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
    """Send alert email to driver"""
    if not DRIVER_EMAIL:
        return
    
    # Format price display
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
                {f'<p style="margin: 5px 0;"><strong>Bagages:</strong> {reservation.luggage}</p>' if reservation.luggage else ''}
                {f'<p style="margin: 5px 0;"><strong>Note:</strong> {reservation.notes}</p>' if reservation.notes else ''}
            </div>
            
            <a href="https://www.google.com/maps/dir/?api=1&origin={reservation.pickup_address}&destination={reservation.dropoff_address}" 
               style="display: block; background-color: #0a0a0a; color: white; text-align: center; padding: 15px; border-radius: 50px; text-decoration: none; font-weight: 600;">
                Voir l'itinéraire sur Google Maps
            </a>
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

# Routes
@api_router.get("/")
async def root():
    return {"message": "JABA DRIVER API"}

@api_router.post("/reservations", response_model=Reservation)
async def create_reservation(input: ReservationCreate):
    """Create a new reservation"""
    reservation_dict = input.model_dump()
    reservation = Reservation(**reservation_dict)
    
    doc = reservation.model_dump()
    await db.reservations.insert_one(doc)
    
    # Send emails asynchronously
    asyncio.create_task(send_confirmation_email(reservation))
    asyncio.create_task(send_driver_alert(reservation))
    
    return reservation

@api_router.get("/reservations", response_model=List[Reservation])
async def get_reservations(
    date: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Get all reservations with optional filters"""
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
    """Get a single reservation"""
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    return reservation

@api_router.patch("/reservations/{reservation_id}/status")
async def update_reservation_status(reservation_id: str, update: StatusUpdate):
    """Update reservation status"""
    valid_statuses = ["nouvelle", "confirmée", "effectuée", "annulée"]
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Statut invalide. Valeurs possibles: {valid_statuses}")
    
    result = await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": {"status": update.status}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    return {"message": "Statut mis à jour", "status": update.status}

@api_router.post("/admin/login")
async def admin_login(login: AdminLogin):
    """Admin login with password"""
    if login.password == ADMIN_PASSWORD:
        return {"success": True, "message": "Connexion réussie"}
    raise HTTPException(status_code=401, detail="Mot de passe incorrect")

@api_router.get("/reservations/export/csv")
async def export_reservations_csv(
    date: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Export reservations as CSV"""
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    
    reservations = await db.reservations.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header with new columns
    writer.writerow([
        "ID", "Nom", "Téléphone", "Email", "Départ", "Arrivée", 
        "Date", "Heure", "Passagers", "Bagages", "Notes", "Statut",
        "Distance (km)", "Durée (min)", "Prix estimé (€)", "Créé le"
    ])
    
    # Data
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
            r.get("luggage", ""),
            r.get("notes", ""),
            r.get("status", ""),
            r.get("distance_km", ""),
            r.get("duration_min", ""),
            r.get("estimated_price", ""),
            r.get("created_at", "")
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reservations_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

# Include the router in the main app
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
