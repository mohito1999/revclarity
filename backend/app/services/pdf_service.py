import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from PIL import Image

from app import models

# --- Constants for CMS-1500 Form Coordinates ---
# All coordinates are (x, y) from the bottom-left of the page in inches.
# This is a simplified subset for a high-impact demo.
COORDS = {
    "patient_name": (1.3, 9.8),  # Box 2
    "patient_dob": (1.3, 9.45), # Box 3
    "insured_name": (4.5, 9.8), # Box 4
    "insured_id": (4.5, 10.15), # Box 1a
    "payer_name": (4.5, 10.6), # Top right corner
    "service_line_1_date": (1.2, 5.3), # Box 24A
    "service_line_1_cpt": (2.8, 5.3),  # Box 24D
    "service_line_1_diag": (4.6, 5.3), # Box 24E
    "service_line_1_charge": (5.2, 5.3), # Box 24F
    "total_charge": (5.2, 3.25), # Box 28
}

def generate_cms1500_pdf(claim: models.Claim) -> bytes:
    """
    Generates a PDF of a CMS-1500 form populated with claim data.
    """
    buffer = io.BytesIO()
    
    # Create a canvas
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter # (8.5 * 72, 11 * 72) points

    # 1. Draw the background image
    # The image path is relative to where the script is run from (the project root)
    try:
        img = Image.open("cms_1500_template.png")
        c.drawImage("cms_1500_template.png", 0, 0, width=width, height=height, preserveAspectRatio=True)
    except FileNotFoundError:
        # Fallback if the image isn't found - just draw a border
        c.drawString(1 * inch, 10 * inch, "CMS-1500 Template Image Not Found")
        c.rect(0.5 * inch, 0.5 * inch, 7.5 * inch, 10 * inch)


    # 2. Set font and size
    c.setFont("Helvetica", 9)

    # 3. Populate the form with data
    # Helper to safely draw strings
    def draw(key, text):
        if text and key in COORDS:
            x, y = COORDS[key]
            c.drawString(x * inch, y * inch, str(text))

    # Populate Payer and Patient Info
    draw("payer_name", claim.payer_name)
    if claim.patient:
        draw("patient_name", f"{claim.patient.last_name}, {claim.patient.first_name}")
        if claim.patient.date_of_birth:
            draw("patient_dob", claim.patient.date_of_birth.strftime("%m %d %Y"))
        draw("insured_name", f"{claim.patient.last_name}, {claim.patient.first_name}") # Assuming patient is insured
    
    # This would be the policy number in a real scenario
    draw("insured_id", str(claim.patient_id)[:12]) # Using patient ID as a placeholder

    # Populate Service Lines (we'll just do the first one for the demo)
    if claim.service_lines and len(claim.service_lines) > 0:
        sl1 = claim.service_lines[0]
        if claim.date_of_service:
             draw("service_line_1_date", claim.date_of_service.strftime("%m %d %y"))
        draw("service_line_1_cpt", sl1.cpt_code)
        draw("service_line_1_diag", "A") # Placeholder for diagnosis pointer
        draw("service_line_1_charge", str(sl1.charge) if sl1.charge else str(claim.total_amount))

    # Populate Totals
    draw("total_charge", str(claim.total_amount))
    
    # Save the PDF to the buffer
    c.showPage()
    c.save()
    
    # Rewind the buffer and return its content
    buffer.seek(0)
    return buffer.getvalue()