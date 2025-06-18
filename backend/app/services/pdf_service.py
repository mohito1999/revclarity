import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from PIL import Image
import logging

from app import models

logger = logging.getLogger(__name__)

# --- Comprehensive CMS-1500 Form Coordinates (in inches from bottom-left) ---
# This map is the "secret sauce" to making the PDF look good.
COORDS = {
    # Payer Info
    "payer_name": (3.8, 10.6),

    # Patient & Insured Info
    "insured_id": (4.8, 10.15), # Box 1a
    "patient_name": (1.0, 9.8), # Box 2
    "patient_dob_mm": (1.0, 9.45), # Box 3
    "patient_dob_dd": (1.3, 9.45),
    "patient_dob_yy": (1.6, 9.45),
    "patient_sex": (2.4, 9.45),
    "insured_name": (4.2, 9.8), # Box 4

    # Diagnoses
    "diag_a": (1.0, 6.45), # Box 21
    "diag_b": (1.0, 6.25),
    "diag_c": (3.0, 6.45),
    "diag_d": (3.0, 6.25),

    # Service Lines (Box 24) - Y coordinates for each line
    "sl_y": [5.3, 5.05, 4.8, 4.55, 4.3, 4.05],
    "sl_x": {
        "date_from_mm": 0.9,
        "date_from_dd": 1.2,
        "date_from_yy": 1.5,
        "place": 2.3,
        "cpt": 2.8,
        "diag_ptr": 4.6,
        "charge": 5.1,
        "units": 6.2,
    },

    # Totals
    "total_charge": (5.1, 3.25), # Box 28
    "amount_paid": (6.1, 3.25), # Box 29 (patient responsibility)
}

def generate_cms1500_pdf(claim: models.Claim) -> bytes:
    """
    Generates a professional-looking CMS-1500 PDF by drawing data onto a template image.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # 1. Draw the background template image
    template_path = "cms_1500_template.jpg"
    try:
        c.drawImage(template_path, 0, 0, width=width, height=height)
    except Exception as e:
        logger.error(f"Could not draw template image from {template_path}: {e}")
        c.drawString(1 * inch, 10 * inch, "ERROR: CMS-1500 Template Image Not Found.")

    # 2. Set font for data entry
    c.setFont("Helvetica", 10)

    # 3. Helper function to draw data at specific coordinates
    def draw(x, y, text):
        if text:
            c.drawString(x * inch, y * inch, str(text))

    # --- Populate Header ---
    draw(COORDS["payer_name"][0], COORDS["payer_name"][1], "HealthFirst Insurance") # Use Payer Name from claim
    draw(COORDS["insured_id"][0], COORDS["insured_id"][1], "HF-11223344") # Placeholder

    # --- Populate Patient & Insured Info (Box 2, 3, 4) ---
    if claim.patient:
        draw(COORDS["patient_name"][0], COORDS["patient_name"][1], f"{claim.patient.last_name}, {claim.patient.first_name}")
        draw(COORDS["insured_name"][0], COORDS["insured_name"][1], f"{claim.patient.last_name}, {claim.patient.first_name}")
        if claim.patient.date_of_birth:
            draw(COORDS["patient_dob_mm"][0], COORDS["patient_dob_mm"][1], claim.patient.date_of_birth.strftime("%m"))
            draw(COORDS["patient_dob_dd"][0], COORDS["patient_dob_dd"][1], claim.patient.date_of_birth.strftime("%d"))
            draw(COORDS["patient_dob_yy"][0], COORDS["patient_dob_yy"][1], claim.patient.date_of_birth.strftime("%Y"))
        draw(COORDS["patient_sex"][0], COORDS["patient_sex"][1], "X") # Placeholder

    # --- Populate Diagnoses (Box 21) ---
    all_icd_codes = []
    if claim.service_lines:
        for sl in claim.service_lines:
            all_icd_codes.extend(sl.icd10_codes or [])
    unique_icd_codes = sorted(list(set(all_icd_codes)))

    if len(unique_icd_codes) > 0: draw(COORDS["diag_a"][0], COORDS["diag_a"][1], f"A. {unique_icd_codes[0]}")
    if len(unique_icd_codes) > 1: draw(COORDS["diag_b"][0], COORDS["diag_b"][1], f"B. {unique_icd_codes[1]}")
    if len(unique_icd_codes) > 2: draw(COORDS["diag_c"][0], COORDS["diag_c"][1], f"C. {unique_icd_codes[2]}")
    if len(unique_icd_codes) > 3: draw(COORDS["diag_d"][0], COORDS["diag_d"][1], f"D. {unique_icd_codes[3]}")

    # --- Populate Service Lines (Box 24) ---
    if claim.service_lines:
        for i, sl in enumerate(claim.service_lines):
            if i >= len(COORDS["sl_y"]): break # Stop if we have more lines than space
            
            y = COORDS["sl_y"][i]
            x_map = COORDS["sl_x"]

            if claim.date_of_service:
                draw(x_map["date_from_mm"], y, claim.date_of_service.strftime("%m"))
                draw(x_map["date_from_dd"], y, claim.date_of_service.strftime("%d"))
                draw(x_map["date_from_yy"], y, claim.date_of_service.strftime("%y"))
            
            draw(x_map["place"], y, "11") # Placeholder for "Office"
            draw(x_map["cpt"], y, sl.cpt_code)
            draw(x_map["diag_ptr"], y, sl.diagnosis_pointer or "A") # Use pointer or default
            draw(x_map["charge"], y, f"{sl.charge:.2f}" if sl.charge else "0.00")
            draw(x_map["units"], y, "1") # Placeholder

    # --- Populate Totals (Box 28, 29) ---
    draw(COORDS["total_charge"][0], COORDS["total_charge"][1], f"{claim.total_amount:.2f}" if claim.total_amount else "0.00")
    draw(COORDS["amount_paid"][0], COORDS["amount_paid"][1], f"{claim.patient_responsibility_amount:.2f}" if claim.patient_responsibility_amount else "0.00")

    c.save()
    buffer.seek(0)
    return buffer.getvalue()