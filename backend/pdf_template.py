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
    """Calculate all financial values for a course"""
    price_base = course.get('price_base') or course.get('price_total', 0) or 0
    supplement_peage = course.get('supplement_peage', 0) or 0
    supplement_parking = course.get('supplement_parking', 0) or 0
    supplement_attente_minutes = course.get('supplement_attente_minutes', 0) or 0
    supplement_attente = course.get('supplement_attente', 0) or supplement_attente_minutes * 0.5
    
    total = price_base + supplement_peage + supplement_parking + supplement_attente
    commission_rate = 0.10
    commission = total * commission_rate
    driver_net = total - commission
    
    return {
        "price_base": price_base,
        "supplement_peage": supplement_peage,
        "supplement_parking": supplement_parking,
        "supplement_attente_minutes": supplement_attente_minutes,
        "supplement_attente": supplement_attente,
        "total": total,
        "commission": commission,
        "driver_net": driver_net,
        "has_supplements": supplement_peage > 0 or supplement_parking > 0 or supplement_attente_minutes > 0
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
        title = "FACTURE PROVISOIRE"
        doc_num = f"PRO-{course_id_short}"
    
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
    fin_height = 4.5 * cm if show_commission and doc_type != 'facture_finale' else 3.5 * cm
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
    
    # Commission (only for bon de commande)
    if show_commission and doc_type != 'facture_finale':
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


def get_document_css() -> str:
    """Get the unified CSS styles for documents - matches frontend exactly"""
    return """
    @page {
        size: A4;
        margin: 1.5cm;
    }
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 10pt;
        color: #1f2937;
        background: #ffffff;
        line-height: 1.5;
    }
    
    /* Container */
    .document {
        max-width: 100%;
        padding: 0;
    }
    
    /* Logo Header */
    .logo-header {
        text-align: center;
        margin-bottom: 25px;
        padding-bottom: 20px;
        border-bottom: 2px solid #e5e7eb;
    }
    
    .logo-header img {
        max-width: 240px;
        height: auto;
    }
    
    /* Document Header */
    .document-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 25px;
        padding-bottom: 15px;
        border-bottom: 1px solid #e5e7eb;
    }
    
    .document-title {
        font-size: 18pt;
        font-weight: 700;
        color: #111827;
        margin-bottom: 5px;
    }
    
    .document-number {
        font-size: 10pt;
        color: #6b7280;
    }
    
    .document-meta {
        text-align: right;
        color: #6b7280;
        font-size: 9pt;
    }
    
    .document-meta p {
        margin-bottom: 3px;
    }
    
    /* Cards */
    .card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
    }
    
    .card-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    
    .card-icon {
        width: 36px;
        height: 36px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }
    
    .card-icon.emerald { background: rgba(16, 185, 129, 0.15); color: #10b981; }
    .card-icon.sky { background: rgba(14, 165, 233, 0.15); color: #0ea5e9; }
    .card-icon.amber { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
    .card-icon.red { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
    
    .card-label {
        font-size: 9pt;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .card-title {
        font-size: 11pt;
        font-weight: 600;
        color: #111827;
    }
    
    /* Two Column Layout */
    .two-columns {
        display: flex;
        gap: 15px;
        margin-bottom: 15px;
    }
    
    .two-columns .card {
        flex: 1;
        margin-bottom: 0;
    }
    
    /* Info Row */
    .info-row {
        display: flex;
        justify-content: space-between;
        padding: 6px 0;
        border-bottom: 1px solid #f3f4f6;
    }
    
    .info-row:last-child {
        border-bottom: none;
    }
    
    .info-label {
        color: #6b7280;
        font-size: 9pt;
    }
    
    .info-value {
        color: #111827;
        font-weight: 500;
        font-size: 9pt;
    }
    
    .info-value.highlight {
        color: #10b981;
        font-weight: 700;
    }
    
    .info-value.amber {
        color: #f59e0b;
    }
    
    .info-value.red {
        color: #ef4444;
    }
    
    /* Address Section */
    .address-section {
        margin-bottom: 15px;
    }
    
    .address-item {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 8px;
    }
    
    .address-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-top: 4px;
        flex-shrink: 0;
    }
    
    .address-dot.green { background: #10b981; }
    .address-dot.red { background: #ef4444; }
    
    .address-content {
        flex: 1;
    }
    
    .address-label {
        font-size: 8pt;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .address-text {
        color: #111827;
        font-size: 9pt;
    }
    
    .address-connector {
        width: 2px;
        height: 15px;
        background: #e5e7eb;
        margin-left: 4px;
        border-style: dashed;
    }
    
    /* Financial Summary */
    .financial-card {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
    }
    
    .financial-card .card-icon {
        background: rgba(16, 185, 129, 0.2);
    }
    
    .financial-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 0;
        font-size: 10pt;
    }
    
    .financial-row.separator {
        border-top: 1px solid #d1fae5;
        padding-top: 12px;
        margin-top: 4px;
    }
    
    .financial-row.total {
        border-top: 2px solid #10b981;
        padding-top: 12px;
        margin-top: 8px;
    }
    
    .financial-label {
        color: #6b7280;
    }
    
    .financial-value {
        font-weight: 600;
        color: #111827;
    }
    
    .financial-value.positive {
        color: #f59e0b;
    }
    
    .financial-value.negative {
        color: #ef4444;
    }
    
    .financial-value.total {
        color: #10b981;
        font-size: 14pt;
        font-weight: 700;
    }
    
    .financial-label.total {
        color: #111827;
        font-weight: 600;
    }
    
    /* Footer */
    .document-footer {
        margin-top: 30px;
        padding-top: 15px;
        border-top: 1px solid #e5e7eb;
        font-size: 8pt;
        color: #9ca3af;
    }
    
    .document-footer p {
        margin-bottom: 4px;
    }
    
    .footer-company {
        font-weight: 600;
        color: #6b7280;
    }
    """


def generate_document_html(
    course: dict, 
    driver: dict, 
    doc_type: str = 'bon',
    show_commission: bool = True
) -> str:
    """
    Generate HTML document matching frontend design exactly.
    
    Args:
        course: Course data dict
        driver: Driver data dict  
        doc_type: 'bon' | 'facture' | 'facture_finale'
        show_commission: Whether to show commission line
    
    Returns:
        Complete HTML string
    """
    course_id = course.get('id', 'N/A')
    course_id_short = course_id[:8].upper() if course_id != 'N/A' else 'N/A'
    is_final = doc_type == 'facture_finale' or course.get('invoice_status') == 'ISSUED'
    
    # Document titles and numbers
    titles = {
        'bon': 'BON DE COMMANDE VTC',
        'facture': 'FACTURE PROVISOIRE',
        'facture_finale': 'FACTURE'
    }
    title = titles.get(doc_type, 'DOCUMENT')
    
    if doc_type == 'bon':
        doc_num = f"BC-{course_id_short}"
    elif is_final:
        doc_num = course.get('invoice_number', f"F-{course_id_short}")
    else:
        doc_num = f"PRO-{course_id_short}"
    
    # Calculate financials
    totals = calculate_totals(course)
    
    # Logo
    logo_base64 = get_logo_base64()
    logo_html = f'<img src="{logo_base64}" alt="JABADRIVER" />' if logo_base64 else '<h1 style="font-size: 24pt; color: #111827;">JABADRIVER</h1>'
    
    # Driver info
    driver_name = driver.get('name', 'N/A') if driver else 'N/A'
    driver_company = driver.get('company_name', '') if driver else ''
    driver_siret = driver.get('siret', '') if driver else ''
    driver_address = driver.get('address', '') if driver else ''
    driver_phone = driver.get('phone', 'N/A') if driver else 'N/A'
    driver_email = driver.get('email', 'N/A') if driver else 'N/A'
    
    # Build driver details
    driver_details = f'<p style="font-weight: 600; color: #111827; margin-bottom: 4px;">{driver_name}</p>'
    if driver_company and driver_company != driver_name:
        driver_details += f'<p style="color: #4b5563; font-size: 9pt;">{driver_company}</p>'
    if driver_siret:
        driver_details += f'<p style="color: #6b7280; font-size: 9pt;">SIRET: {driver_siret}</p>'
    if driver_address:
        driver_details += f'<p style="color: #6b7280; font-size: 9pt;">{driver_address[:60]}</p>'
    driver_details += f'<p style="color: #6b7280; font-size: 9pt;">Tél: {driver_phone}</p>'
    driver_details += f'<p style="color: #6b7280; font-size: 9pt;">{driver_email}</p>'
    
    # Financial rows
    financial_rows = f'''
        <div class="financial-row">
            <span class="financial-label">Prix course</span>
            <span class="financial-value">{totals["price_base"]:.2f} €</span>
        </div>
    '''
    
    if totals["supplement_peage"] > 0:
        financial_rows += f'''
        <div class="financial-row">
            <span class="financial-label">Péage</span>
            <span class="financial-value positive">+{totals["supplement_peage"]:.2f} €</span>
        </div>
        '''
    
    if totals["supplement_parking"] > 0:
        financial_rows += f'''
        <div class="financial-row">
            <span class="financial-label">Parking</span>
            <span class="financial-value positive">+{totals["supplement_parking"]:.2f} €</span>
        </div>
        '''
    
    if totals["supplement_attente_minutes"] > 0:
        financial_rows += f'''
        <div class="financial-row">
            <span class="financial-label">Attente ({totals["supplement_attente_minutes"]} min)</span>
            <span class="financial-value positive">+{totals["supplement_attente"]:.2f} €</span>
        </div>
        '''
    
    # Commission row (only for bon de commande and draft invoices)
    if show_commission and doc_type != 'facture_finale':
        financial_rows += f'''
        <div class="financial-row separator">
            <span class="financial-label" style="color: #ef4444;">Commission payée</span>
            <span class="financial-value negative">-{totals["commission"]:.2f} €</span>
        </div>
        '''
        # Driver net total
        financial_rows += f'''
        <div class="financial-row total">
            <span class="financial-label total">Votre gain net</span>
            <span class="financial-value total">{totals["driver_net"]:.2f} €</span>
        </div>
        '''
    else:
        # Simple total TTC for final invoice
        financial_rows += f'''
        <div class="financial-row total">
            <span class="financial-label total">Total TTC</span>
            <span class="financial-value total">{totals["total"]:.2f} €</span>
        </div>
        '''
    
    # TVA mention
    tva_mention = ''
    if doc_type in ['facture', 'facture_finale']:
        driver_vat = driver.get('vat_mention', 'TVA non applicable - Article 293B du CGI') if driver else 'TVA non applicable - Article 293B du CGI'
        tva_mention = f'<p>{driver_vat}</p>'
    
    html = f'''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>{title} - {doc_num}</title>
    <style>
        {get_document_css()}
    </style>
</head>
<body>
    <div class="document">
        <!-- Logo Header -->
        <div class="logo-header">
            {logo_html}
        </div>
        
        <!-- Document Header -->
        <div class="document-header">
            <div>
                <div class="document-title">{title}</div>
                <div class="document-number">N° {doc_num}</div>
            </div>
            <div class="document-meta">
                <p>Date: {course.get('date', 'N/A')}</p>
                <p>Réf: #{course_id_short}</p>
            </div>
        </div>
        
        <!-- Two Column: Prestataire & Client -->
        <div class="two-columns">
            <!-- Prestataire -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon sky">🏢</div>
                    <div>
                        <div class="card-label">Prestataire VTC</div>
                    </div>
                </div>
                <div>
                    {driver_details}
                </div>
            </div>
            
            <!-- Client -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon emerald">👤</div>
                    <div>
                        <div class="card-label">Client</div>
                    </div>
                </div>
                <div>
                    <p style="font-weight: 600; color: #111827; margin-bottom: 4px;">{course.get('client_name', 'N/A')}</p>
                    <p style="color: #6b7280; font-size: 9pt;">Tél: {course.get('client_phone', 'N/A')}</p>
                    {'<p style="color: #6b7280; font-size: 9pt;">' + course.get('client_email', '') + '</p>' if course.get('client_email') else ''}
                </div>
            </div>
        </div>
        
        <!-- Course Details -->
        <div class="card">
            <div class="card-header">
                <div class="card-icon amber">📍</div>
                <div>
                    <div class="card-label">Détails de la course</div>
                </div>
            </div>
            
            <div class="info-row">
                <span class="info-label">Date & Heure</span>
                <span class="info-value">{course.get('date', 'N/A')} à {course.get('time', 'N/A')}</span>
            </div>
            
            <div class="address-section" style="margin-top: 12px;">
                <div class="address-item">
                    <div class="address-dot green"></div>
                    <div class="address-content">
                        <div class="address-label">Départ</div>
                        <div class="address-text">{course.get('pickup_address', 'N/A')}</div>
                    </div>
                </div>
                
                <div class="address-connector"></div>
                
                <div class="address-item">
                    <div class="address-dot red"></div>
                    <div class="address-content">
                        <div class="address-label">Arrivée</div>
                        <div class="address-text">{course.get('dropoff_address', 'N/A')}</div>
                    </div>
                </div>
            </div>
            
            {f'<div class="info-row"><span class="info-label">Distance</span><span class="info-value">{course.get("distance_km")} km</span></div>' if course.get('distance_km') else ''}
        </div>
        
        <!-- Financial Summary -->
        <div class="card financial-card">
            <div class="card-header">
                <div class="card-icon emerald">💰</div>
                <div>
                    <div class="card-label">Récapitulatif financier</div>
                </div>
            </div>
            
            {financial_rows}
        </div>
        
        <!-- Footer -->
        <div class="document-footer">
            {tva_mention}
            <p class="footer-company">JABADRIVER — Service VTC Premium Île-de-France</p>
            <p>Contact: contact@jabadriver.fr | WhatsApp disponible</p>
            <p>Réf. course: #{course_id_short}</p>
        </div>
    </div>
</body>
</html>
    '''
    
    return html


def generate_pdf_from_html(html: str) -> BytesIO:
    """
    Convert HTML to PDF using weasyprint.
    
    Args:
        html: HTML string to convert
    
    Returns:
        BytesIO buffer containing PDF
    """
    from weasyprint import HTML, CSS
    
    buffer = BytesIO()
    
    # Generate PDF
    doc = HTML(string=html)
    doc.write_pdf(buffer)
    
    buffer.seek(0)
    return buffer


def generate_unified_pdf(
    course: dict, 
    driver: dict, 
    doc_type: str = 'bon',
    show_commission: bool = True
) -> BytesIO:
    """
    Main entry point: Generate PDF with unified template.
    
    Args:
        course: Course data dict
        driver: Driver data dict
        doc_type: 'bon' | 'facture' | 'facture_finale'
        show_commission: Whether to show commission line
    
    Returns:
        BytesIO buffer containing PDF
    """
    html = generate_document_html(course, driver, doc_type, show_commission)
    return generate_pdf_from_html(html)
