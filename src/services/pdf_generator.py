import os
from datetime import datetime
from typing import Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from weasyprint import HTML
from src.models import Job

class InvoicePDFGenerator:
    def __init__(self, template_dir: Optional[str] = None):
        if template_dir is None:
            # Default to src/templates relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_dir = os.path.join(base_dir, "templates")
        
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True  # CRITICAL: Prevent template injection
        )
        self.template_name = "invoice.html"

    def generate(self, job: Job, invoice_date: Optional[datetime] = None) -> bytes:
        """
        Generates a PDF invoice for a given job.
        
        Args:
            job: The Job object containing customer and line items.
            invoice_date: Optional date to display on the invoice. Defaults to now.
            
        Returns:
            The generated PDF as bytes.
            
        Raises:
            ValueError: If the invoice template is not found.
            RuntimeError: If PDF generation fails.
        """
        if invoice_date is None:
            invoice_date = datetime.now()
            
        try:
            template = self.env.get_template(self.template_name)
            
            # Prepare context
            context = {
                "job": job,
                "invoice_date": invoice_date.strftime("%Y-%m-%d")
            }
            
            # Render HTML
            html_content = template.render(**context)
            
            # Convert to PDF
            pdf_bytes = HTML(string=html_content).write_pdf()
            
            return pdf_bytes

        except TemplateNotFound as e:
            raise ValueError(f"Invoice template not found: {self.template_name}") from e
        except Exception as e:
            raise RuntimeError(f"Failed to generate invoice PDF: {str(e)}") from e
