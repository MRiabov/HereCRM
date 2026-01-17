# Research for Feature 006: Professional Invoices

## PDF Generation Engine

- **Decision**: `WeasyPrint`
- **Rationale**:
  - User requested "very professional" look.
  - WeasyPrint allows perfect styling control using standard CSS (paged media support).
  - Easier to maintain HTML templates than programmatically drawing PDFs with reportlab.
- **Alternatives Considered**:
  - `reportlab`: Harder to style, requires learning custom API for layout.
  - `xhtml2pdf`: Older, less support for modern CSS.

## File Storage

- **Decision**: S3-Compatible Storage (Backblaze B2)
- **Rationale**:
  - User requested ability to send links, not just attachments.
  - Keeps local server storage clean (stateless application server).
  - Cost-effective (Backblaze).
- **Alternatives Considered**:
  - Local `media/` folder: Simpler dev, but harder to scale or share public links securely without exposing server files directly.

## Sending Mechanism

- **Decision**: Send both Attachment and Link.
- **Rationale**: User explicitly requested both options for convenience.
