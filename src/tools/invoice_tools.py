from pydantic.v1 import BaseModel, Field

class SendInvoiceTool(BaseModel):
    """Send an invoice to a customer.
    Triggered when user says 'send invoice to X' or similar."""

    query: str = Field(
        ..., description="Name or phone to find the customer", max_length=100
    )
    force_regenerate: bool = Field(
        False, description="If true, generates a new invoice even if one exists."
    )
