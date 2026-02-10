from fastapi import FastAPI, APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from io import BytesIO
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

# PDF imports
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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


# ============= MODELS =============

class ReservationCreate(BaseModel):
    client_nom: str
    client_telephone: str
    client_email: EmailStr
    adresse_depart: str
    adresse_arrivee: str
    date_course: str  # Format: YYYY-MM-DD
    heure_course: str  # Format: HH:MM
    distance_km: float
    duree_minutes: int
    prix_estime: float
    nombre_passagers: int = 1

class ReservationUpdate(BaseModel):
    prix_final: Optional[float] = None
    statut: Optional[str] = None

class Reservation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    numero_reservation: str = Field(default_factory=lambda: f"RES-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}")
    client_nom: str
    client_telephone: str
    client_email: EmailStr
    adresse_depart: str
    adresse_arrivee: str
    date_course: str
    heure_course: str
    distance_km: float
    duree_minutes: int
    prix_estime: float
    prix_final: Optional[float] = None
    nombre_passagers: int = 1
    statut: str = "nouvelle"  # nouvelle, confirmee, terminee, annulee
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============= INFORMATIONS ENTREPRISE =============

ENTREPRISE_INFO = {
    "nom": "JabaDriver VTC",
    "siret": "123 456 789 00012",
    "siren": "123 456 789",
    "adresse": "123 Rue du Transport, 75001 Paris",
    "telephone": "+33 1 23 45 67 89",
    "email": "contact@jabadriver-vtc.fr",
    "tva_mention": "TVA non applicable - art. 293B du CGI"
}


# ============= PDF SERVICES =============

def generer_bon_commande_pdf(reservation: Reservation) -> BytesIO:
    """Génère un bon de commande PDF pour une réservation"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Style personnalisé titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a56db'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    # Style personnalisé pour sous-titre
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # En-tête
    story.append(Paragraph("BON DE COMMANDE", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informations entreprise
    story.append(Paragraph("Informations Entreprise", subtitle_style))
    entreprise_data = [
        ["Entreprise:", ENTREPRISE_INFO["nom"]],
        ["SIREN:", ENTREPRISE_INFO["siren"]],
        ["SIRET:", ENTREPRISE_INFO["siret"]],
        ["Adresse:", ENTREPRISE_INFO["adresse"]],
        ["Téléphone:", ENTREPRISE_INFO["telephone"]],
        ["Email:", ENTREPRISE_INFO["email"]],
        ["TVA:", ENTREPRISE_INFO["tva_mention"]],
    ]
    
    entreprise_table = Table(entreprise_data, colWidths=[4*cm, 12*cm])
    entreprise_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(entreprise_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Informations client
    story.append(Paragraph("Informations Client", subtitle_style))
    client_data = [
        ["Nom:", reservation.client_nom],
        ["Téléphone:", reservation.client_telephone],
        ["Email:", reservation.client_email],
    ]
    
    client_table = Table(client_data, colWidths=[4*cm, 12*cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(client_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Détails de la course
    story.append(Paragraph("Détails de la Course", subtitle_style))
    course_data = [
        ["Numéro de réservation:", reservation.numero_reservation],
        ["Date:", reservation.date_course],
        ["Heure:", reservation.heure_course],
        ["Adresse de départ:", reservation.adresse_depart],
        ["Adresse d'arrivée:", reservation.adresse_arrivee],
        ["Distance:", f"{reservation.distance_km} km"],
        ["Durée estimée:", f"{reservation.duree_minutes} min"],
        ["Nombre de passagers:", str(reservation.nombre_passagers)],
        ["Prix estimé:", f"{reservation.prix_estime} €"],
    ]
    
    course_table = Table(course_data, colWidths=[5*cm, 11*cm])
    course_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(course_table)
    story.append(Spacer(1, 1*cm))
    
    # Footer
    footer_text = f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(footer_text, footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def generer_facture_pdf(reservation: Reservation) -> BytesIO:
    """Génère une facture PDF pour une réservation"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Style personnalisé titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1a56db'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # En-tête
    story.append(Paragraph("FACTURE", title_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informations entreprise
    story.append(Paragraph("Émetteur", subtitle_style))
    entreprise_data = [
        ["Entreprise:", ENTREPRISE_INFO["nom"]],
        ["SIRET:", ENTREPRISE_INFO["siret"]],
        ["Adresse:", ENTREPRISE_INFO["adresse"]],
        ["Téléphone:", ENTREPRISE_INFO["telephone"]],
        ["Email:", ENTREPRISE_INFO["email"]],
    ]
    
    entreprise_table = Table(entreprise_data, colWidths=[4*cm, 12*cm])
    entreprise_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(entreprise_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Informations client
    story.append(Paragraph("Client", subtitle_style))
    client_data = [
        ["Nom:", reservation.client_nom],
        ["Email:", reservation.client_email],
        ["Téléphone:", reservation.client_telephone],
    ]
    
    client_table = Table(client_data, colWidths=[4*cm, 12*cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1f2937')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    story.append(client_table)
    story.append(Spacer(1, 0.8*cm))
    
    # Détails facture
    story.append(Paragraph("Détails de la prestation", subtitle_style))
    
    prix_final = reservation.prix_final if reservation.prix_final is not None else reservation.prix_estime
    
    facture_data = [
        ["Description", "Quantité", "Prix unitaire", "Total"],
        [
            f"Course VTC\n{reservation.adresse_depart}\n→ {reservation.adresse_arrivee}\n{reservation.date_course} à {reservation.heure_course}",
            "1",
            f"{prix_final} €",
            f"{prix_final} €"
        ],
    ]
    
    facture_table = Table(facture_data, colWidths=[9*cm, 2*cm, 2.5*cm, 2.5*cm])
    facture_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a56db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(facture_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Total
    total_data = [
        ["TOTAL HT:", f"{prix_final} €"],
        ["TVA:", ENTREPRISE_INFO["tva_mention"]],
        ["TOTAL TTC:", f"{prix_final} €"],
    ]
    
    total_table = Table(total_data, colWidths=[12*cm, 4*cm])
    total_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1a56db')),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#1a56db')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 1*cm))
    
    # Mentions légales
    mentions_text = f"Numéro de réservation: {reservation.numero_reservation}<br/>{ENTREPRISE_INFO['tva_mention']}"
    mentions_style = ParagraphStyle(
        'Mentions',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Paragraph(mentions_text, mentions_style))
    
    # Footer
    footer_text = f"Facture générée le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph(footer_text, footer_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


# ============= EMAIL SERVICE =============

async def envoyer_email_reservation(reservation: Reservation, pdf_buffer: BytesIO):
    """Envoie un email à l'admin avec le bon de commande en pièce jointe"""
    
    # Configuration email (à adapter selon votre provider)
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@jabadriver-vtc.fr')
    
    if not smtp_user or not smtp_password:
        logger.warning("Email non configuré - SMTP_USER ou SMTP_PASSWORD manquant")
        return
    
    # Créer le message
    message = MIMEMultipart()
    message['From'] = smtp_user
    message['To'] = admin_email
    message['Subject'] = f"Nouvelle réservation VTC - {reservation.numero_reservation}"
    
    # Corps du message
    body = f"""
Bonjour,

Une nouvelle réservation VTC vient d'être effectuée :

Numéro de réservation : {reservation.numero_reservation}
Client : {reservation.client_nom}
Téléphone : {reservation.client_telephone}
Email : {reservation.client_email}

Date de la course : {reservation.date_course}
Heure : {reservation.heure_course}

Départ : {reservation.adresse_depart}
Arrivée : {reservation.adresse_arrivee}

Distance : {reservation.distance_km} km
Durée estimée : {reservation.duree_minutes} min
Nombre de passagers : {reservation.nombre_passagers}
Prix estimé : {reservation.prix_estime} €

Le bon de commande est joint à cet email.

Cordialement,
Système JabaDriver VTC
"""
    
    message.attach(MIMEText(body, 'plain'))
    
    # Attacher le PDF
    pdf_attachment = MIMEApplication(pdf_buffer.read(), _subtype='pdf')
    pdf_attachment.add_header(
        'Content-Disposition', 
        'attachment', 
        filename=f'bon_commande_{reservation.numero_reservation}.pdf'
    )
    message.attach(pdf_attachment)
    
    # Envoyer l'email
    try:
        await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True
        )
        logger.info(f"Email envoyé pour réservation {reservation.numero_reservation}")
    except Exception as e:
        logger.error(f"Erreur envoi email : {str(e)}")


# ============= API ROUTES =============

@api_router.get("/")
async def root():
    return {"message": "API JabaDriver VTC"}


@api_router.post("/reservations", response_model=Reservation)
async def creer_reservation(input: ReservationCreate):
    """Créer une nouvelle réservation et envoyer email avec bon de commande"""
    
    # Créer l'objet réservation
    reservation = Reservation(**input.model_dump())
    
    # Sauvegarder dans MongoDB
    doc = reservation.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.reservations.insert_one(doc)
    
    # Générer le bon de commande PDF
    try:
        pdf_buffer = generer_bon_commande_pdf(reservation)
        
        # Envoyer l'email avec le PDF
        await envoyer_email_reservation(reservation, pdf_buffer)
    except Exception as e:
        logger.error(f"Erreur génération PDF ou envoi email : {str(e)}")
    
    return reservation


@api_router.get("/reservations", response_model=List[Reservation])
async def lister_reservations():
    """Lister toutes les réservations"""
    reservations = await db.reservations.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for res in reservations:
        if isinstance(res['created_at'], str):
            res['created_at'] = datetime.fromisoformat(res['created_at'])
        if isinstance(res['updated_at'], str):
            res['updated_at'] = datetime.fromisoformat(res['updated_at'])
    
    # Trier par date de création décroissante
    reservations.sort(key=lambda x: x['created_at'], reverse=True)
    
    return reservations


@api_router.get("/reservations/{reservation_id}", response_model=Reservation)
async def obtenir_reservation(reservation_id: str):
    """Obtenir une réservation par son ID"""
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    # Convert ISO string timestamps back to datetime objects
    if isinstance(reservation['created_at'], str):
        reservation['created_at'] = datetime.fromisoformat(reservation['created_at'])
    if isinstance(reservation['updated_at'], str):
        reservation['updated_at'] = datetime.fromisoformat(reservation['updated_at'])
    
    return reservation


@api_router.patch("/reservations/{reservation_id}", response_model=Reservation)
async def modifier_reservation(reservation_id: str, input: ReservationUpdate):
    """Modifier une réservation (prix final, statut)"""
    
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    # Préparer les updates
    update_data = {}
    if input.prix_final is not None:
        update_data["prix_final"] = input.prix_final
    if input.statut is not None:
        update_data["statut"] = input.statut
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # Mettre à jour dans MongoDB
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": update_data}
    )
    
    # Récupérer la réservation mise à jour
    updated_reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    
    # Convert ISO string timestamps
    if isinstance(updated_reservation['created_at'], str):
        updated_reservation['created_at'] = datetime.fromisoformat(updated_reservation['created_at'])
    if isinstance(updated_reservation['updated_at'], str):
        updated_reservation['updated_at'] = datetime.fromisoformat(updated_reservation['updated_at'])
    
    return updated_reservation


@api_router.get("/reservations/{reservation_id}/bon-commande-pdf")
async def telecharger_bon_commande(reservation_id: str):
    """Télécharger le bon de commande PDF d'une réservation"""
    
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    # Convert ISO string timestamps
    if isinstance(reservation['created_at'], str):
        reservation['created_at'] = datetime.fromisoformat(reservation['created_at'])
    if isinstance(reservation['updated_at'], str):
        reservation['updated_at'] = datetime.fromisoformat(reservation['updated_at'])
    
    reservation_obj = Reservation(**reservation)
    pdf_buffer = generer_bon_commande_pdf(reservation_obj)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=bon_commande_{reservation_obj.numero_reservation}.pdf"
        }
    )


@api_router.get("/reservations/{reservation_id}/facture-pdf")
async def telecharger_facture(reservation_id: str):
    """Télécharger la facture PDF d'une réservation"""
    
    reservation = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not reservation:
        raise HTTPException(status_code=404, detail="Réservation non trouvée")
    
    # Convert ISO string timestamps
    if isinstance(reservation['created_at'], str):
        reservation['created_at'] = datetime.fromisoformat(reservation['created_at'])
    if isinstance(reservation['updated_at'], str):
        reservation['updated_at'] = datetime.fromisoformat(reservation['updated_at'])
    
    reservation_obj = Reservation(**reservation)
    pdf_buffer = generer_facture_pdf(reservation_obj)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=facture_{reservation_obj.numero_reservation}.pdf"
        }
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
