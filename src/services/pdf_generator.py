import os
from datetime import datetime
from typing import Optional
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from weasyprint import HTML
from src.models import Job, Quote

class PDFGenerator:
    def __init__(self, template_dir: Optional[str] = None):
        if template_dir is None:
            # Default to src/templates relative to this file
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            template_dir = os.path.join(base_dir, "templates")
        
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True  # CRITICAL: Prevent template injection
        )

    def generate_invoice(self, job: Job, invoice_date: Optional[datetime] = None, payment_link: Optional[str] = None) -> bytes:
        """
        Generates a PDF invoice for a given job.
        
        Args:
            job: The Job object containing customer and line items.
            invoice_date: Optional date to display on the invoice. Defaults to now.
            payment_link: Optional payment link to display on the invoice.
            
        Returns:
            The generated PDF as bytes.
            
        Raises:
            ValueError: If the invoice template is not found.
            RuntimeError: If PDF generation fails.
        """
        if invoice_date is None:
            invoice_date = datetime.now()
            
        try:
            template_name = getattr(self, "template_name", "invoice.html")
            template = self.env.get_template(template_name)
            
            # Prepare context
            context = {
                "job": job,
                "invoice_date": invoice_date.strftime("%Y-%m-%d"),
                "due_date": invoice_date.strftime("%Y-%m-%d"), # Fallback if no due date logic
                "payment_link": payment_link
            }
            
            # Render HTML
            html_content = template.render(**context)
            
            # Convert to PDF
            pdf_bytes = HTML(string=html_content).write_pdf()
            
            return pdf_bytes

        except TemplateNotFound as e:
            raise ValueError("Invoice template not found: invoice.html") from e
        except Exception as e:
            raise RuntimeError(f"Failed to generate invoice PDF: {str(e)}") from e

    def generate(self, job: Job, invoice_date: Optional[datetime] = None, payment_link: Optional[str] = None) -> bytes:
        """Alias for generate_invoice to support existing tests."""
        return self.generate_invoice(job, invoice_date=invoice_date, payment_link=payment_link)

    def generate_quote(self, quote: Quote, issue_date: Optional[datetime] = None, expiry_date: Optional[datetime] = None) -> bytes:
        """
        Generates a PDF quote.

        Args:
            quote: The Quote object.
            issue_date: Optional issue date. Defaults to quote.created_at or now.
            expiry_date: Optional expiry date.

        Returns:
            The generated PDF as bytes.
        """
        if issue_date is None:
            issue_date = quote.created_at or datetime.now()

        try:
            template = self.env.get_template("quote.html")

            context = {
                "quote": quote,
                "issue_date": issue_date.strftime("%B %d, %Y"),
                "expiry_date": expiry_date.strftime("%B %d, %Y") if expiry_date else "N/A"
            }

            html_content = template.render(**context)
            pdf_bytes = HTML(string=html_content).write_pdf()
            return pdf_bytes

        except TemplateNotFound as e:
            raise ValueError("Quote template not found: quote.html") from e
# ... (lines 98-99)
        except Exception as e:
            raise RuntimeError(f"Failed to generate quote PDF: {str(e)}") from e

# Singleton instance for module-level access
pdf_generator = PDFGenerator()

# Alias for backward compatibility if needed, though we will refactor usage.
InvoicePDFGenerator = PDFGenerator
