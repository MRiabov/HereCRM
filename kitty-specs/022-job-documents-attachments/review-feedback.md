**Issue 1**: **Incomplete Email Parsing**
Reference: `src/api/routes.py` lines 490 and 519.
Description: The `From` field from Postmark often contains the name and email (e.g., `"John Doe <john@example.com>"`). The current implementation passes this raw string directly to `auth_service.get_or_create_user_by_identity`. This causes `AuthService` to create users with the full string (including the name and brackets) as their email address, which is incorrect and prevents matching existing users by email if the format varies slightly.
Fix: Use `email.utils.parseaddr` to extract the actual email address from the `From` header before using it.
Example:

```python
import email.utils
# ...
raw_from = payload.get("From", "")
name, from_email = email.utils.parseaddr(raw_from)
if not from_email:
    # Handle error or fallback
    pass
# Use from_email for lookup
```
