import os
import io
import base64
import qrcode
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from src.models import Job

class InvoicePDFGenerator:
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to src/templates relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_dir = os.path.join(base_dir, "templates")
        
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template_name = "invoice.html"

    def generate(self, job: Job, invoice_date: datetime = None) -> bytes:
        """
        Generates a PDF invoice for a given job.
        
        Args:
            job: The Job object containing customer and line items.
            invoice_date: Optional date to display on the invoice. Defaults to now.
            
        Returns:
            The generated PDF as bytes.
        """
        if invoice_date is None:
            invoice_date = datetime.now()

        due_date = invoice_date + timedelta(days=15)

        # Generate QR Code
        qr = qrcode.QRCode(box_size=10, border=0)
        # In a real app, this would be a payment URL or invoice URL
        qr.add_data(f"https://herecrm.com/invoices/{job.id}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
        template = self.env.get_template(self.template_name)
        
        # Prepare context
        context = {
            "job": job,
            "invoice_date": invoice_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "qr_code_base64": qr_code_base64
        }
        
        # Render HTML
        html_content = template.render(**context)
        
        # Convert to PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        
        return pdf_bytes
