"""
PDF Template Module - Unified templates for document generation
========================================================================

This module provides a single source of truth for document styling,
matching the frontend design exactly (DriverDocumentTemplate.jsx).

Visual consistency guaranteed:
- Portail chauffeur (session)
- Page token chauffeur
- PDF téléchargé (bon de commande / facture)
"""

import os
import base64
from pathlib import Path
from io import BytesIO
from typing import Optional

# PDF generation with reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import Color, HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Logo path
LOGO_PATH = Path(__file__).parent / "assets" / "jabadriver_logo.png"

def get_logo_base64() -> str:
    """Get logo as base64 data URI for embedding in HTML"""
    if not LOGO_PATH.exists():
        return ""
    
    with open(LOGO_PATH, "rb") as f:
        logo_data = base64.b64encode(f.read()).decode("utf-8")
    
    return f"data:image/png;base64,{logo_data}"


def calculate_totals(course: dict) -> dict:
    """
    Calculate all financial values for a course.
    
    IMPORTANT: Commission = 10% of BASE PRICE ONLY (not final total)
    This is the Single Source of Truth for PDF generation.
    
    Uses persisted values when available (from backend calculate_course_totals).
    """
    price_base = course.get('price_base') or course.get('price_total', 0) or 0
    supplement_peage = course.get('supplement_peage', 0) or 0
    supplement_parking = course.get('supplement_parking', 0) or 0
    supplement_traffic = course.get('supplement_traffic', 0) or 0  # Traffic delay supplement
    
    # Use persisted waiting values when available
    supplement_attente_minutes = course.get('waiting_billable_minutes') or course.get('supplement_attente_minutes', 0) or 0
    supplement_attente = course.get('waiting_price') or course.get('supplement_attente_amount') or course.get('supplement_attente', 0) or 0
    
    # If waiting_price is 0 but billable minutes > 0, calculate (1€/min)
    if supplement_attente == 0 and supplement_attente_minutes > 0:
        supplement_attente = float(supplement_attente_minutes)  # 1€/min
    
    # Manual supplements total (péage + parking + traffic)
    manual_supplements = supplement_peage + supplement_parking + supplement_traffic
    
    # Total = base + waiting + manual supplements
    total = price_base + supplement_attente + manual_supplements
    
    # COMMISSION: 10% of BASE PRICE ONLY (never on final total)
    commission_rate = 0.10
    commission = round(price_base * commission_rate, 2)  # BASE price, not total
    driver_net = total - commission
    
    return {
        "price_base": price_base,
        "supplement_peage": supplement_peage,
        "supplement_parking": supplement_parking,
        "supplement_traffic": supplement_traffic,
        "supplement_attente_minutes": supplement_attente_minutes,
        "supplement_attente": supplement_attente,
        "manual_supplements": manual_supplements,
        "total": total,
        "commission": commission,  # 10% of base only
        "driver_net": driver_net,
        "has_supplements": manual_supplements > 0 or supplement_attente > 0
    }


# === COLORS matching frontend design ===
COLORS = {
    'bg': HexColor('#f9fafb'),          # Light gray background
    'card_bg': HexColor('#ffffff'),      # White card
    'card_border': HexColor('#e5e7eb'),  # Light border
    'text_primary': HexColor('#111827'), # Dark text
    'text_secondary': HexColor('#6b7280'), # Gray text
    'text_muted': HexColor('#9ca3af'),   # Muted text
    'emerald': HexColor('#10b981'),       # Green accent
    'emerald_light': HexColor('#d1fae5'), # Light green
    'emerald_bg': HexColor('#f0fdf4'),    # Green background
    'amber': HexColor('#f59e0b'),          # Amber/Yellow
    'amber_light': HexColor('#fef3c7'),   # Light amber
    'red': HexColor('#ef4444'),            # Red
    'red_light': HexColor('#fee2e2'),     # Light red
    'sky': HexColor('#0ea5e9'),            # Sky blue
    'sky_light': HexColor('#e0f2fe'),     # Light sky
}


def draw_rounded_rect(c, x, y, width, height, radius, fill_color=None, stroke_color=None, stroke_width=0.5):
    """Draw a rounded rectangle"""
    c.saveState()
    
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    
    # Draw rounded rectangle path
    p = c.beginPath()
    p.moveTo(x + radius, y)
    p.lineTo(x + width - radius, y)
    p.arcTo(x + width - radius, y, x + width, y + radius, radius)
    p.lineTo(x + width, y + height - radius)
    p.arcTo(x + width, y + height - radius, x + width - radius, y + height, radius)
    p.lineTo(x + radius, y + height)
    p.arcTo(x + radius, y + height, x, y + height - radius, radius)
    p.lineTo(x, y + radius)
    p.arcTo(x, y + radius, x + radius, y, radius)
    p.close()
    
    if fill_color and stroke_color:
        c.drawPath(p, fill=1, stroke=1)
    elif fill_color:
        c.drawPath(p, fill=1, stroke=0)
    elif stroke_color:
        c.drawPath(p, fill=0, stroke=1)
    
    c.restoreState()


def generate_unified_pdf(
    course: dict, 
    driver: dict, 
    doc_type: str = 'bon',
    show_commission: bool = True
) -> BytesIO:
    """
    Generate PDF with unified template matching frontend design exactly.
    
    Uses reportlab to create PDF that matches DriverDocumentTemplate.jsx styling.
    
    Args:
        course: Course data dict
        driver: Driver data dict
        doc_type: 'bon' | 'facture' | 'facture_finale'
        show_commission: Whether to show commission line
    
    Returns:
        BytesIO buffer containing PDF
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    course_id = course.get('id', 'N/A')
    course_id_short = course_id[:8].upper() if course_id != 'N/A' else 'N/A'
    is_final = doc_type == 'facture_finale' or course.get('invoice_status') == 'ISSUED'
    
    # Document titles and numbers
    if doc_type == 'bon':
        title = "BON DE COMMANDE VTC"
        doc_num = f"BC-{course_id_short}"
    elif is_final:
        title = "FACTURE"
        doc_num = course.get('invoice_number', f"F-{course_id_short}")
    else:
        title = "FACTURE"
        doc_num = f"F-{course_id_short}"
    
    # Calculate financials
    totals = calculate_totals(course)
    
    # Margins
    margin_left = 1.8 * cm
    margin_right = 1.8 * cm
    content_width = width - margin_left - margin_right
    
    y = height - 1.5 * cm
    
    # === LOGO HEADER ===
    if LOGO_PATH.exists():
        try:
            img = ImageReader(str(LOGO_PATH))
            # Logo: 240px width, proportional height, centered
            logo_width = 6 * cm  # ~240px at 96dpi
            img_width, img_height = img.getSize()
            aspect = img_height / img_width
            logo_height = logo_width * aspect
            
            # Center horizontally
            logo_x = (width - logo_width) / 2
            c.drawImage(img, logo_x, y - logo_height, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
            y -= logo_height + 0.8 * cm
        except Exception:
            # Fallback: text title
            c.setFont("Helvetica-Bold", 24)
            c.setFillColor(COLORS['text_primary'])
            c.drawCentredString(width / 2, y - 0.8 * cm, "JABADRIVER")
            y -= 1.5 * cm
    else:
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(COLORS['text_primary'])
        c.drawCentredString(width / 2, y - 0.8 * cm, "JABADRIVER")
        y -= 1.5 * cm
    
    # Separator line
    c.setStrokeColor(COLORS['card_border'])
    c.setLineWidth(1)
    c.line(margin_left, y, width - margin_right, y)
    y -= 0.8 * cm
    
    # === DOCUMENT HEADER ===
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(COLORS['text_primary'])
    c.drawString(margin_left, y, title)
    
    c.setFont("Helvetica", 10)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left, y - 0.5 * cm, f"N° {doc_num}")
    
    # Right side: date and ref
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin_right, y, f"Date: {course.get('date', 'N/A')}")
    c.drawRightString(width - margin_right, y - 0.4 * cm, f"Réf: #{course_id_short}")
    
    y -= 1.5 * cm
    
    # Separator
    c.setStrokeColor(COLORS['card_border'])
    c.line(margin_left, y, width - margin_right, y)
    y -= 0.8 * cm
    
    # === TWO COLUMN: PRESTATAIRE & CLIENT ===
    card_width = (content_width - 0.5 * cm) / 2
    card_height = 3.5 * cm
    card_radius = 4
    
    # Left card: Prestataire
    draw_rounded_rect(c, margin_left, y - card_height, card_width, card_height, 
                      card_radius, fill_color=COLORS['bg'], stroke_color=COLORS['card_border'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['sky'])
    c.drawString(margin_left + 0.4 * cm, card_y, "🏢 PRESTATAIRE VTC")
    card_y -= 0.5 * cm
    
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(COLORS['text_primary'])
    driver_name = driver.get('name', 'N/A') if driver else 'N/A'
    c.drawString(margin_left + 0.4 * cm, card_y, driver_name[:30])
    card_y -= 0.4 * cm
    
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_secondary'])
    if driver:
        if driver.get('company_name') and driver.get('company_name') != driver.get('name'):
            c.drawString(margin_left + 0.4 * cm, card_y, driver.get('company_name', '')[:35])
            card_y -= 0.35 * cm
        if driver.get('siret'):
            c.drawString(margin_left + 0.4 * cm, card_y, f"SIRET: {driver.get('siret')}")
            card_y -= 0.35 * cm
        if driver.get('phone'):
            c.drawString(margin_left + 0.4 * cm, card_y, f"Tél: {driver.get('phone', 'N/A')}")
            card_y -= 0.35 * cm
        if driver.get('email'):
            c.drawString(margin_left + 0.4 * cm, card_y, driver.get('email', '')[:35])
    
    # Right card: Client
    client_x = margin_left + card_width + 0.5 * cm
    draw_rounded_rect(c, client_x, y - card_height, card_width, card_height, 
                      card_radius, fill_color=COLORS['bg'], stroke_color=COLORS['card_border'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['emerald'])
    c.drawString(client_x + 0.4 * cm, card_y, "👤 CLIENT")
    card_y -= 0.5 * cm
    
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(COLORS['text_primary'])
    c.drawString(client_x + 0.4 * cm, card_y, course.get('client_name', 'N/A')[:30])
    card_y -= 0.4 * cm
    
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(client_x + 0.4 * cm, card_y, f"Tél: {course.get('client_phone', 'N/A')}")
    if course.get('client_email'):
        card_y -= 0.35 * cm
        c.drawString(client_x + 0.4 * cm, card_y, course.get('client_email', '')[:35])
    
    y -= card_height + 0.6 * cm
    
    # === COURSE DETAILS CARD ===
    details_height = 3.8 * cm
    draw_rounded_rect(c, margin_left, y - details_height, content_width, details_height, 
                      card_radius, fill_color=COLORS['bg'], stroke_color=COLORS['card_border'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['amber'])
    c.drawString(margin_left + 0.4 * cm, card_y, "📍 DÉTAILS DE LA COURSE")
    card_y -= 0.6 * cm
    
    # Date/Time row
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left + 0.4 * cm, card_y, "Date & Heure")
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(COLORS['text_primary'])
    c.drawRightString(width - margin_right - 0.4 * cm, card_y, f"{course.get('date', 'N/A')} à {course.get('time', 'N/A')}")
    card_y -= 0.6 * cm
    
    # Pickup (green dot)
    c.setFillColor(COLORS['emerald'])
    c.circle(margin_left + 0.6 * cm, card_y + 0.1 * cm, 0.15 * cm, fill=1, stroke=0)
    c.setFont("Helvetica", 7)
    c.setFillColor(COLORS['text_muted'])
    c.drawString(margin_left + 1 * cm, card_y + 0.2 * cm, "DÉPART")
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_primary'])
    pickup = course.get('pickup_address', 'N/A')[:65]
    c.drawString(margin_left + 1 * cm, card_y - 0.15 * cm, pickup)
    card_y -= 0.7 * cm
    
    # Dashed connector
    c.setStrokeColor(COLORS['card_border'])
    c.setDash(2, 2)
    c.line(margin_left + 0.6 * cm, card_y + 0.3 * cm, margin_left + 0.6 * cm, card_y - 0.1 * cm)
    c.setDash()
    card_y -= 0.3 * cm
    
    # Dropoff (red dot)
    c.setFillColor(COLORS['red'])
    c.circle(margin_left + 0.6 * cm, card_y + 0.1 * cm, 0.15 * cm, fill=1, stroke=0)
    c.setFont("Helvetica", 7)
    c.setFillColor(COLORS['text_muted'])
    c.drawString(margin_left + 1 * cm, card_y + 0.2 * cm, "ARRIVÉE")
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_primary'])
    dropoff = course.get('dropoff_address', 'N/A')[:65]
    c.drawString(margin_left + 1 * cm, card_y - 0.15 * cm, dropoff)
    
    y -= details_height + 0.6 * cm
    
    # === FINANCIAL SUMMARY CARD (green themed) ===
    # Commission NEVER shown on bon de commande (client document), facture, or facture_finale
    show_commission_in_pdf = show_commission and doc_type not in ['bon', 'facture', 'facture_finale']
    fin_height = 4.5 * cm if show_commission_in_pdf else 3.5 * cm
    if totals['has_supplements']:
        fin_height += 0.8 * cm  # Extra space for supplement rows
    
    draw_rounded_rect(c, margin_left, y - fin_height, content_width, fin_height, 
                      card_radius, fill_color=COLORS['emerald_bg'], stroke_color=COLORS['emerald_light'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['emerald'])
    c.drawString(margin_left + 0.4 * cm, card_y, "💰 RÉCAPITULATIF FINANCIER")
    card_y -= 0.7 * cm
    
    # Price rows
    row_left = margin_left + 0.4 * cm
    row_right = width - margin_right - 0.4 * cm
    
    # Base price
    c.setFont("Helvetica", 9)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(row_left, card_y, "Prix course")
    c.setFillColor(COLORS['text_primary'])
    c.drawRightString(row_right, card_y, f"{totals['price_base']:.2f} €")
    card_y -= 0.5 * cm
    
    # Supplements
    if totals['supplement_peage'] > 0:
        c.setFillColor(COLORS['text_secondary'])
        c.drawString(row_left, card_y, "Péage")
        c.setFillColor(COLORS['amber'])
        c.drawRightString(row_right, card_y, f"+{totals['supplement_peage']:.2f} €")
        card_y -= 0.5 * cm
    
    if totals['supplement_parking'] > 0:
        c.setFillColor(COLORS['text_secondary'])
        c.drawString(row_left, card_y, "Parking")
        c.setFillColor(COLORS['amber'])
        c.drawRightString(row_right, card_y, f"+{totals['supplement_parking']:.2f} €")
        card_y -= 0.5 * cm
    
    if totals['supplement_attente_minutes'] > 0:
        c.setFillColor(COLORS['text_secondary'])
        c.drawString(row_left, card_y, f"Attente ({totals['supplement_attente_minutes']} min)")
        c.setFillColor(COLORS['amber'])
        c.drawRightString(row_right, card_y, f"+{totals['supplement_attente']:.2f} €")
        card_y -= 0.5 * cm
    
    # Commission (NEVER on bon de commande client - only on internal driver views)
    # Bon de commande = document client, donc pas de commission
    # show_commission is only for internal driver dashboard display, not PDF bon de commande
    if show_commission and doc_type not in ['bon', 'facture', 'facture_finale']:
        # This block is for internal driver dashboard views only, not PDF documents
        # Separator line
        card_y -= 0.2 * cm
        c.setStrokeColor(COLORS['emerald_light'])
        c.setLineWidth(0.5)
        c.line(row_left, card_y, row_right, card_y)
        card_y -= 0.5 * cm
        
        c.setFillColor(COLORS['red'])
        c.drawString(row_left, card_y, "Commission payée")
        c.drawRightString(row_right, card_y, f"-{totals['commission']:.2f} €")
        card_y -= 0.6 * cm
        
        # Total line (green)
        c.setStrokeColor(COLORS['emerald'])
        c.setLineWidth(1.5)
        c.line(row_left, card_y + 0.2 * cm, row_right, card_y + 0.2 * cm)
        card_y -= 0.4 * cm
        
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COLORS['text_primary'])
        c.drawString(row_left, card_y, "Votre gain net")
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(COLORS['emerald'])
        c.drawRightString(row_right, card_y, f"{totals['driver_net']:.2f} €")
    else:
        # Simple total TTC for invoice
        card_y -= 0.2 * cm
        c.setStrokeColor(COLORS['emerald'])
        c.setLineWidth(1.5)
        c.line(row_left, card_y + 0.2 * cm, row_right, card_y + 0.2 * cm)
        card_y -= 0.4 * cm
        
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(COLORS['text_primary'])
        c.drawString(row_left, card_y, "Total TTC")
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(COLORS['emerald'])
        c.drawRightString(row_right, card_y, f"{totals['total']:.2f} €")
    
    y -= fin_height + 0.8 * cm
    
    # === FOOTER ===
    c.setStrokeColor(COLORS['card_border'])
    c.setLineWidth(0.5)
    c.line(margin_left, y, width - margin_right, y)
    y -= 0.5 * cm
    
    c.setFont("Helvetica", 7)
    c.setFillColor(COLORS['text_muted'])
    
    # TVA mention for invoices
    if doc_type in ['facture', 'facture_finale']:
        vat_mention = driver.get('vat_mention', 'TVA non applicable - Article 293B du CGI') if driver else 'TVA non applicable - Article 293B du CGI'
        c.drawString(margin_left, y, vat_mention)
        y -= 0.35 * cm
    
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left, y, "JABADRIVER — Service VTC Premium Île-de-France")
    y -= 0.35 * cm
    
    c.setFont("Helvetica", 7)
    c.setFillColor(COLORS['text_muted'])
    c.drawString(margin_left, y, "Contact: contact@jabadriver.fr | WhatsApp disponible")
    y -= 0.35 * cm
    c.drawString(margin_left, y, f"Réf. course: #{course_id_short}")
    
    c.save()
    buffer.seek(0)
    return buffer


# Legacy HTML generation (kept for potential future use with weasyprint)
def generate_document_html(
    course: dict, 
    driver: dict, 
    doc_type: str = 'bon',
    show_commission: bool = True
) -> str:
    """Generate HTML document - kept for reference/future weasyprint use"""
    # Implementation moved to backup - using reportlab instead
    return "<html><body>PDF generation uses reportlab</body></html>"


def generate_pdf_from_html(html: str) -> BytesIO:
    """
    Convert HTML to PDF - DISABLED (weasyprint not available).
    Use generate_unified_pdf() instead.
    """
    raise NotImplementedError("weasyprint not available - use generate_unified_pdf() instead")


# ============================================
# PLATFORM COMMISSION INVOICE (Jabadriver → Driver)
# ============================================

# Platform logo path (different from driver documents logo)
PLATFORM_LOGO_PATH = Path(__file__).parent / "assets" / "logo_jabadriver_chauffeur.png"

# Platform company info (Jabadriver) - FIXED VALUES
PLATFORM_INFO = {
    "name": "JABADRIVER",
    "legal_name": "JABADRIVER",
    "description": "Service de mise en relation VTC",
    "siret": "941 473 217 00011",
    "address": "49 boulevard Marc Chagall, 93600 Aulnay-sous-Bois",
    "email": "contact@jabadriver.fr",
    "vat_mention": "TVA non applicable — art. 293B du CGI"
}


def generate_platform_commission_invoice(
    course: dict,
    driver: dict,
    invoice_number: str = None
) -> BytesIO:
    """
    Generate Platform Commission Invoice (Jabadriver → Driver).
    
    This is a SEPARATE document from driver→client invoices.
    Used for accounting: Jabadriver invoices the driver for the commission fee.
    
    Args:
        course: Course data dict
        driver: Driver data dict
        invoice_number: Optional custom invoice number
    
    Returns:
        BytesIO buffer containing PDF
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    course_id = course.get('id', 'N/A')
    course_id_short = course_id[:8].upper() if course_id != 'N/A' else 'N/A'
    
    # Calculate commission
    totals = calculate_totals(course)
    commission_amount = totals['commission']
    
    # Invoice number
    if not invoice_number:
        # Generate invoice number: JABA-YYYY-{course_id_short}
        from datetime import datetime
        year = datetime.now().year
        invoice_number = f"JABA-{year}-{course_id_short}"
    
    # Margins
    margin_left = 1.8 * cm
    margin_right = 1.8 * cm
    content_width = width - margin_left - margin_right
    
    y = height - 1.5 * cm
    
    # === PLATFORM LOGO ===
    if PLATFORM_LOGO_PATH.exists():
        try:
            img = ImageReader(str(PLATFORM_LOGO_PATH))
            logo_width = 7 * cm
            img_width, img_height = img.getSize()
            aspect = img_height / img_width
            logo_height = logo_width * aspect
            
            # Center horizontally
            logo_x = (width - logo_width) / 2
            c.drawImage(img, logo_x, y - logo_height, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
            y -= logo_height + 1 * cm
        except Exception:
            c.setFont("Helvetica-Bold", 24)
            c.setFillColor(COLORS['text_primary'])
            c.drawCentredString(width / 2, y - 0.8 * cm, "JABADRIVER")
            y -= 1.5 * cm
    else:
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(COLORS['text_primary'])
        c.drawCentredString(width / 2, y - 0.8 * cm, "JABADRIVER")
        y -= 1.5 * cm
    
    # Separator line
    c.setStrokeColor(COLORS['card_border'])
    c.setLineWidth(1)
    c.line(margin_left, y, width - margin_right, y)
    y -= 1 * cm
    
    # === DOCUMENT HEADER ===
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(COLORS['text_primary'])
    c.drawString(margin_left, y, "FACTURE DE COMMISSION")
    
    c.setFont("Helvetica", 10)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left, y - 0.5 * cm, f"N° {invoice_number}")
    
    # Right side: date
    from datetime import datetime
    today = datetime.now().strftime("%d/%m/%Y")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin_right, y, f"Date: {today}")
    c.drawRightString(width - margin_right, y - 0.4 * cm, f"Réf. course: #{course_id_short}")
    
    y -= 1.8 * cm
    
    # Separator
    c.setStrokeColor(COLORS['card_border'])
    c.line(margin_left, y, width - margin_right, y)
    y -= 0.8 * cm
    
    # === TWO COLUMN: ÉMETTEUR (Platform) & CLIENT (Driver) ===
    card_width = (content_width - 0.5 * cm) / 2
    card_height = 4.5 * cm
    card_radius = 4
    
    # Left card: Émetteur (Jabadriver)
    draw_rounded_rect(c, margin_left, y - card_height, card_width, card_height, 
                      card_radius, fill_color=COLORS['bg'], stroke_color=COLORS['card_border'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['amber'])
    c.drawString(margin_left + 0.4 * cm, card_y, "ÉMETTEUR")
    card_y -= 0.6 * cm
    
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(COLORS['text_primary'])
    c.drawString(margin_left + 0.4 * cm, card_y, PLATFORM_INFO['legal_name'])
    card_y -= 0.45 * cm
    
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left + 0.4 * cm, card_y, PLATFORM_INFO['description'])
    card_y -= 0.4 * cm
    c.drawString(margin_left + 0.4 * cm, card_y, f"SIRET: {PLATFORM_INFO['siret']}")
    card_y -= 0.4 * cm
    c.drawString(margin_left + 0.4 * cm, card_y, PLATFORM_INFO['address'])
    card_y -= 0.4 * cm
    c.drawString(margin_left + 0.4 * cm, card_y, PLATFORM_INFO['email'])
    
    # Right card: Client (Driver)
    client_x = margin_left + card_width + 0.5 * cm
    draw_rounded_rect(c, client_x, y - card_height, card_width, card_height, 
                      card_radius, fill_color=COLORS['bg'], stroke_color=COLORS['card_border'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['emerald'])
    c.drawString(client_x + 0.4 * cm, card_y, "CLIENT (CHAUFFEUR)")
    card_y -= 0.6 * cm
    
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(COLORS['text_primary'])
    driver_name = driver.get('name', 'N/A') if driver else 'N/A'
    c.drawString(client_x + 0.4 * cm, card_y, driver_name[:30])
    card_y -= 0.45 * cm
    
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_secondary'])
    if driver:
        if driver.get('company_name') and driver.get('company_name') != driver.get('name'):
            c.drawString(client_x + 0.4 * cm, card_y, driver.get('company_name', '')[:35])
            card_y -= 0.4 * cm
        if driver.get('siret'):
            c.drawString(client_x + 0.4 * cm, card_y, f"SIRET: {driver.get('siret')}")
            card_y -= 0.4 * cm
        if driver.get('email'):
            c.drawString(client_x + 0.4 * cm, card_y, driver.get('email', '')[:35])
            card_y -= 0.4 * cm
        if driver.get('phone'):
            c.drawString(client_x + 0.4 * cm, card_y, f"Tél: {driver.get('phone', 'N/A')}")
    
    y -= card_height + 0.8 * cm
    
    # === OBJET / DESCRIPTION ===
    obj_height = 2.5 * cm
    draw_rounded_rect(c, margin_left, y - obj_height, content_width, obj_height, 
                      card_radius, fill_color=COLORS['bg'], stroke_color=COLORS['card_border'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['sky'])
    c.drawString(margin_left + 0.4 * cm, card_y, "OBJET")
    card_y -= 0.6 * cm
    
    c.setFont("Helvetica", 10)
    c.setFillColor(COLORS['text_primary'])
    c.drawString(margin_left + 0.4 * cm, card_y, f"Commission de mise en relation — Course #{course_id_short}")
    card_y -= 0.5 * cm
    
    c.setFont("Helvetica", 8)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left + 0.4 * cm, card_y, f"Date course: {course.get('date', 'N/A')} | Client: {course.get('client_name', 'N/A')}")
    
    y -= obj_height + 0.8 * cm
    
    # === FINANCIAL DETAILS ===
    fin_height = 3.5 * cm
    draw_rounded_rect(c, margin_left, y - fin_height, content_width, fin_height, 
                      card_radius, fill_color=COLORS['emerald_bg'], stroke_color=COLORS['emerald_light'])
    
    card_y = y - 0.5 * cm
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(COLORS['emerald'])
    c.drawString(margin_left + 0.4 * cm, card_y, "DÉTAIL FACTURATION")
    card_y -= 0.8 * cm
    
    row_left = margin_left + 0.4 * cm
    row_right = width - margin_right - 0.4 * cm
    
    # Course base price (commission is calculated on this)
    c.setFont("Helvetica", 9)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(row_left, card_y, "Prix de base course")
    c.setFillColor(COLORS['text_primary'])
    c.drawRightString(row_right, card_y, f"{totals['price_base']:.2f} €")
    card_y -= 0.5 * cm
    
    # Show final total if different from base
    if totals['total'] != totals['price_base']:
        c.setFillColor(COLORS['text_muted'])
        c.drawString(row_left, card_y, "Total avec suppléments")
        c.drawRightString(row_right, card_y, f"{totals['total']:.2f} €")
        card_y -= 0.5 * cm
    
    # Commission rate - clarify it's on base
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(row_left, card_y, "Commission plateforme (10% du prix de base)")
    c.setFillColor(COLORS['text_primary'])
    c.drawRightString(row_right, card_y, "10%")
    card_y -= 0.6 * cm
    
    # Separator
    c.setStrokeColor(COLORS['emerald'])
    c.setLineWidth(1.5)
    c.line(row_left, card_y + 0.15 * cm, row_right, card_y + 0.15 * cm)
    card_y -= 0.5 * cm
    
    # TOTAL Commission
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(COLORS['text_primary'])
    c.drawString(row_left, card_y, "MONTANT COMMISSION TTC")
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(COLORS['emerald'])
    c.drawRightString(row_right, card_y, f"{commission_amount:.2f} €")
    
    y -= fin_height + 1 * cm
    
    # === TVA MENTION ===
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(COLORS['text_muted'])
    c.drawString(margin_left, y, PLATFORM_INFO['vat_mention'])
    y -= 0.5 * cm
    
    # === FOOTER ===
    y -= 0.5 * cm
    c.setStrokeColor(COLORS['card_border'])
    c.setLineWidth(0.5)
    c.line(margin_left, y, width - margin_right, y)
    y -= 0.5 * cm
    
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(COLORS['text_secondary'])
    c.drawString(margin_left, y, "JABADRIVER — Plateforme de mise en relation VTC")
    y -= 0.35 * cm
    
    c.setFont("Helvetica", 7)
    c.setFillColor(COLORS['text_muted'])
    c.drawString(margin_left, y, "Ce document constitue une facture de commission pour les services de mise en relation.")
    y -= 0.35 * cm
    c.drawString(margin_left, y, f"Facture N° {invoice_number} | Réf. course: #{course_id_short}")
    
    c.save()
    buffer.seek(0)
    return buffer

