# ============================================
# MODULE SOUS-TRAITANCE JABADRIVER
# ============================================
# Ce module est isolé du code principal pour éviter les régressions
# Il gère : courses, chauffeurs, claim tokens, paiements commission

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import secrets
import io
import asyncio
import resend

# PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

# Stripe integration - SDK natif
import stripe

logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================
COMMISSION_RATE = 0.10  # 10%
RESERVATION_DURATION_MINUTES = 3
CLAIM_TOKEN_EXPIRY_MINUTES = 30
SUBCONTRACTING_ENABLED = True  # Feature flag

# ============================================
# MODELS - CHAUFFEURS
# ============================================
class DriverCreate(BaseModel):
    email: str
    password: str
    company_name: str
    name: str
    phone: str
    address: str
    siret: str
    vat_applicable: bool = False
    vat_number: Optional[str] = None
    invoice_prefix: str = "DRI"

class DriverLogin(BaseModel):
    email: str
    password: str

class DriverProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    siret: Optional[str] = None
    vat_applicable: Optional[bool] = None
    vat_number: Optional[str] = None
    invoice_prefix: Optional[str] = None

class Driver(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str  # Simple hash for demo - use bcrypt in production
    company_name: str
    name: str
    phone: str
    address: str
    siret: str
    vat_applicable: bool = False
    vat_number: Optional[str] = None
    invoice_prefix: str = "DRI"
    invoice_next_number: int = 1
    is_active: bool = False  # Requires admin validation
    late_cancellation_count: int = 0  # Number of late cancellations (< 1h before pickup)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ============================================
# MODELS - COURSES SOUS-TRAITANCE
# ============================================
class CourseCreate(BaseModel):
    client_name: str
    client_email: str
    client_phone: str
    pickup_address: str
    dropoff_address: str
    date: str
    time: str
    distance_km: Optional[float] = None
    price_total: float
    notes: Optional[str] = None

class CourseStatusEnum:
    OPEN = "OPEN"
    RESERVED = "RESERVED"
    ASSIGNED = "ASSIGNED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"
    CANCELLED_LATE_DRIVER = "CANCELLED_LATE_DRIVER"  # Driver cancelled < 1h before pickup
    CANCELLED_LATE_CLIENT = "CANCELLED_LATE_CLIENT"  # Client cancelled < 1h before pickup

class Course(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    client_email: str
    client_phone: str
    pickup_address: str
    dropoff_address: str
    date: str
    time: str
    distance_km: Optional[float] = None
    price_total: float
    notes: Optional[str] = None
    admin_notes: Optional[str] = None  # Internal admin notes
    status: str = CourseStatusEnum.OPEN
    reserved_by_driver_id: Optional[str] = None
    reserved_until: Optional[str] = None
    assigned_driver_id: Optional[str] = None
    assigned_at: Optional[str] = None
    commission_rate: float = COMMISSION_RATE
    commission_amount: float = 0.0
    commission_paid: bool = False
    commission_paid_at: Optional[str] = None
    cancelled_at: Optional[str] = None
    cancelled_by: Optional[str] = None  # "driver" or "client"
    is_late_cancellation: bool = False  # True if cancelled < 1h before pickup
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ============================================
# MODELS - CLAIM TOKENS
# ============================================
class ClaimToken(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    expires_at: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ============================================
# MODELS - COMMISSION PAYMENTS
# ============================================
class CommissionPayment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    course_id: str
    driver_id: str
    provider: str = "stripe"
    provider_payment_id: Optional[str] = None
    session_id: Optional[str] = None
    amount: float
    currency: str = "eur"
    status: str = "pending"  # pending | paid | failed | refunded
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    paid_at: Optional[str] = None

# ============================================
# MODELS - ACTIVITY LOGS
# ============================================
class ActivityLogType:
    COURSE_CREATED = "course_created"
    COURSE_ASSIGNED = "course_assigned"
    COURSE_CANCELLED_DRIVER = "course_cancelled_driver"
    COURSE_CANCELLED_DRIVER_LATE = "course_cancelled_driver_late"
    COURSE_CANCELLED_CLIENT = "course_cancelled_client"
    COURSE_CANCELLED_CLIENT_LATE = "course_cancelled_client_late"
    COURSE_STATUS_CHANGED = "course_status_changed"
    DRIVER_ACTIVATED = "driver_activated"
    DRIVER_DEACTIVATED = "driver_deactivated"
    CLIENT_MODIFICATION_REQUEST = "client_modification_request"
    CLIENT_CANCELLATION_REQUEST = "client_cancellation_request"
    CLIENT_MESSAGE = "client_message"

class ActivityLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    log_type: str
    entity_type: str  # "course", "driver", "reservation"
    entity_id: str
    actor_type: Optional[str] = None  # "admin", "driver", "client", "system"
    actor_id: Optional[str] = None
    details: Optional[dict] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# ============================================
# ROUTER
# ============================================
subcontracting_router = APIRouter(prefix="/api/subcontracting", tags=["Sous-traitance"])
driver_router = APIRouter(prefix="/api/driver", tags=["Chauffeur"])
admin_subcontracting_router = APIRouter(prefix="/api/admin/subcontracting", tags=["Admin Sous-traitance"])

# Database reference - will be set from main server.py
db = None
STRIPE_API_KEY = None
ADMIN_EMAIL = None
SENDER_EMAIL = None
FRONTEND_URL = None

def init_subcontracting(database, stripe_key, admin_email=None, sender_email=None, frontend_url=None):
    """Initialize the subcontracting module with database and stripe key"""
    global db, STRIPE_API_KEY, ADMIN_EMAIL, SENDER_EMAIL, FRONTEND_URL
    db = database
    STRIPE_API_KEY = stripe_key
    ADMIN_EMAIL = admin_email
    SENDER_EMAIL = sender_email
    FRONTEND_URL = frontend_url
    logger.info("[SUBCONTRACTING] Module initialized")
    logger.info(f"[SUBCONTRACTING] Stripe API Key present: {bool(STRIPE_API_KEY)}")
    logger.info(f"[SUBCONTRACTING] Admin Email: {ADMIN_EMAIL}")

# ============================================
# HELPER FUNCTIONS
# ============================================

async def send_new_driver_notification(driver: dict):
    """Send email to admin when a new driver registers"""
    if not ADMIN_EMAIL or not SENDER_EMAIL:
        logger.warning("[EMAIL] Skipping new driver notification - ADMIN_EMAIL or SENDER_EMAIL not configured")
        return
    
    # Ensure resend API key is set
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    admin_url = f"{FRONTEND_URL}/admin/subcontracting" if FRONTEND_URL else "#"
    registration_date = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M")
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #3b82f6; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">👤 NOUVEAU CHAUFFEUR INSCRIT</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #92400e;">⏳ En attente de validation</p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #92400e;">Ce compte doit être validé avant que le chauffeur puisse réclamer des courses.</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📋 Informations du chauffeur</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 40%;">Nom :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{driver.get('name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Société :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{driver.get('company_name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Email :</td>
                        <td style="padding: 8px 0;"><a href="mailto:{driver.get('email', '')}">{driver.get('email', 'N/A')}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Téléphone :</td>
                        <td style="padding: 8px 0;"><a href="tel:{driver.get('phone', '')}">{driver.get('phone', 'N/A')}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">SIRET :</td>
                        <td style="padding: 8px 0;">{driver.get('siret', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Adresse :</td>
                        <td style="padding: 8px 0;">{driver.get('address', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Date d'inscription :</td>
                        <td style="padding: 8px 0;">{registration_date}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; margin: 25px 0;">
                <a href="{admin_url}" style="display: inline-block; background-color: #22c55e; color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                    ✅ Ouvrir / Valider le chauffeur
                </a>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    Module de sous-traitance
                </p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"👤 Nouveau chauffeur inscrit - {driver.get('name', 'N/A')} ({driver.get('company_name', 'N/A')})",
            "html": html_content
        }
        
        logger.info(f"[EMAIL] Sending new driver notification to admin | Driver: {driver.get('email')}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ New driver notification sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send new driver notification | Error: {str(e)}")
        logger.exception("Full exception trace:")

async def send_driver_validation_email(driver: dict):
    """Send email to driver when their account is validated by admin"""
    driver_email = driver.get('email')
    if not driver_email or not SENDER_EMAIL:
        logger.warning("[EMAIL] Skipping driver validation email - driver email or SENDER_EMAIL not configured")
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    driver_portal_url = f"{FRONTEND_URL}/driver/login" if FRONTEND_URL else "#"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #22c55e; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">✅ COMPTE VALIDÉ</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            
            <div style="background: #dcfce7; border-left: 4px solid #22c55e; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #166534;">🎉 Bienvenue {driver.get('name', '')} !</p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #166534;">Votre compte chauffeur a été validé par l'administrateur. Vous pouvez maintenant réclamer des courses.</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📋 Comment ça fonctionne ?</h3>
                <ol style="margin: 0; padding-left: 20px; color: #475569; line-height: 1.8;">
                    <li><strong>Réception du lien</strong> — Vous recevrez des liens de courses disponibles via WhatsApp ou autre</li>
                    <li><strong>Claim de la course</strong> — Cliquez sur le lien pour voir les détails et réserver la course pendant 3 minutes</li>
                    <li><strong>Paiement commission</strong> — Payez la commission de 10% via Stripe pour confirmer l'attribution</li>
                    <li><strong>Course attribuée</strong> — Une fois le paiement validé, la course vous est définitivement attribuée avec toutes les informations client</li>
                    <li><strong>Documents</strong> — Générez votre bon de commande et facture depuis votre espace chauffeur</li>
                </ol>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">👤 Votre profil</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Société :</td>
                        <td style="padding: 6px 0; font-weight: bold;">{driver.get('company_name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Email :</td>
                        <td style="padding: 6px 0;">{driver.get('email', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">SIRET :</td>
                        <td style="padding: 6px 0;">{driver.get('siret', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; margin: 25px 0;">
                <a href="{driver_portal_url}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                    🚗 Accéder à l'Espace Chauffeur
                </a>
            </div>
            
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; color: #475569; font-size: 13px;">
                    <strong>Besoin d'aide ?</strong><br/>
                    Contactez-nous via WhatsApp : <a href="https://wa.me/message/MQ6BTZ7KU26OM1" style="color: #25D366;">Cliquez ici</a><br/>
                    Email : contact@jabadriver.fr
                </p>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    Module de sous-traitance
                </p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [driver_email],
            "subject": f"✅ Votre compte chauffeur JABADRIVER est validé !",
            "html": html_content
        }
        
        logger.info(f"[EMAIL] Sending validation email to driver | Email: {driver_email}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver validation email sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver validation email | Error: {str(e)}")
        logger.exception("Full exception trace:")

async def send_course_assigned_notification(course: dict, driver: dict, payment_intent_id: str = None):
    """Send email to admin when a course is assigned to a driver after commission payment"""
    if not ADMIN_EMAIL or not SENDER_EMAIL:
        logger.warning("[EMAIL] Skipping course assigned notification - ADMIN_EMAIL or SENDER_EMAIL not configured")
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    admin_url = f"{FRONTEND_URL}/admin/subcontracting" if FRONTEND_URL else "#"
    
    # Extract city/department for privacy
    pickup_city = extract_city_department(course.get('pickup_address', ''))
    dropoff_city = extract_city_department(course.get('dropoff_address', ''))
    
    price_total = course.get('price_total', 0)
    commission_amount = course.get('commission_amount', round(price_total * COMMISSION_RATE, 2))
    assigned_at = course.get('assigned_at', datetime.now(timezone.utc).isoformat())
    
    # Format date
    try:
        dt = datetime.fromisoformat(assigned_at.replace('Z', '+00:00'))
        assigned_date_str = dt.strftime("%d/%m/%Y à %H:%M")
    except:
        assigned_date_str = assigned_at
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #22c55e; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">🎯 COURSE ATTRIBUÉE</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            
            <div style="background: #dcfce7; border-left: 4px solid #22c55e; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #166534;">✅ Commission payée — Course attribuée</p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #166534;">Un chauffeur a payé la commission et s'est vu attribuer cette course.</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📋 Détails de la course</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 40%;">ID Réservation :</td>
                        <td style="padding: 8px 0; font-weight: bold; font-family: monospace;">{course.get('id', 'N/A')[:8].upper()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Date/Heure :</td>
                        <td style="padding: 8px 0;">{course.get('date', 'N/A')} à {course.get('time', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Trajet :</td>
                        <td style="padding: 8px 0;">{pickup_city} → {dropoff_city}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Prix course :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{int(price_total)}€</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Commission (10%) :</td>
                        <td style="padding: 8px 0; font-weight: bold; color: #22c55e;">{commission_amount:.2f}€</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">👤 Chauffeur attribué</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 40%;">Nom :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{driver.get('name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Société :</td>
                        <td style="padding: 8px 0;">{driver.get('company_name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Email :</td>
                        <td style="padding: 8px 0;"><a href="mailto:{driver.get('email', '')}">{driver.get('email', 'N/A')}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Téléphone :</td>
                        <td style="padding: 8px 0;"><a href="tel:{driver.get('phone', '')}">{driver.get('phone', 'N/A')}</a></td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h4 style="margin: 0 0 10px 0; color: #475569;">💳 Paiement Stripe</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                    <tr>
                        <td style="padding: 4px 0; color: #64748b;">PaymentIntent :</td>
                        <td style="padding: 4px 0; font-family: monospace; font-size: 11px;">{payment_intent_id or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td style="padding: 4px 0; color: #64748b;">Date paiement :</td>
                        <td style="padding: 4px 0;">{assigned_date_str}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; margin: 25px 0;">
                <a href="{admin_url}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                    📋 Voir dans l'admin
                </a>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    Module de sous-traitance
                </p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"🎯 Course attribuée - {driver.get('name', 'N/A')} - {course.get('date', '')} {course.get('time', '')} - {int(commission_amount)}€ commission",
            "html": html_content
        }
        
        logger.info(f"[EMAIL] Sending course assigned notification to admin | Course: {course.get('id', '')[:8]}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Course assigned notification sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send course assigned notification | Error: {str(e)}")
        logger.exception("Full exception trace:")

async def send_driver_cancellation_notification(course: dict, driver: dict, is_late: bool):
    """Send email to driver when client cancels their assigned course"""
    driver_email = driver.get('email')
    if not driver_email or not SENDER_EMAIL:
        logger.warning("[EMAIL] Skipping driver cancellation notification - email not configured")
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    # Extract cities for privacy
    pickup_city = extract_city_department(course.get('pickup_address', ''))
    dropoff_city = extract_city_department(course.get('dropoff_address', ''))
    
    course_id_short = course.get('id', '')[:8].upper()
    commission_amount = course.get('commission_amount', 0)
    
    if is_late:
        # Late cancellation email
        subject = f"⚠️ Annulation tardive client — Course {course_id_short}"
        alert_box = f"""
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #dc2626;">⚠️ ANNULATION TARDIVE (< 1h avant prise en charge)</p>
                <p style="margin: 10px 0 0 0; font-size: 14px; color: #991b1b;">
                    Le client a annulé cette course moins d'1 heure avant la prise en charge.<br/>
                    <strong>La commission de {commission_amount:.2f}€ reste due / décision administrative selon conditions en vigueur.</strong>
                </p>
            </div>
        """
        header_bg = "#dc2626"
        header_title = "⚠️ ANNULATION TARDIVE CLIENT"
    else:
        # Normal cancellation email
        subject = f"❌ Course annulée par le client — {course_id_short}"
        alert_box = f"""
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #92400e;">❌ Course annulée</p>
                <p style="margin: 10px 0 0 0; font-size: 14px; color: #92400e;">
                    Le client a annulé cette course plus d'1 heure avant la prise en charge.
                </p>
            </div>
        """
        header_bg = "#f59e0b"
        header_title = "❌ COURSE ANNULÉE PAR LE CLIENT"
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: {header_bg}; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">{header_title}</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            
            {alert_box}
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📋 Détails de la course</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; color: #64748b; width: 40%;">ID Réservation :</td>
                        <td style="padding: 8px 0; font-weight: bold; font-family: monospace;">{course_id_short}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Date :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{course.get('date', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Heure prise en charge :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{course.get('time', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Trajet :</td>
                        <td style="padding: 8px 0;">{pickup_city} → {dropoff_city}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Prix course :</td>
                        <td style="padding: 8px 0;">{int(course.get('price_total', 0))}€</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; color: #64748b;">Commission payée :</td>
                        <td style="padding: 8px 0; font-weight: bold;">{commission_amount:.2f}€</td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; color: #475569; font-size: 13px;">
                    <strong>Besoin d'aide ?</strong><br/>
                    Contactez-nous via WhatsApp : <a href="https://wa.me/33756923711" style="color: #25D366;">+33 7 56 92 37 11</a><br/>
                    Email : contact@jabadriver.fr
                </p>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    Module de sous-traitance
                </p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [driver_email],
            "subject": subject,
            "html": html_content
        }
        
        logger.info(f"[EMAIL] Sending cancellation notification to driver | Course: {course_id_short} | Late: {is_late}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver cancellation notification sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver cancellation notification | Error: {str(e)}")
        logger.exception("Full exception trace:")

# ============================================
# EMAIL - ADMIN CANCELLATION (to client + driver)
# ============================================
async def send_admin_cancellation_to_client(course: dict):
    """Email to client when admin cancels the course"""
    client_email = course.get('client_email')
    if not client_email or not SENDER_EMAIL:
        logger.warning("[EMAIL] Skipping admin cancellation to client - email not configured")
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    pickup_city = extract_city_department(course.get('pickup_address', ''))
    dropoff_city = extract_city_department(course.get('dropoff_address', ''))
    course_id_short = course.get('id', '')[:8].upper()
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #dc2626; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">❌ RÉSERVATION ANNULÉE</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                Bonjour,<br/><br/>
                Votre réservation <strong>#{course_id_short}</strong> prévue le <strong>{course.get('date', 'N/A')}</strong> à <strong>{course.get('time', 'N/A')}</strong> a été annulée par l'administration Jabadriver.
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📍 Trajet</h3>
                <p style="margin: 5px 0;"><strong>Départ :</strong> {pickup_city}</p>
                <p style="margin: 5px 0;"><strong>Arrivée :</strong> {dropoff_city}</p>
            </div>
            
            <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                Si cette annulation fait suite à un ajustement logistique ou exceptionnel, nous vous invitons à nous contacter directement.
            </p>
            
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #475569; font-size: 13px;">
                    <strong>📞 Assistance :</strong> 07 56 92 37 11<br/>
                    <strong>💬 WhatsApp :</strong> <a href="https://wa.me/33756923711" style="color: #25D366;">Cliquez ici</a>
                </p>
            </div>
            
            <p style="color: #475569; font-size: 14px;">
                Nous restons à votre disposition.<br/><br/>
                Cordialement,<br/>
                <strong>JABADRIVER</strong><br/>
                Service VTC Premium
            </p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [client_email],
            "subject": f"Réservation annulée – Jabadriver",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending admin cancellation to client | Course: {course_id_short}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Admin cancellation to client sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send admin cancellation to client | Error: {str(e)}")

async def send_admin_cancellation_to_driver(course: dict, driver: dict):
    """Email to driver when admin cancels an assigned course"""
    driver_email = driver.get('email')
    if not driver_email or not SENDER_EMAIL:
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    pickup_city = extract_city_department(course.get('pickup_address', ''))
    dropoff_city = extract_city_department(course.get('dropoff_address', ''))
    course_id_short = course.get('id', '')[:8].upper()
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #dc2626; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">❌ COURSE ANNULÉE</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                Bonjour {driver.get('name', '')},<br/><br/>
                La réservation <strong>#{course_id_short}</strong> qui vous était attribuée a été annulée par l'administration.
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
                <p style="margin: 5px 0;"><strong>Date :</strong> {course.get('date', 'N/A')} à {course.get('time', 'N/A')}</p>
                <p style="margin: 5px 0;"><strong>Trajet :</strong> {pickup_city} → {dropoff_city}</p>
            </div>
            
            <p style="color: #475569; font-size: 14px;">
                Cordialement,<br/>
                <strong>JABADRIVER</strong>
            </p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [driver_email],
            "subject": f"Réservation annulée – Jabadriver",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending admin cancellation to driver | Course: {course_id_short}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Admin cancellation to driver sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send admin cancellation to driver | Error: {str(e)}")

# ============================================
# EMAIL - DRIVER CANCELLATION (to client + admin + driver confirmation)
# ============================================
async def send_driver_cancel_to_client(course: dict):
    """Email to client when driver cancels"""
    client_email = course.get('client_email')
    if not client_email or not SENDER_EMAIL:
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    course_id_short = course.get('id', '')[:8].upper()
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #f59e0b; color: #0a0a0a; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">⚠️ CHANGEMENT DE CHAUFFEUR</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                Bonjour,<br/><br/>
                Le chauffeur initialement attribué à votre réservation <strong>#{course_id_short}</strong> du <strong>{course.get('date', 'N/A')}</strong> à <strong>{course.get('time', 'N/A')}</strong> a annulé la prise en charge.
            </p>
            
            <div style="background: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #1e40af; font-size: 14px;">
                    <strong>Notre équipe est informée et traite immédiatement la situation.</strong>
                </p>
            </div>
            
            <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                Nous faisons le nécessaire pour :<br/>
                • vous proposer un autre chauffeur<br/>
                ou<br/>
                • confirmer l'annulation définitive selon disponibilité
            </p>
            
            <p style="color: #475569; font-size: 14px; margin-top: 20px;">
                Nous vous remercions pour votre compréhension.<br/><br/>
                <strong>JABADRIVER – Service Premium Île-de-France</strong><br/>
                Support : 07 56 92 37 11
            </p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [client_email],
            "subject": f"Votre chauffeur a annulé la course – Action en cours",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending driver cancel notification to client | Course: {course_id_short}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver cancel to client sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver cancel to client | Error: {str(e)}")

async def send_driver_cancel_to_admin(course: dict, driver: dict, is_late: bool):
    """Email to admin when driver cancels"""
    if not ADMIN_EMAIL or not SENDER_EMAIL:
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    pickup_city = extract_city_department(course.get('pickup_address', ''))
    dropoff_city = extract_city_department(course.get('dropoff_address', ''))
    course_id_short = course.get('id', '')[:8].upper()
    late_count = driver.get('late_cancellation_count', 0)
    
    late_warning = ""
    if is_late:
        late_warning = f"""
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #dc2626;">⚠️ ANNULATION TARDIVE (< 1h)</p>
                <p style="margin: 5px 0 0 0; font-size: 13px; color: #991b1b;">
                    Compteur annulations tardives chauffeur : <strong>{late_count}/3</strong>
                </p>
            </div>
        """
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #f59e0b; color: #0a0a0a; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">🚨 ANNULATION CHAUFFEUR</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            {late_warning}
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📋 Course annulée</h3>
                <p><strong>ID :</strong> {course_id_short}</p>
                <p><strong>Date :</strong> {course.get('date', 'N/A')} à {course.get('time', 'N/A')}</p>
                <p><strong>Trajet :</strong> {pickup_city} → {dropoff_city}</p>
                <p><strong>Client :</strong> {course.get('client_name', 'N/A')} - {course.get('client_phone', 'N/A')}</p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">👤 Chauffeur</h3>
                <p><strong>Nom :</strong> {driver.get('name', 'N/A')}</p>
                <p><strong>Société :</strong> {driver.get('company_name', 'N/A')}</p>
                <p><strong>Email :</strong> {driver.get('email', 'N/A')}</p>
                <p><strong>Annulations tardives :</strong> {late_count}/3</p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"🚨 Annulation chauffeur{' TARDIVE' if is_late else ''} – Course {course_id_short}",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending driver cancel notification to admin | Course: {course_id_short}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver cancel to admin sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver cancel to admin | Error: {str(e)}")

async def send_driver_cancel_confirmation(course: dict, driver: dict, is_late: bool, late_count: int):
    """Confirmation email to driver when they cancel"""
    driver_email = driver.get('email')
    if not driver_email or not SENDER_EMAIL:
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    course_id_short = course.get('id', '')[:8].upper()
    
    late_warning = ""
    if is_late:
        late_warning = f"""
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; font-weight: bold; color: #dc2626;">⚠️ ANNULATION TARDIVE</p>
                <p style="margin: 5px 0 0 0; font-size: 13px; color: #991b1b;">
                    Cette annulation a été comptabilisée comme tardive (< 1h avant prise en charge).<br/>
                    <strong>Compteur : {late_count}/3</strong>
                </p>
            </div>
        """
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #64748b; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">✅ CONFIRMATION D'ANNULATION</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                Bonjour {driver.get('name', '').split()[0] if driver.get('name') else ''},<br/><br/>
                Vous avez annulé la réservation <strong>#{course_id_short}</strong> prévue le <strong>{course.get('date', 'N/A')}</strong> à <strong>{course.get('time', 'N/A')}</strong>.
            </p>
            
            {late_warning}
            
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; font-weight: bold; color: #92400e;">⚠️ Rappel des règles Jabadriver</p>
                <ul style="margin: 10px 0 0 0; padding-left: 20px; color: #92400e; font-size: 13px;">
                    <li>Annulation < 1 heure avant prise en charge = annulation tardive</li>
                    <li><strong>3 annulations tardives entraînent la désactivation automatique du compte</strong></li>
                    <li>Les annulations répétées impactent la qualité de service et la priorité d'attribution</li>
                </ul>
            </div>
            
            <p style="color: #475569; font-size: 14px; margin-top: 20px;">
                Nous comptons sur votre professionnalisme.<br/><br/>
                Merci de votre engagement.<br/><br/>
                <strong>JABADRIVER – Plateforme Sous-Traitance</strong>
            </p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [driver_email],
            "subject": f"Confirmation d'annulation – Rappel des règles",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending cancel confirmation to driver | Course: {course_id_short}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Cancel confirmation to driver sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send cancel confirmation to driver | Error: {str(e)}")

# ============================================
# EMAIL - DRIVER AUTO-DEACTIVATION (3 late cancellations)
# ============================================
async def send_driver_deactivation_email(driver: dict):
    """Email to driver when auto-deactivated due to late cancellations"""
    driver_email = driver.get('email')
    if not driver_email or not SENDER_EMAIL:
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #dc2626; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">🚫 COMPTE DÉSACTIVÉ</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                Bonjour {driver.get('name', '').split()[0] if driver.get('name') else ''},<br/><br/>
                Suite à <strong>3 annulations tardives</strong> (moins d'1h avant prise en charge), votre compte a été <strong>automatiquement désactivé</strong> conformément aux règles de la plateforme.
            </p>
            
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #dc2626; font-size: 14px;">
                    Vous ne pouvez plus réclamer de courses tant que votre compte n'est pas réactivé.
                </p>
            </div>
            
            <p style="color: #475569; font-size: 14px; line-height: 1.6;">
                Pour toute demande de réactivation, merci de contacter l'administration :<br/>
                📧 contact@jabadriver.fr<br/>
                📞 07 56 92 37 11
            </p>
            
            <p style="color: #475569; font-size: 14px; margin-top: 20px;">
                Cordialement,<br/>
                <strong>JABADRIVER</strong>
            </p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [driver_email],
            "subject": f"Compte temporairement désactivé – Annulations tardives",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending deactivation email to driver | Driver: {driver.get('id', '')[:8]}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Deactivation email to driver sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send deactivation email to driver | Error: {str(e)}")

async def send_driver_deactivation_to_admin(driver: dict):
    """Email to admin when driver is auto-deactivated"""
    if not ADMIN_EMAIL or not SENDER_EMAIL:
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #dc2626; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">🚫 CHAUFFEUR DÉSACTIVÉ AUTO</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            <div style="background: white; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #dc2626;">Désactivation automatique</h3>
                <p><strong>Chauffeur :</strong> {driver.get('name', 'N/A')}</p>
                <p><strong>Société :</strong> {driver.get('company_name', 'N/A')}</p>
                <p><strong>Email :</strong> {driver.get('email', 'N/A')}</p>
                <p><strong>Raison :</strong> 3 annulations tardives (< 1h)</p>
            </div>
            
            <p style="color: #475569; font-size: 14px; margin-top: 20px;">
                Le chauffeur a été notifié. Réactivation manuelle possible depuis l'admin.
            </p>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [ADMIN_EMAIL],
            "subject": f"🚫 Chauffeur désactivé – {driver.get('name', 'N/A')} – 3 annulations tardives",
            "html": html_content
        }
        logger.info(f"[EMAIL] Sending driver deactivation to admin")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver deactivation to admin sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver deactivation to admin | Error: {str(e)}")

async def send_driver_registration_confirmation(driver: dict):
    """Send confirmation email to driver after registration (pending validation)"""
    driver_email = driver.get('email')
    if not driver_email or not SENDER_EMAIL:
        logger.warning("[EMAIL] Skipping driver registration confirmation - email not configured")
        return
    
    if not resend.api_key:
        resend.api_key = os.environ.get('RESEND_API_KEY', '')
    
    support_email = "contact@jabadriver.fr"
    driver_id_short = driver.get('id', '')[:8].upper()
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #3b82f6; color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0;">📋 DOSSIER REÇU</h1>
        </div>
        <div style="padding: 30px; background: #F8FAFC;">
            
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; font-weight: bold; color: #92400e;">⏳ En attente de validation</p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #92400e;">Votre dossier va être examiné par notre équipe. Votre compte sera activé une fois le dossier complet et validé.</p>
            </div>
            
            <p style="color: #475569; font-size: 15px; line-height: 1.6;">
                Bonjour <strong>{driver.get('name', '')}</strong>,<br/><br/>
                Merci pour votre inscription sur <strong>JABADRIVER</strong> !<br/><br/>
                Nous avons bien reçu votre demande d'inscription. Avant de pouvoir activer votre compte et vous permettre de réclamer des courses, nous devons vérifier votre dossier.
            </p>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #dc2626;">📎 Documents à fournir</h3>
                <p style="color: #475569; font-size: 14px; margin-bottom: 15px;">
                    Merci d'envoyer les pièces suivantes par email à <a href="mailto:{support_email}" style="color: #3b82f6; font-weight: bold;">{support_email}</a> :
                </p>
                <ol style="margin: 0; padding-left: 20px; color: #475569; line-height: 2;">
                    <li>Permis de conduire</li>
                    <li>Carte d'identité</li>
                    <li>Carte grise du véhicule</li>
                    <li>Assurance RC Circulation</li>
                    <li>Assurance RC PRO</li>
                    <li>KBIS ou SIREN</li>
                    <li>Carte VTC</li>
                    <li>Macaron VTC</li>
                    <li>Attestation d'inscription au registre VTC</li>
                </ol>
            </div>
            
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; color: #475569; font-size: 13px;">
                    <strong>💡 Important :</strong> Votre compte restera en statut "En attente de validation" tant que votre dossier n'est pas complet. Une fois validé, vous recevrez un email de confirmation.
                </p>
            </div>
            
            <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #e2e8f0;">
                <h3 style="margin-top: 0; color: #1e3a5f;">📝 Récapitulatif de votre inscription</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; width: 40%;">ID Chauffeur :</td>
                        <td style="padding: 6px 0; font-family: monospace; font-weight: bold;">{driver_id_short}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Nom :</td>
                        <td style="padding: 6px 0; font-weight: bold;">{driver.get('name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Société :</td>
                        <td style="padding: 6px 0;">{driver.get('company_name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Téléphone :</td>
                        <td style="padding: 6px 0;">{driver.get('phone', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Email :</td>
                        <td style="padding: 6px 0;">{driver.get('email', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">SIRET :</td>
                        <td style="padding: 6px 0;">{driver.get('siret', 'N/A')}</td>
                    </tr>
                </table>
            </div>
            
            <div style="text-align: center; margin: 25px 0;">
                <a href="mailto:{support_email}?subject=Dossier%20chauffeur%20{driver_id_short}%20-%20{driver.get('name', '').replace(' ', '%20')}" style="display: inline-block; background-color: #22c55e; color: white; padding: 16px 40px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 16px;">
                    📧 Envoyer mes documents
                </a>
            </div>
            
            <div style="background: #f1f5f9; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <p style="margin: 0; color: #475569; font-size: 13px;">
                    <strong>Besoin d'aide ?</strong><br/>
                    Contactez-nous via WhatsApp : <a href="https://wa.me/message/MQ6BTZ7KU26OM1" style="color: #25D366;">Cliquez ici</a><br/>
                    Email : <a href="mailto:{support_email}" style="color: #3b82f6;">{support_email}</a>
                </p>
            </div>
            
            <div style="text-align: center; margin: 20px 0; padding: 15px; background: #f8fafc; border-radius: 8px;">
                <p style="margin: 0; color: #64748b; font-size: 12px;">
                    <strong>JABADRIVER</strong><br/>
                    Service VTC Premium — Île-de-France
                </p>
            </div>
        </div>
    </div>
    """
    
    try:
        params = {
            "from": SENDER_EMAIL,
            "to": [driver_email],
            "subject": f"Jabadriver — Dossier reçu, en attente de validation",
            "html": html_content
        }
        
        logger.info(f"[EMAIL] Sending registration confirmation to driver | Email: {driver_email}")
        response = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL] ✅ Driver registration confirmation sent | Resend ID: {response.get('id', 'N/A')}")
    except Exception as e:
        logger.error(f"[EMAIL] ❌ Failed to send driver registration confirmation | Error: {str(e)}")
        logger.exception("Full exception trace:")

def simple_hash(password: str) -> str:
    """Simple hash for demo - use bcrypt in production"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return simple_hash(password) == password_hash

async def create_activity_log(
    log_type: str,
    entity_type: str,
    entity_id: str,
    actor_type: str = None,
    actor_id: str = None,
    details: dict = None
):
    """Create an activity log entry"""
    log = ActivityLog(
        log_type=log_type,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_type=actor_type,
        actor_id=actor_id,
        details=details
    )
    await db.activity_logs.insert_one(log.model_dump())
    logger.info(f"[ACTIVITY LOG] {log_type} | {entity_type}:{entity_id[:8]} | Actor: {actor_type}:{actor_id[:8] if actor_id else 'N/A'}")
    return log

def is_late_cancellation(course_date: str, course_time: str) -> bool:
    """Check if cancellation is < 1h before pickup"""
    try:
        pickup_datetime = datetime.fromisoformat(f"{course_date}T{course_time}")
        now = datetime.now()
        time_until_pickup = pickup_datetime - now
        return time_until_pickup.total_seconds() < 3600  # Less than 1 hour
    except Exception as e:
        logger.error(f"Error checking late cancellation: {e}")
        return False

async def get_driver_from_token(authorization: str) -> dict:
    """Extract driver from JWT-like token (simplified)"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = authorization.replace("Bearer ", "")
    # Simple token format: driver_id (for demo)
    driver = await db.drivers.find_one({"id": token}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=401, detail="Token invalide")
    if not driver.get("is_active"):
        raise HTTPException(status_code=403, detail="Compte chauffeur non activé. Contactez l'administrateur.")
    return driver

async def check_and_expire_reservation(course: dict) -> dict:
    """Check if reservation has expired and reset to OPEN if so"""
    if course.get("status") == CourseStatusEnum.RESERVED:
        reserved_until = course.get("reserved_until")
        if reserved_until:
            expiry = datetime.fromisoformat(reserved_until.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expiry:
                # Reservation expired - reset to OPEN
                await db.courses.update_one(
                    {"id": course["id"]},
                    {"$set": {
                        "status": CourseStatusEnum.OPEN,
                        "reserved_by_driver_id": None,
                        "reserved_until": None
                    }}
                )
                course["status"] = CourseStatusEnum.OPEN
                course["reserved_by_driver_id"] = None
                course["reserved_until"] = None
                logger.info(f"[SUBCONTRACTING] Course {course['id'][:8]} reservation expired, reset to OPEN")
    return course

# ============================================
# DRIVER AUTHENTICATION ROUTES
# ============================================
@driver_router.post("/register")
async def register_driver(data: DriverCreate):
    """Register a new driver account (requires admin validation)"""
    if not SUBCONTRACTING_ENABLED:
        raise HTTPException(status_code=503, detail="Module sous-traitance désactivé")
    
    # Check if email already exists
    existing = await db.drivers.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Cet email est déjà utilisé")
    
    driver = Driver(
        email=data.email,
        password_hash=simple_hash(data.password),
        company_name=data.company_name,
        name=data.name,
        phone=data.phone,
        address=data.address,
        siret=data.siret,
        vat_applicable=data.vat_applicable,
        vat_number=data.vat_number,
        invoice_prefix=data.invoice_prefix,
        is_active=False  # Requires admin validation
    )
    
    driver_dict = driver.model_dump()
    await db.drivers.insert_one(driver_dict)
    logger.info(f"[DRIVER] New driver registered: {data.email} (pending validation)")
    
    # Send confirmation email to driver (pending validation)
    try:
        await send_driver_registration_confirmation(driver_dict)
    except Exception as e:
        logger.error(f"[DRIVER] Failed to send registration confirmation to driver: {str(e)}")
    
    # Send notification email to admin
    try:
        await send_new_driver_notification(driver_dict)
    except Exception as e:
        logger.error(f"[DRIVER] Failed to send admin notification: {str(e)}")
    
    return {
        "message": "Inscription réussie. Votre compte doit être validé par l'administrateur.",
        "driver_id": driver.id,
        "is_active": False
    }

@driver_router.post("/login")
async def login_driver(data: DriverLogin):
    """Login driver and return token"""
    if not SUBCONTRACTING_ENABLED:
        raise HTTPException(status_code=503, detail="Module sous-traitance désactivé")
    
    driver = await db.drivers.find_one({"email": data.email}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if not verify_password(data.password, driver["password_hash"]):
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
    
    if not driver.get("is_active"):
        raise HTTPException(status_code=403, detail="Votre compte n'est pas encore activé. Contactez l'administrateur.")
    
    # Return simple token (driver_id) - use JWT in production
    return {
        "token": driver["id"],
        "driver": {
            "id": driver["id"],
            "email": driver["email"],
            "name": driver["name"],
            "company_name": driver["company_name"],
            "is_active": driver["is_active"]
        }
    }

@driver_router.get("/profile")
async def get_driver_profile(request: Request):
    """Get current driver profile"""
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    # Remove password hash from response
    driver.pop("password_hash", None)
    return driver

@driver_router.put("/profile")
async def update_driver_profile(request: Request, data: DriverProfileUpdate):
    """Update driver profile"""
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if update_data:
        await db.drivers.update_one({"id": driver["id"]}, {"$set": update_data})
    
    updated = await db.drivers.find_one({"id": driver["id"]}, {"_id": 0, "password_hash": 0})
    return updated

# ============================================
# DRIVER COURSES ROUTES
# ============================================
@driver_router.get("/courses")
async def get_driver_courses(request: Request):
    """Get courses assigned to current driver"""
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    courses = await db.courses.find(
        {"assigned_driver_id": driver["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return courses

@driver_router.get("/courses/{course_id}")
async def get_driver_course_detail(request: Request, course_id: str):
    """Get specific course details"""
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    course = await db.courses.find_one(
        {"id": course_id, "assigned_driver_id": driver["id"]},
        {"_id": 0}
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    return course

# ============================================
# DRIVER CANCELLATION
# ============================================
@driver_router.post("/courses/{course_id}/cancel")
async def driver_cancel_course(request: Request, course_id: str, reason: Optional[str] = None):
    """Driver cancels an assigned course"""
    authorization = request.headers.get("Authorization", "")
    driver = await get_driver_from_token(authorization)
    
    # Get course
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Verify driver is assigned to this course
    if course.get("assigned_driver_id") != driver["id"]:
        raise HTTPException(status_code=403, detail="Vous n'êtes pas assigné à cette course")
    
    # Only assigned courses can be cancelled by driver
    if course.get("status") != CourseStatusEnum.ASSIGNED:
        raise HTTPException(status_code=400, detail="Cette course ne peut pas être annulée")
    
    # Check if late cancellation
    is_late = is_late_cancellation(course["date"], course["time"])
    
    # Determine new status
    new_status = CourseStatusEnum.CANCELLED_LATE_DRIVER if is_late else CourseStatusEnum.CANCELLED
    
    # Update course
    update_data = {
        "status": new_status,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancelled_by": "driver",
        "is_late_cancellation": is_late,
        "admin_notes": f"Annulation chauffeur{' (tardive < 1h)' if is_late else ''}: {reason or 'Aucune raison fournie'}"
    }
    await db.courses.update_one({"id": course_id}, {"$set": update_data})
    
    # If late cancellation, increment driver's late cancellation count
    if is_late:
        await db.drivers.update_one(
            {"id": driver["id"]},
            {"$inc": {"late_cancellation_count": 1}}
        )
        logger.warning(f"[SUBCONTRACTING] ⚠️ Late cancellation by driver {driver['id'][:8]} for course {course_id[:8]}")
    
    # Create activity log
    await create_activity_log(
        log_type=ActivityLogType.COURSE_CANCELLED_DRIVER_LATE if is_late else ActivityLogType.COURSE_CANCELLED_DRIVER,
        entity_type="course",
        entity_id=course_id,
        actor_type="driver",
        actor_id=driver["id"],
        details={
            "reason": reason,
            "is_late_cancellation": is_late,
            "commission_paid": course.get("commission_paid", False),
            "commission_amount": course.get("commission_amount", 0)
        }
    )
    
    # Note: Commission is NOT refunded for late cancellations
    message = "Course annulée."
    if is_late:
        message = "Course annulée. ⚠️ Annulation tardive (< 1h avant prise en charge) : la commission reste due."
    
    return {
        "message": message,
        "is_late_cancellation": is_late,
        "commission_refunded": False  # Never refund automatically
    }

# ============================================
# CLAIM ROUTES (PUBLIC WITH AUTH)
# ============================================

def extract_city_department(address: str) -> str:
    """Extract city and department from full address for privacy"""
    if not address:
        return "Non spécifié"
    
    # Common patterns for French addresses
    parts = address.split(',')
    
    # Try to find postal code pattern (5 digits)
    import re
    postal_match = re.search(r'\b(\d{5})\b', address)
    
    if postal_match:
        postal = postal_match.group(1)
        dept = postal[:2]
        # Find city name near postal code
        for i, part in enumerate(parts):
            if postal in part:
                city_part = part.strip()
                # Extract just city name
                city = re.sub(r'\d{5}', '', city_part).strip()
                if city:
                    return f"{city} ({dept})"
                elif i > 0:
                    return f"{parts[i-1].strip()} ({dept})"
    
    # Fallback: return last meaningful part
    if len(parts) >= 2:
        return parts[-1].strip()
    
    # If no comma, try to extract last words
    words = address.split()
    if len(words) >= 2:
        return ' '.join(words[-2:])
    
    return address[:30] + "..."

@subcontracting_router.get("/claim/{token}")
async def get_claim_info(token: str):
    """Get course info from claim token (public) - MASKED for security"""
    if not SUBCONTRACTING_ENABLED:
        raise HTTPException(status_code=503, detail="Module sous-traitance désactivé")
    
    # Find claim token
    claim = await db.claim_tokens.find_one({"token": token}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Lien invalide ou expiré")
    
    # Check token expiry
    expires_at = datetime.fromisoformat(claim["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=410, detail="Lien expiré")
    
    # Get course
    course = await db.courses.find_one({"id": claim["course_id"]}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Check and expire reservation if needed
    course = await check_and_expire_reservation(course)
    
    # Calculate commission
    commission_amount = round(course["price_total"] * COMMISSION_RATE, 2)
    
    # Get reserved driver info if any
    reserved_driver_name = None
    time_remaining = None
    if course.get("status") == CourseStatusEnum.RESERVED and course.get("reserved_by_driver_id"):
        reserved_driver = await db.drivers.find_one({"id": course["reserved_by_driver_id"]}, {"_id": 0})
        if reserved_driver:
            reserved_driver_name = reserved_driver.get("name", "Chauffeur")
        if course.get("reserved_until"):
            expiry = datetime.fromisoformat(course["reserved_until"].replace('Z', '+00:00'))
            remaining = (expiry - datetime.now(timezone.utc)).total_seconds()
            time_remaining = max(0, int(remaining))
    
    # SECURITY: Mask sensitive info before payment
    # Only show: client name, price, date/time, city+dept, commission
    # Hide: full addresses, phone, email, notes
    is_assigned = course["status"] == CourseStatusEnum.ASSIGNED
    
    # Extract city + department only (not full address)
    pickup_masked = extract_city_department(course["pickup_address"])
    dropoff_masked = extract_city_department(course["dropoff_address"])
    
    return {
        "course": {
            "id": course["id"],
            "client_name": course["client_name"],
            # Masked addresses - only city + department
            "pickup_location": pickup_masked,
            "dropoff_location": dropoff_masked,
            # Full addresses only if ASSIGNED (after payment)
            "pickup_address": course["pickup_address"] if is_assigned else None,
            "dropoff_address": course["dropoff_address"] if is_assigned else None,
            "date": course["date"],
            "time": course["time"],
            "distance_km": course.get("distance_km"),
            "price_total": course["price_total"],
            # Sensitive info hidden before payment
            "client_phone": course.get("client_phone") if is_assigned else None,
            "client_email": course.get("client_email") if is_assigned else None,
            "notes": course.get("notes") if is_assigned else None,
            "status": course["status"]
        },
        "commission_rate": COMMISSION_RATE,
        "commission_amount": commission_amount,
        "reserved_by": reserved_driver_name,
        "time_remaining_seconds": time_remaining,
        "claim_expires_at": claim["expires_at"],
        "is_assigned": is_assigned
    }

@subcontracting_router.post("/claim/{token}/reserve")
async def reserve_course(token: str, request: Request):
    """Reserve a course for 3 minutes (requires driver auth)"""
    if not SUBCONTRACTING_ENABLED:
        raise HTTPException(status_code=503, detail="Module sous-traitance désactivé")
    
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    # Find claim token
    claim = await db.claim_tokens.find_one({"token": token}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Lien invalide")
    
    # Check token expiry
    expires_at = datetime.fromisoformat(claim["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(status_code=410, detail="Lien expiré")
    
    # Get course with atomic check
    course = await db.courses.find_one({"id": claim["course_id"]}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Check and expire old reservation if needed
    course = await check_and_expire_reservation(course)
    
    # Check current status
    if course["status"] == CourseStatusEnum.ASSIGNED:
        raise HTTPException(status_code=409, detail="Désolé, cette course est déjà attribuée à un autre chauffeur")
    
    if course["status"] == CourseStatusEnum.RESERVED:
        if course.get("reserved_by_driver_id") == driver["id"]:
            # Already reserved by this driver
            return {
                "message": "Vous avez déjà réservé cette course",
                "reserved_until": course["reserved_until"],
                "status": "RESERVED"
            }
        else:
            raise HTTPException(status_code=409, detail="Course déjà réservée par un autre chauffeur. Réessayez dans quelques minutes.")
    
    if course["status"] != CourseStatusEnum.OPEN:
        raise HTTPException(status_code=409, detail=f"Course non disponible (statut: {course['status']})")
    
    # Atomic reservation - use findOneAndUpdate to prevent race conditions
    reserved_until = (datetime.now(timezone.utc) + timedelta(minutes=RESERVATION_DURATION_MINUTES)).isoformat()
    
    result = await db.courses.find_one_and_update(
        {
            "id": claim["course_id"],
            "status": CourseStatusEnum.OPEN
        },
        {
            "$set": {
                "status": CourseStatusEnum.RESERVED,
                "reserved_by_driver_id": driver["id"],
                "reserved_until": reserved_until
            }
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=409, detail="Course non disponible - un autre chauffeur a été plus rapide")
    
    logger.info(f"[SUBCONTRACTING] Course {claim['course_id'][:8]} reserved by driver {driver['id'][:8]} until {reserved_until}")
    
    return {
        "message": "Course réservée ! Vous avez 3 minutes pour payer la commission.",
        "reserved_until": reserved_until,
        "status": "RESERVED",
        "commission_amount": round(course["price_total"] * COMMISSION_RATE, 2)
    }

@subcontracting_router.post("/claim/{token}/pay")
async def initiate_payment(token: str, request: Request):
    """Create Stripe checkout session for commission payment"""
    if not SUBCONTRACTING_ENABLED:
        raise HTTPException(status_code=503, detail="Module sous-traitance désactivé")
    
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Paiement non configuré - clé Stripe manquante")
    
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    # Find claim token
    claim = await db.claim_tokens.find_one({"token": token}, {"_id": 0})
    if not claim:
        raise HTTPException(status_code=404, detail="Lien invalide")
    
    # Get course
    course = await db.courses.find_one({"id": claim["course_id"]}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Check course is reserved by this driver
    if course["status"] != CourseStatusEnum.RESERVED:
        raise HTTPException(status_code=409, detail="Vous devez d'abord réserver la course")
    
    if course.get("reserved_by_driver_id") != driver["id"]:
        raise HTTPException(status_code=403, detail="Cette course n'est pas réservée par vous")
    
    # Check reservation hasn't expired
    reserved_until = course.get("reserved_until")
    if reserved_until:
        expiry = datetime.fromisoformat(reserved_until.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expiry:
            raise HTTPException(status_code=410, detail="Votre réservation a expiré")
    
    # Calculate commission (amount in cents for Stripe)
    commission_amount = round(course["price_total"] * COMMISSION_RATE, 2)
    commission_cents = int(commission_amount * 100)
    
    # Get host URL for redirect - detect from request host, ignore FRONTEND_URL
    try:
        body = await request.json()
    except:
        body = {}
    
    # Detect base URL from request host
    host = request.headers.get("host", "")
    if "jabadriver.fr" in host:
        origin_url = "https://jabadriver.fr"
    else:
        # Preview or other environment - use request base
        origin_url = body.get("origin_url", "").rstrip("/")
        if not origin_url:
            origin_header = request.headers.get("origin") or request.headers.get("referer")
            if origin_header:
                from urllib.parse import urlparse
                parsed = urlparse(origin_header)
                origin_url = f"{parsed.scheme}://{parsed.netloc}"
            else:
                base = str(request.base_url).rstrip("/")
                origin_url = base.split("/api")[0]
    
    logger.info(f"[STRIPE] BASE_URL_USED={origin_url}")
    
    # Build URLs - success page will verify payment
    success_url = f"{origin_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}&course_id={course['id']}"
    cancel_url = f"{origin_url}/claim/{token}?payment=cancelled"
    
    logger.info(f"[STRIPE] Creating checkout session...")
    logger.info(f"[STRIPE] API Key: {STRIPE_API_KEY[:12]}...")
    logger.info(f"[STRIPE] Amount: {commission_amount}€ ({commission_cents} cents)")
    logger.info(f"[STRIPE] Success URL: {success_url}")
    logger.info(f"[STRIPE] Cancel URL: {cancel_url}")
    
    try:
        # Configure Stripe with API key
        stripe.api_key = STRIPE_API_KEY
        
        # Create Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f'Commission course VTC - {course["client_name"]}',
                        'description': f'Course du {course["date"]} - {course["pickup_address"][:30]}... → {course["dropoff_address"][:30]}...',
                    },
                    'unit_amount': commission_cents,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'course_id': course['id'],
                'driver_id': driver['id'],
                'claim_token': token,
                'type': 'commission_payment'
            },
            customer_email=driver.get('email'),
        )
        
        logger.info(f"[STRIPE] ✅ Session created successfully!")
        logger.info(f"[STRIPE] Session ID: {session.id}")
        logger.info(f"[STRIPE] Checkout URL: {session.url}")
        
        # Create payment record
        payment = CommissionPayment(
            course_id=course["id"],
            driver_id=driver["id"],
            session_id=session.id,
            amount=commission_amount,
            currency="eur",
            status="pending"
        )
        await db.commission_payments.insert_one(payment.model_dump())
        
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "amount": commission_amount,
            "currency": "eur"
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"[STRIPE] ❌ Stripe error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur Stripe: {str(e)}")
    except Exception as e:
        logger.error(f"[STRIPE] ❌ Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur création paiement: {str(e)}")

@subcontracting_router.get("/payment/status/{session_id}")
async def get_payment_status(session_id: str, request: Request):
    """Check payment status and finalize attribution if paid"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Paiement non configuré")
    
    logger.info(f"[STRIPE] Checking payment status for session: {session_id}")
    
    # Get payment record from DB
    payment = await db.commission_payments.find_one({"session_id": session_id}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Paiement non trouvé dans la base")
    
    try:
        # Configure Stripe
        stripe.api_key = STRIPE_API_KEY
        
        # Retrieve session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        logger.info(f"[STRIPE] Session status: {session.status}")
        logger.info(f"[STRIPE] Payment status: {session.payment_status}")
        
        payment_status = session.payment_status  # 'unpaid', 'paid', 'no_payment_required'
        
        if payment_status == "paid" and payment["status"] != "paid":
            # Payment successful - finalize attribution
            logger.info(f"[STRIPE] ✅ Payment confirmed! Finalizing attribution...")
            await finalize_attribution(payment["course_id"], payment["driver_id"], session_id)
            
            # Update payment record
            await db.commission_payments.update_one(
                {"session_id": session_id},
                {"$set": {
                    "status": "paid",
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                    "provider_payment_id": session.payment_intent
                }}
            )
            
            return {
                "status": "paid",
                "payment_status": "paid",
                "message": "Paiement confirmé ! La course vous est attribuée.",
                "course_id": payment["course_id"],
                "amount": payment["amount"]
            }
        
        return {
            "status": payment["status"],
            "payment_status": payment_status,
            "message": "En attente de paiement" if payment_status == "unpaid" else f"Statut: {payment_status}",
            "amount": payment["amount"],
            "currency": payment["currency"]
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"[STRIPE] Error checking status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur Stripe: {str(e)}")

# New endpoint for verifying payment after redirect
@subcontracting_router.get("/verify-payment")
async def verify_payment(session_id: str):
    """Verify payment status after Stripe redirect - called from success page"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Paiement non configuré")
    
    logger.info(f"[STRIPE VERIFY] Verifying session: {session_id}")
    
    try:
        stripe.api_key = STRIPE_API_KEY
        session = stripe.checkout.Session.retrieve(session_id)
        
        logger.info(f"[STRIPE VERIFY] Session {session_id[:20]}...")
        logger.info(f"[STRIPE VERIFY] Status: {session.status}")
        logger.info(f"[STRIPE VERIFY] Payment Status: {session.payment_status}")
        
        # Get payment record
        payment = await db.commission_payments.find_one({"session_id": session_id}, {"_id": 0})
        
        if session.payment_status == "paid":
            if payment and payment["status"] != "paid":
                # Finalize attribution
                await finalize_attribution(payment["course_id"], payment["driver_id"], session_id)
                
                await db.commission_payments.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": "paid",
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                        "provider_payment_id": session.payment_intent
                    }}
                )
            
            return {
                "success": True,
                "payment_status": "paid",
                "message": "Paiement confirmé ! La course vous est attribuée.",
                "course_id": payment["course_id"] if payment else None,
                "amount": session.amount_total / 100,
                "currency": session.currency
            }
        else:
            return {
                "success": False,
                "payment_status": session.payment_status,
                "message": "Paiement non confirmé",
                "session_status": session.status
            }
            
    except stripe.error.StripeError as e:
        logger.error(f"[STRIPE VERIFY] Error: {str(e)}")
        return {
            "success": False,
            "payment_status": "error",
            "message": f"Erreur vérification: {str(e)}"
        }

async def finalize_attribution(course_id: str, driver_id: str, payment_session_id: str):
    """Finalize course attribution after successful payment"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        logger.error(f"[SUBCONTRACTING] Course {course_id} not found for attribution")
        return False
    
    # Check if course is still reserved by this driver
    if course["status"] == CourseStatusEnum.ASSIGNED:
        if course.get("assigned_driver_id") == driver_id:
            logger.info(f"[SUBCONTRACTING] Course {course_id[:8]} already assigned to driver {driver_id[:8]}")
            return True
        else:
            # Course assigned to someone else - should refund
            logger.error(f"[SUBCONTRACTING] Course {course_id[:8]} already assigned to different driver - REFUND NEEDED")
            return False
    
    # Finalize attribution
    commission_amount = round(course["price_total"] * COMMISSION_RATE, 2)
    
    await db.courses.update_one(
        {"id": course_id},
        {"$set": {
            "status": CourseStatusEnum.ASSIGNED,
            "assigned_driver_id": driver_id,
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "commission_amount": commission_amount,
            "commission_paid": True,
            "commission_paid_at": datetime.now(timezone.utc).isoformat(),
            "reserved_by_driver_id": None,
            "reserved_until": None
        }}
    )
    
    logger.info(f"[SUBCONTRACTING] ✅ Course {course_id[:8]} ASSIGNED to driver {driver_id[:8]}")
    
    # Send email notification to admin
    try:
        driver = await db.drivers.find_one({"id": driver_id}, {"_id": 0, "password_hash": 0})
        updated_course = await db.courses.find_one({"id": course_id}, {"_id": 0})
        
        # Get payment intent ID from commission_payments
        payment = await db.commission_payments.find_one({"session_id": payment_session_id}, {"_id": 0})
        payment_intent_id = payment.get("provider_payment_id") if payment else None
        
        if driver and updated_course:
            await send_course_assigned_notification(updated_course, driver, payment_intent_id)
    except Exception as e:
        logger.error(f"[SUBCONTRACTING] Failed to send assignment notification: {str(e)}")
        # Don't fail attribution if email fails
    
    return True

# ============================================
# ADMIN ROUTES - COURSES MANAGEMENT
# ============================================
@admin_subcontracting_router.get("/courses")
async def admin_get_all_courses():
    """Get all subcontracting courses with driver info"""
    courses = await db.courses.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Enrich with driver info
    for course in courses:
        if course.get("assigned_driver_id"):
            driver = await db.drivers.find_one({"id": course["assigned_driver_id"]}, {"_id": 0, "password_hash": 0})
            course["assigned_driver"] = driver
        
        # Check and update expired reservations
        await check_and_expire_reservation(course)
    
    return courses

@admin_subcontracting_router.post("/courses")
async def admin_create_course(data: CourseCreate):
    """Create a new course for subcontracting"""
    if not SUBCONTRACTING_ENABLED:
        raise HTTPException(status_code=503, detail="Module sous-traitance désactivé")
    
    course = Course(
        client_name=data.client_name,
        client_email=data.client_email,
        client_phone=data.client_phone,
        pickup_address=data.pickup_address,
        dropoff_address=data.dropoff_address,
        date=data.date,
        time=data.time,
        distance_km=data.distance_km,
        price_total=data.price_total,
        notes=data.notes,
        commission_amount=round(data.price_total * COMMISSION_RATE, 2)
    )
    
    await db.courses.insert_one(course.model_dump())
    
    # Generate claim token
    claim_token = ClaimToken(
        course_id=course.id,
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=CLAIM_TOKEN_EXPIRY_MINUTES)).isoformat()
    )
    await db.claim_tokens.insert_one(claim_token.model_dump())
    
    logger.info(f"[SUBCONTRACTING] New course created: {course.id[:8]}, token: {claim_token.token[:8]}...")
    
    return {
        "course": course.model_dump(),
        "claim_token": claim_token.token,
        "claim_url": f"/claim/{claim_token.token}"
    }

@admin_subcontracting_router.get("/courses/{course_id}")
async def admin_get_course(course_id: str):
    """Get course details with full info"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Check expiration
    course = await check_and_expire_reservation(course)
    
    # Get driver info
    if course.get("assigned_driver_id"):
        driver = await db.drivers.find_one({"id": course["assigned_driver_id"]}, {"_id": 0, "password_hash": 0})
        course["assigned_driver"] = driver
    
    if course.get("reserved_by_driver_id"):
        driver = await db.drivers.find_one({"id": course["reserved_by_driver_id"]}, {"_id": 0, "password_hash": 0})
        course["reserved_by_driver"] = driver
    
    # Get claim tokens
    tokens = await db.claim_tokens.find({"course_id": course_id}, {"_id": 0}).to_list(10)
    course["claim_tokens"] = tokens
    
    # Get payments
    payments = await db.commission_payments.find({"course_id": course_id}, {"_id": 0}).to_list(10)
    course["payments"] = payments
    
    return course

@admin_subcontracting_router.post("/courses/{course_id}/regenerate-token")
async def admin_regenerate_claim_token(course_id: str):
    """Regenerate claim token for a course"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Invalidate old tokens by setting very short expiry
    await db.claim_tokens.update_many(
        {"course_id": course_id},
        {"$set": {"expires_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create new token
    claim_token = ClaimToken(
        course_id=course_id,
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=CLAIM_TOKEN_EXPIRY_MINUTES)).isoformat()
    )
    await db.claim_tokens.insert_one(claim_token.model_dump())
    
    logger.info(f"[SUBCONTRACTING] Token regenerated for course {course_id[:8]}")
    
    return {
        "claim_token": claim_token.token,
        "expires_at": claim_token.expires_at
    }

@admin_subcontracting_router.post("/courses/{course_id}/reset-to-open")
async def admin_reset_course_to_open(course_id: str):
    """Reset course to OPEN status (admin override)"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    if course["status"] == CourseStatusEnum.ASSIGNED and course.get("commission_paid"):
        raise HTTPException(status_code=400, detail="Cannot reset - commission already paid. Consider refund first.")
    
    await db.courses.update_one(
        {"id": course_id},
        {"$set": {
            "status": CourseStatusEnum.OPEN,
            "reserved_by_driver_id": None,
            "reserved_until": None,
            "assigned_driver_id": None,
            "assigned_at": None
        }}
    )
    
    logger.info(f"[SUBCONTRACTING] Course {course_id[:8]} reset to OPEN by admin")
    
    return {"message": "Course remise en disponible", "status": CourseStatusEnum.OPEN}

@admin_subcontracting_router.post("/courses/{course_id}/cancel")
async def admin_cancel_course(course_id: str):
    """Cancel a course"""
    await db.courses.update_one(
        {"id": course_id},
        {"$set": {"status": CourseStatusEnum.CANCELLED}}
    )
    logger.info(f"[SUBCONTRACTING] Course {course_id[:8]} cancelled by admin")
    return {"message": "Course annulée", "status": CourseStatusEnum.CANCELLED}

@admin_subcontracting_router.post("/courses/{course_id}/mark-done")
async def admin_mark_course_done(course_id: str):
    """Mark course as done"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    if course["status"] != CourseStatusEnum.ASSIGNED:
        raise HTTPException(status_code=400, detail="La course doit être attribuée avant d'être terminée")
    
    await db.courses.update_one(
        {"id": course_id},
        {"$set": {"status": CourseStatusEnum.DONE}}
    )
    
    return {"message": "Course marquée comme terminée", "status": CourseStatusEnum.DONE}

# ============================================
# ADMIN ROUTES - DRIVERS MANAGEMENT
# ============================================
@admin_subcontracting_router.get("/drivers")
async def admin_get_all_drivers():
    """Get all registered drivers"""
    drivers = await db.drivers.find({}, {"_id": 0, "password_hash": 0}).sort("created_at", -1).to_list(500)
    return drivers

@admin_subcontracting_router.post("/drivers/{driver_id}/activate")
async def admin_activate_driver(driver_id: str):
    """Activate a driver account"""
    result = await db.drivers.update_one(
        {"id": driver_id},
        {"$set": {"is_active": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    logger.info(f"[SUBCONTRACTING] Driver {driver_id[:8]} activated by admin")
    
    # Send validation email to driver
    try:
        driver = await db.drivers.find_one({"id": driver_id}, {"_id": 0, "password_hash": 0})
        if driver:
            await send_driver_validation_email(driver)
    except Exception as e:
        logger.error(f"[SUBCONTRACTING] Failed to send validation email: {str(e)}")
        # Don't fail activation if email fails
    
    return {"message": "Chauffeur activé", "is_active": True}

@admin_subcontracting_router.post("/drivers/{driver_id}/deactivate")
async def admin_deactivate_driver(driver_id: str):
    """Deactivate a driver account"""
    result = await db.drivers.update_one(
        {"id": driver_id},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    logger.info(f"[SUBCONTRACTING] Driver {driver_id[:8]} deactivated by admin")
    return {"message": "Chauffeur désactivé", "is_active": False}

@admin_subcontracting_router.delete("/drivers/{driver_id}")
async def admin_delete_driver(driver_id: str):
    """Delete a driver (only if no courses assigned)"""
    # Check if driver has assigned courses
    course_count = await db.courses.count_documents({"assigned_driver_id": driver_id})
    if course_count > 0:
        raise HTTPException(status_code=400, detail=f"Impossible de supprimer: {course_count} course(s) attribuée(s)")
    
    result = await db.drivers.delete_one({"id": driver_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    return {"message": "Chauffeur supprimé"}

# ============================================
# ADMIN ROUTES - SETTINGS
# ============================================
@admin_subcontracting_router.get("/settings")
async def get_subcontracting_settings():
    """Get subcontracting settings"""
    return {
        "subcontracting_enabled": SUBCONTRACTING_ENABLED,
        "commission_rate": COMMISSION_RATE,
        "reservation_duration_minutes": RESERVATION_DURATION_MINUTES,
        "claim_token_expiry_minutes": CLAIM_TOKEN_EXPIRY_MINUTES
    }

# ============================================
# ADMIN ROUTES - ACTIVITY LOGS
# ============================================
@admin_subcontracting_router.get("/logs")
async def admin_get_activity_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    log_type: Optional[str] = None,
    limit: int = 100
):
    """Get activity logs for admin"""
    query = {}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if log_type:
        query["log_type"] = log_type
    
    logs = await db.activity_logs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs

@admin_subcontracting_router.get("/courses/{course_id}/logs")
async def admin_get_course_logs(course_id: str):
    """Get activity logs for a specific course"""
    logs = await db.activity_logs.find(
        {"entity_type": "course", "entity_id": course_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return logs

# ============================================
# ADMIN ROUTES - CLIENT CANCELLATION
# ============================================
class ClientCancellationRequest(BaseModel):
    reason: Optional[str] = None
    admin_note: Optional[str] = None

@admin_subcontracting_router.post("/courses/{course_id}/cancel-client")
async def admin_cancel_course_by_client(course_id: str, data: ClientCancellationRequest):
    """Admin records a client cancellation request"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    # Check if late cancellation
    is_late = is_late_cancellation(course["date"], course["time"])
    
    # Check if course was assigned to a driver (for notification)
    assigned_driver_id = course.get("assigned_driver_id")
    
    # Determine new status
    new_status = CourseStatusEnum.CANCELLED_LATE_CLIENT if is_late else CourseStatusEnum.CANCELLED
    
    # Update course
    update_data = {
        "status": new_status,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "cancelled_by": "client",
        "is_late_cancellation": is_late,
        "admin_notes": f"Annulation client{' (tardive < 1h)' if is_late else ''}: {data.reason or 'Aucune raison'}. Note admin: {data.admin_note or '-'}"
    }
    await db.courses.update_one({"id": course_id}, {"$set": update_data})
    
    # Create activity log
    await create_activity_log(
        log_type=ActivityLogType.COURSE_CANCELLED_CLIENT_LATE if is_late else ActivityLogType.COURSE_CANCELLED_CLIENT,
        entity_type="course",
        entity_id=course_id,
        actor_type="admin",
        actor_id=None,
        details={
            "reason": data.reason,
            "admin_note": data.admin_note,
            "is_late_cancellation": is_late,
            "assigned_driver_id": assigned_driver_id
        }
    )
    
    # If course was assigned to a driver, send notification email
    driver_notified = False
    if assigned_driver_id:
        try:
            driver = await db.drivers.find_one({"id": assigned_driver_id}, {"_id": 0, "password_hash": 0})
            if driver:
                await send_driver_cancellation_notification(course, driver, is_late)
                driver_notified = True
                logger.info(f"[SUBCONTRACTING] Driver {assigned_driver_id[:8]} notified of client cancellation")
        except Exception as e:
            logger.error(f"[SUBCONTRACTING] Failed to notify driver of cancellation: {str(e)}")
    
    logger.info(f"[SUBCONTRACTING] Course {course_id[:8]} cancelled by client{' (LATE)' if is_late else ''} | Driver notified: {driver_notified}")
    
    return {
        "message": "Annulation client enregistrée",
        "is_late_cancellation": is_late,
        "status": new_status,
        "driver_notified": driver_notified
    }

@admin_subcontracting_router.put("/courses/{course_id}/admin-notes")
async def admin_update_course_notes(course_id: str, notes: str):
    """Update internal admin notes on a course"""
    result = await db.courses.update_one(
        {"id": course_id},
        {"$set": {"admin_notes": notes}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    return {"message": "Notes mises à jour"}

# ============================================
# ADMIN ROUTES - COMMISSIONS HISTORY
# ============================================
@admin_subcontracting_router.get("/commissions")
async def admin_get_commissions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    driver_id: Optional[str] = None,
    status: Optional[str] = None,
    test_mode: Optional[bool] = None
):
    """Get commission payments history with filters"""
    # Build query
    query = {}
    
    # Date filter
    if start_date or end_date:
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date + "T23:59:59"
        if date_filter:
            query["created_at"] = date_filter
    
    # Driver filter
    if driver_id:
        query["driver_id"] = driver_id
    
    # Status filter
    if status:
        query["status"] = status
    
    # Get payments
    payments = await db.commission_payments.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrich with course and driver info
    enriched_payments = []
    total_commission = 0
    
    for payment in payments:
        # Get course info
        course = await db.courses.find_one({"id": payment.get("course_id")}, {"_id": 0})
        
        # Get driver info
        driver = await db.drivers.find_one({"id": payment.get("driver_id")}, {"_id": 0, "password_hash": 0})
        
        # Determine test/live mode from payment intent or Stripe key
        payment_intent_id = payment.get("provider_payment_id") or ""
        is_test_mode = True  # Default to test mode if can't determine
        
        # Check Stripe key first (more reliable)
        if STRIPE_API_KEY:
            is_test_mode = STRIPE_API_KEY.startswith("sk_test_")
        elif payment_intent_id:
            is_test_mode = "_test_" in payment_intent_id or not payment_intent_id.startswith("pi_")
        
        # Apply test_mode filter
        if test_mode is not None and is_test_mode != test_mode:
            continue
        
        enriched = {
            **payment,
            "course": {
                "id": course.get("id") if course else None,
                "date": course.get("date") if course else None,
                "time": course.get("time") if course else None,
                "price_total": course.get("price_total") if course else None,
                "pickup_city": extract_city_department(course.get("pickup_address", "")) if course else None,
                "dropoff_city": extract_city_department(course.get("dropoff_address", "")) if course else None,
            } if course else None,
            "driver": {
                "id": driver.get("id") if driver else None,
                "name": driver.get("name") if driver else None,
                "company_name": driver.get("company_name") if driver else None,
                "email": driver.get("email") if driver else None,
            } if driver else None,
            "is_test_mode": is_test_mode
        }
        enriched_payments.append(enriched)
        
        # Sum up paid commissions
        if payment.get("status") == "paid":
            total_commission += payment.get("amount", 0)
    
    return {
        "payments": enriched_payments,
        "total_commission": round(total_commission, 2),
        "count": len(enriched_payments),
        "filters_applied": {
            "start_date": start_date,
            "end_date": end_date,
            "driver_id": driver_id,
            "status": status,
            "test_mode": test_mode
        }
    }

@admin_subcontracting_router.get("/commissions/export-csv")
async def admin_export_commissions_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    driver_id: Optional[str] = None,
    status: Optional[str] = None
):
    """Export commission payments to CSV"""
    # Get data using same logic
    data = await admin_get_commissions(start_date, end_date, driver_id, status)
    payments = data["payments"]
    
    # Generate CSV
    output = io.StringIO()
    import csv
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "Date Paiement",
        "ID Réservation", 
        "Chauffeur Nom",
        "Chauffeur Société",
        "Chauffeur Email",
        "Commission (€)",
        "Prix Course (€)",
        "Statut",
        "PaymentIntent",
        "Mode"
    ])
    
    # Data rows
    for p in payments:
        course = p.get("course") or {}
        driver = p.get("driver") or {}
        
        # Format date
        created_at = p.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime("%d/%m/%Y %H:%M")
        except:
            date_str = created_at[:16] if created_at else ""
        
        writer.writerow([
            date_str,
            course.get("id", "")[:8].upper() if course.get("id") else "",
            driver.get("name", ""),
            driver.get("company_name", ""),
            driver.get("email", ""),
            f"{p.get('amount', 0):.2f}",
            f"{course.get('price_total', 0):.2f}" if course.get('price_total') else "",
            p.get("status", ""),
            p.get("provider_payment_id", ""),
            "TEST" if p.get("is_test_mode") else "LIVE"
        ])
    
    # Return CSV
    csv_content = output.getvalue()
    filename = f"commissions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ============================================
# PDF GENERATION - DRIVER DOCUMENTS
# ============================================
def generate_driver_bon_commande_pdf(course: dict, driver: dict):
    """Generate bon de commande with driver's company info"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    dark = HexColor("#0a0a0a")
    accent = HexColor("#7dd3fc")
    gray = HexColor("#64748b")
    
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
    
    # Reference
    c.setFillColor(HexColor("#1a1a1a"))
    c.roundRect(width - 200, height - 90, 180, 70, 5, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", 9)
    c.drawString(width - 190, height - 45, "N° Bon de commande")
    c.setFont("Helvetica-Bold", 11)
    bon_number = f"BC-{course['id'][:8].upper()}"
    c.drawString(width - 190, height - 60, bon_number)
    c.setFont("Helvetica", 9)
    c.drawString(width - 190, height - 80, datetime.now().strftime("%d/%m/%Y"))
    
    y = height - 130
    
    # Driver company info
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "EXPLOITANT")
    y -= 20
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(40, y, driver.get("company_name", ""))
    y -= 14
    c.drawString(40, y, driver.get("address", ""))
    y -= 14
    c.drawString(40, y, f"SIRET: {driver.get('siret', '')}")
    if driver.get("vat_applicable") and driver.get("vat_number"):
        y -= 14
        c.drawString(40, y, f"TVA: {driver['vat_number']}")
    y -= 14
    c.drawString(40, y, f"Tél: {driver.get('phone', '')} | Email: {driver.get('email', '')}")
    
    # Client info
    y = height - 130
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, y, "CLIENT")
    y -= 20
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    c.drawString(320, y, course.get("client_name", ""))
    y -= 14
    c.drawString(320, y, course.get("client_email", ""))
    y -= 14
    c.drawString(320, y, course.get("client_phone", ""))
    
    # Course details
    y = height - 260
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "DÉTAILS DE LA COURSE")
    y -= 30
    
    c.setFont("Helvetica", 10)
    c.setFillColor(gray)
    
    details = [
        ("Date", course.get("date", "")),
        ("Heure", course.get("time", "")),
        ("Départ", course.get("pickup_address", "")),
        ("Arrivée", course.get("dropoff_address", "")),
    ]
    if course.get("distance_km"):
        details.append(("Distance", f"{course['distance_km']} km"))
    if course.get("notes"):
        details.append(("Notes", course["notes"]))
    
    for label, value in details:
        c.setFillColor(dark)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(40, y, f"{label}:")
        c.setFillColor(gray)
        c.setFont("Helvetica", 9)
        c.drawString(120, y, str(value)[:80])
        y -= 18
    
    # Price
    y -= 20
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "PRIX TOTAL:")
    c.setFillColor(accent)
    c.drawString(160, y, f"{course.get('price_total', 0):.2f} €")
    
    # Footer
    c.setFillColor(dark)
    c.rect(0, 0, width, 35, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 15, f"{driver.get('company_name', '')} — SIRET: {driver.get('siret', '')} — {driver.get('email', '')}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def generate_driver_invoice_pdf(course: dict, driver: dict, invoice_number: str, invoice_date: str):
    """Generate invoice from driver to client"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    dark = HexColor("#0a0a0a")
    accent = HexColor("#7dd3fc")
    gray = HexColor("#64748b")
    
    # Header
    c.setFillColor(dark)
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 50, "FACTURE")
    c.setFont("Helvetica", 10)
    c.setFillColor(accent)
    c.drawString(40, height - 68, "Transport VTC")
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 40, height - 40, f"N° {invoice_number}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 40, height - 55, f"Date: {invoice_date}")
    
    y = height - 120
    
    # Driver info
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "ÉMETTEUR")
    y -= 18
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    c.drawString(40, y, driver.get("company_name", ""))
    y -= 14
    c.drawString(40, y, driver.get("address", ""))
    y -= 14
    c.drawString(40, y, f"SIRET: {driver.get('siret', '')}")
    if driver.get("vat_applicable") and driver.get("vat_number"):
        y -= 14
        c.drawString(40, y, f"TVA: {driver['vat_number']}")
    
    # Client info
    y = height - 120
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, y, "CLIENT")
    y -= 18
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    c.drawString(320, y, course.get("client_name", ""))
    y -= 14
    c.drawString(320, y, course.get("client_email", ""))
    
    # Table header
    y = height - 260
    c.setFillColor(dark)
    c.rect(40, y - 5, width - 80, 25, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y + 5, "DESCRIPTION")
    c.drawString(350, y + 5, "QTÉ")
    c.drawString(420, y + 5, "PRIX HT")
    c.drawString(490, y + 5, "TOTAL")
    
    # Service line
    y -= 30
    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    service_desc = f"Transport VTC {course.get('date', '')} - {course.get('pickup_address', '')[:30]}... → {course.get('dropoff_address', '')[:30]}..."
    c.drawString(50, y, service_desc[:60])
    c.drawString(350, y, "1")
    
    price_total = course.get("price_total", 0)
    
    if driver.get("vat_applicable"):
        price_ht = round(price_total / 1.10, 2)
        tva = round(price_total - price_ht, 2)
    else:
        price_ht = price_total
        tva = 0
    
    c.drawString(420, y, f"{price_ht:.2f} €")
    c.drawString(490, y, f"{price_ht:.2f} €")
    
    # Totals
    y -= 50
    c.setFillColor(dark)
    c.setFont("Helvetica", 10)
    c.drawRightString(470, y, "Total HT:")
    c.drawRightString(550, y, f"{price_ht:.2f} €")
    
    if driver.get("vat_applicable"):
        y -= 18
        c.drawRightString(470, y, "TVA (10%):")
        c.drawRightString(550, y, f"{tva:.2f} €")
    
    y -= 25
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(470, y, "TOTAL TTC:")
    c.setFillColor(accent)
    c.drawRightString(550, y, f"{price_total:.2f} €")
    
    # Footer
    c.setFillColor(dark)
    c.rect(0, 0, width, 40, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 20, f"{driver.get('company_name', '')} — SIRET: {driver.get('siret', '')}")
    c.drawCentredString(width / 2, 8, f"Email: {driver.get('email', '')}")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def generate_commission_invoice_pdf(course: dict, driver: dict, invoice_number: str):
    """Generate commission invoice from JABADRIVER to driver"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    dark = HexColor("#0a0a0a")
    accent = HexColor("#f59e0b")  # Orange for commission
    gray = HexColor("#64748b")
    
    # Header
    c.setFillColor(dark)
    c.rect(0, height - 80, width, 80, fill=True, stroke=False)
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 22)
    c.drawString(40, height - 50, "FACTURE COMMISSION")
    c.setFont("Helvetica", 10)
    c.setFillColor(accent)
    c.drawString(40, height - 68, "Plateforme JABADRIVER")
    
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - 40, height - 40, f"N° {invoice_number}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 40, height - 55, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    
    y = height - 120
    
    # JABADRIVER info
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "ÉMETTEUR")
    y -= 18
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    c.drawString(40, y, "JABADRIVER")
    y -= 14
    c.drawString(40, y, "SIRET: 941 473 217 00011")
    y -= 14
    c.drawString(40, y, "contact@jabadriver.fr")
    
    # Driver info
    y = height - 120
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(320, y, "CLIENT (CHAUFFEUR)")
    y -= 18
    c.setFont("Helvetica", 9)
    c.setFillColor(gray)
    c.drawString(320, y, driver.get("company_name", ""))
    y -= 14
    c.drawString(320, y, f"SIRET: {driver.get('siret', '')}")
    y -= 14
    c.drawString(320, y, driver.get("email", ""))
    
    # Table
    y = height - 250
    c.setFillColor(dark)
    c.rect(40, y - 5, width - 80, 25, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y + 5, "DESCRIPTION")
    c.drawString(420, y + 5, "MONTANT")
    
    y -= 30
    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    c.drawString(50, y, f"Commission course du {course.get('date', '')} - {course.get('client_name', '')}")
    y -= 14
    c.drawString(50, y, f"(10% sur {course.get('price_total', 0):.2f} €)")
    
    commission = course.get("commission_amount", round(course.get("price_total", 0) * 0.10, 2))
    c.drawString(420, y + 7, f"{commission:.2f} €")
    
    # Total
    y -= 50
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(470, y, "TOTAL:")
    c.setFillColor(accent)
    c.drawRightString(550, y, f"{commission:.2f} €")
    
    y -= 30
    c.setFillColor(gray)
    c.setFont("Helvetica", 9)
    c.drawString(40, y, "Paiement reçu par carte bancaire via Stripe.")
    
    # Footer
    c.setFillColor(dark)
    c.rect(0, 0, width, 35, fill=True, stroke=False)
    c.setFillColor(HexColor("#ffffff"))
    c.setFont("Helvetica", 8)
    c.drawCentredString(width / 2, 15, "JABADRIVER — SIRET: 941 473 217 00011 — contact@jabadriver.fr")
    
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ============================================
# DRIVER DOCUMENT ROUTES
# ============================================
@driver_router.get("/courses/{course_id}/bon-commande-pdf")
async def driver_generate_bon_commande(request: Request, course_id: str):
    """Generate bon de commande PDF for driver"""
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    course = await db.courses.find_one(
        {"id": course_id, "assigned_driver_id": driver["id"]},
        {"_id": 0}
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée ou non attribuée")
    
    pdf_bytes = generate_driver_bon_commande_pdf(course, driver)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=bon_commande_{course_id[:8]}.pdf"}
    )

@driver_router.get("/courses/{course_id}/invoice-pdf")
async def driver_generate_invoice(request: Request, course_id: str):
    """Generate invoice PDF for driver"""
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    course = await db.courses.find_one(
        {"id": course_id, "assigned_driver_id": driver["id"]},
        {"_id": 0}
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée ou non attribuée")
    
    # Generate invoice number
    prefix = driver.get("invoice_prefix", "DRI")
    year = datetime.now().year
    next_num = driver.get("invoice_next_number", 1)
    invoice_number = f"{prefix}-{year}-{next_num:04d}"
    
    # Increment invoice number
    await db.drivers.update_one(
        {"id": driver["id"]},
        {"$inc": {"invoice_next_number": 1}}
    )
    
    invoice_date = datetime.now().strftime("%d/%m/%Y")
    pdf_bytes = generate_driver_invoice_pdf(course, driver, invoice_number, invoice_date)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=facture_{invoice_number}.pdf"}
    )

@driver_router.post("/courses/{course_id}/send-invoice")
async def driver_send_invoice_to_client(request: Request, course_id: str):
    """Send invoice to client via email"""
    import resend
    
    driver = await get_driver_from_token(request.headers.get("Authorization"))
    
    course = await db.courses.find_one(
        {"id": course_id, "assigned_driver_id": driver["id"]},
        {"_id": 0}
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée ou non attribuée")
    
    if not course.get("client_email"):
        raise HTTPException(status_code=400, detail="Pas d'email client")
    
    # Generate invoice
    prefix = driver.get("invoice_prefix", "DRI")
    year = datetime.now().year
    next_num = driver.get("invoice_next_number", 1)
    invoice_number = f"{prefix}-{year}-{next_num:04d}"
    
    await db.drivers.update_one(
        {"id": driver["id"]},
        {"$inc": {"invoice_next_number": 1}}
    )
    
    invoice_date = datetime.now().strftime("%d/%m/%Y")
    pdf_bytes = generate_driver_invoice_pdf(course, driver, invoice_number, invoice_date)
    
    # Send email
    import base64
    pdf_base64 = base64.b64encode(pdf_bytes).decode()
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Facture pour votre course VTC</h2>
        <p>Bonjour {course.get('client_name', '')},</p>
        <p>Veuillez trouver ci-joint la facture pour votre course du {course.get('date', '')}.</p>
        <p><strong>Détails:</strong></p>
        <ul>
            <li>Départ: {course.get('pickup_address', '')}</li>
            <li>Arrivée: {course.get('dropoff_address', '')}</li>
            <li>Montant: {course.get('price_total', 0):.2f} €</li>
        </ul>
        <p>Merci de votre confiance.</p>
        <p>Cordialement,<br>{driver.get('company_name', '')}</p>
    </body>
    </html>
    """
    
    params = {
        "from": f"{driver.get('company_name', 'Chauffeur')} <noreply@jabadriver.fr>",
        "to": [course["client_email"]],
        "subject": f"Facture {invoice_number} - Course VTC du {course.get('date', '')}",
        "html": html_content,
        "attachments": [{
            "filename": f"facture_{invoice_number}.pdf",
            "content": pdf_base64
        }]
    }
    
    try:
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[DRIVER] Invoice {invoice_number} sent to {course['client_email']}")
        return {"message": f"Facture {invoice_number} envoyée à {course['client_email']}"}
    except Exception as e:
        logger.error(f"[DRIVER] Failed to send invoice: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur envoi email: {str(e)}")

# ============================================
# ADMIN DOCUMENT ROUTES
# ============================================
@admin_subcontracting_router.get("/courses/{course_id}/commission-invoice-pdf")
async def admin_generate_commission_invoice(course_id: str):
    """Generate commission invoice (JABADRIVER -> driver)"""
    course = await db.courses.find_one({"id": course_id}, {"_id": 0})
    if not course:
        raise HTTPException(status_code=404, detail="Course non trouvée")
    
    if not course.get("assigned_driver_id"):
        raise HTTPException(status_code=400, detail="Course non attribuée")
    
    driver = await db.drivers.find_one({"id": course["assigned_driver_id"]}, {"_id": 0})
    if not driver:
        raise HTTPException(status_code=404, detail="Chauffeur non trouvé")
    
    invoice_number = f"COM-{datetime.now().year}-{course_id[:8].upper()}"
    pdf_bytes = generate_commission_invoice_pdf(course, driver, invoice_number)
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=commission_{invoice_number}.pdf"}
    )

# ============================================
# STRIPE WEBHOOK
# ============================================
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events - using native Stripe SDK"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    
    logger.info(f"[STRIPE WEBHOOK] Received webhook event")
    
    try:
        stripe.api_key = STRIPE_API_KEY
        
        # For now, parse event without signature verification (add webhook secret later)
        import json
        event_data = json.loads(payload)
        event_type = event_data.get('type', '')
        
        logger.info(f"[STRIPE WEBHOOK] Event type: {event_type}")
        
        if event_type == "checkout.session.completed":
            session = event_data['data']['object']
            session_id = session.get('id')
            payment_status = session.get('payment_status')
            
            logger.info(f"[STRIPE WEBHOOK] Session: {session_id}, Payment: {payment_status}")
            
            if payment_status == "paid":
                # Get payment record
                payment = await db.commission_payments.find_one({"session_id": session_id}, {"_id": 0})
                
                if payment and payment["status"] != "paid":
                    # Finalize attribution
                    success = await finalize_attribution(
                        payment["course_id"], 
                        payment["driver_id"], 
                        session_id
                    )
                    
                    # Update payment
                    await db.commission_payments.update_one(
                        {"session_id": session_id},
                        {"$set": {
                            "status": "paid" if success else "refund_needed",
                            "paid_at": datetime.now(timezone.utc).isoformat(),
                            "provider_payment_id": session.get('payment_intent')
                        }}
                    )
                    
                    logger.info(f"[STRIPE WEBHOOK] ✅ Payment processed for course {payment['course_id'][:8]}")
        
        return {"status": "ok", "received": True}
    
    except Exception as e:
        logger.error(f"[STRIPE WEBHOOK] Error: {str(e)}")
        # Return 200 to prevent Stripe from retrying
        return {"status": "error", "message": str(e)}
