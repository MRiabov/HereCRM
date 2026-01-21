# Quickstart: Ad Automation & Integrations

## 1. Provisioning Credentials

To enable integrations, you must first provision a configuration.

1. Generate a setup link (Admin CLI or UI):

   ```bash
   # (Future command example)
   spec-kitty integration generate-link --type META_CAPI
   > https://herecrm.io/supply-key?auth-id=...
   ```

2. User visits link and enters credentials (pixel ID, token, etc.).
3. External site posts to `/api/v1/integrations/provision`.
4. Configuration is now active in HereCRM.

## 2. Inbound API (Zapier / Landing Pages)

Use your provisioned `INBOUND_KEY` to submit leads.

### Create Lead (Bash)

```bash
curl -X POST https://your-crm.com/api/v1/integrations/leads \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "phone": "+15550001234",
    "source": "Google Ads"
  }'
```

Response:

```json
{
  "customer_id": "550e8400-e29b-...",
  "is_existing": false
}
```

## 3. Verifying Webhooks (For Developers)

If you configured a generic Webhook, HereCRM will POST to your URL when a job is booked.

**Headers**:

- `X-HereCRM-Event`: `job.booked`
- `X-HereCRM-Signature`: `sha256=...`

**Verification Code (Python)**:

```python
import hmac
import hashlib

def verify_signature(payload_body, secret, signature_header):
    expected = hmac.new(
        key=secret.encode(), 
        msg=payload_body, 
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature_header)
```

## 4. Meta CAPI Troubleshooting

- **Check Logs**: All CAPI responses are logged. Look for "Meta CAPI Success" or "Meta CAPI Error".
- **Test Events**: In Facebook Events Manager, use the "Test Events" tab. Add the `test_event_code` to your `META_CAPI` config payload to see events appear in real-time.
