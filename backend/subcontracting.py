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
    status: str = CourseStatusEnum.OPEN
    reserved_by_driver_id: Optional[str] = None
    reserved_until: Optional[str] = None
    assigned_driver_id: Optional[str] = None
    assigned_at: Optional[str] = None
    commission_rate: float = COMMISSION_RATE
    commission_amount: float = 0.0
    commission_paid: bool = False
    commission_paid_at: Optional[str] = None
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
# ROUTER
# ============================================
subcontracting_router = APIRouter(prefix="/api/subcontracting", tags=["Sous-traitance"])
driver_router = APIRouter(prefix="/api/driver", tags=["Chauffeur"])
admin_subcontracting_router = APIRouter(prefix="/api/admin/subcontracting", tags=["Admin Sous-traitance"])

# Database reference - will be set from main server.py
db = None
STRIPE_API_KEY = None

def init_subcontracting(database, stripe_key):
    """Initialize the subcontracting module with database and stripe key"""
    global db, STRIPE_API_KEY
    db = database
    STRIPE_API_KEY = stripe_key
    logger.info("[SUBCONTRACTING] Module initialized")
    logger.info(f"[SUBCONTRACTING] Stripe API Key present: {bool(STRIPE_API_KEY)}")

# ============================================
# HELPER FUNCTIONS
# ============================================
def simple_hash(password: str) -> str:
    """Simple hash for demo - use bcrypt in production"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return simple_hash(password) == password_hash

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
    
    await db.drivers.insert_one(driver.model_dump())
    logger.info(f"[DRIVER] New driver registered: {data.email} (pending validation)")
    
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
# CLAIM ROUTES (PUBLIC WITH AUTH)
# ============================================
@subcontracting_router.get("/claim/{token}")
async def get_claim_info(token: str):
    """Get course info from claim token (public)"""
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
    
    return {
        "course": {
            "id": course["id"],
            "client_name": course["client_name"],
            "pickup_address": course["pickup_address"],
            "dropoff_address": course["dropoff_address"],
            "date": course["date"],
            "time": course["time"],
            "distance_km": course.get("distance_km"),
            "price_total": course["price_total"],
            "notes": course.get("notes"),
            "status": course["status"]
        },
        "commission_rate": COMMISSION_RATE,
        "commission_amount": commission_amount,
        "reserved_by": reserved_driver_name,
        "time_remaining_seconds": time_remaining,
        "claim_expires_at": claim["expires_at"]
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
    
    # Get host URL for redirect
    try:
        body = await request.json()
    except:
        body = {}
    origin_url = body.get("origin_url", "").rstrip("/")
    if not origin_url:
        origin_url = os.environ.get('FRONTEND_URL', 'https://ride-booking-98.preview.emergentagent.com')
    
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

# Import asyncio at module level
import asyncio

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
    """Handle Stripe webhook events"""
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature")
    
    webhook_url = f"{str(request.base_url).rstrip('/')}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    
    try:
        event = await stripe_checkout.handle_webhook(body, sig_header)
        
        logger.info(f"[STRIPE WEBHOOK] Event: {event.event_type}, Session: {event.session_id}")
        
        if event.event_type == "checkout.session.completed" and event.payment_status == "paid":
            # Get payment record
            payment = await db.commission_payments.find_one({"session_id": event.session_id}, {"_id": 0})
            
            if payment and payment["status"] != "paid":
                # Finalize attribution
                success = await finalize_attribution(
                    payment["course_id"], 
                    payment["driver_id"], 
                    event.session_id
                )
                
                # Update payment
                await db.commission_payments.update_one(
                    {"session_id": event.session_id},
                    {"$set": {
                        "status": "paid" if success else "refund_needed",
                        "paid_at": datetime.now(timezone.utc).isoformat(),
                        "provider_payment_id": event.event_id
                    }}
                )
                
                logger.info(f"[STRIPE WEBHOOK] Payment processed for course {payment['course_id'][:8]}")
        
        return {"status": "ok"}
    
    except Exception as e:
        logger.error(f"[STRIPE WEBHOOK] Error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
