import logging
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os

from app import models

logger = logging.getLogger(__name__)

# Set up Jinja2 environment to load templates
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = Environment(loader=FileSystemLoader(template_dir))

def generate_claim_summary_pdf(claim: models.Claim) -> bytes:
    """
    Generates a professional claim summary PDF from an HTML template.
    """
    try:
        template = jinja_env.get_template("claim_export_template.html")
        
        # Pass the claim and its related patient object to the template
        html_string = template.render(claim=claim, patient=claim.patient)
        
        # Generate PDF from the rendered HTML
        pdf_bytes = HTML(string=html_string).write_pdf()
        
        return pdf_bytes
        
    except Exception as e:
        logger.error(f"Failed to generate PDF for claim {claim.id}: {e}", exc_info=True)
        # Return a simple error PDF if generation fails
        error_html = f"<h1>Error</h1><p>Could not generate PDF for claim {claim.id}.</p><p>Error: {e}</p>"
        return HTML(string=error_html).write_pdf()