
from typing import Any, Dict, Optional
from src.models import Business, Customer, Job, User
from datetime import datetime

def build_template_context(
    business: Optional[Business] = None,
    customer: Optional[Customer] = None,
    job: Optional[Job] = None,
    technician: Optional[User] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Builds a flat dictionary context for template rendering.
    Supports dot notation access via nested objects.
    """
    context = {}
    
    if business:
        context["business"] = business
        
    if customer:
        context["customer"] = customer
        # Add a convenience helper for first name
        if not hasattr(customer, "first_name") or not customer.first_name:
            # Split from name if first_name is missing
            name = customer.name or "Client"
            customer.first_name = name.split()[0]
            
    if job:
        context["job"] = job
        # Format date/time helpers if scheduled
        if job.scheduled_at:
            # We add these as attributes to a proxy or just directly to job if it's safe (SQLAlchemy objects)
            # Better to use a dedicated dict for formatted values
            context["job_date"] = job.scheduled_at.strftime("%A, %b %d")
            context["job_time"] = job.scheduled_at.strftime("%H:%M")
        
        # Total amount
        context["job_total"] = f"{job.value:.2f}" if job.value is not None else "0.00"

    if technician:
        context["technician"] = technician
        
    if extra:
        context.update(extra)
        
    return context
