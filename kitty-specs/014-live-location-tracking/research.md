# Research: Live Location Tracking

## 1. WhatsApp Business API Protocol

**Correction**: We use the direct WhatsApp Business API (Cloud API), not Twilio for WhatsApp.

**Research Question**: How does WhatsApp deliver location messages via webhook?
**Finding**:

- The payload structure is a JSON object with `entry` -> `changes` -> `value` -> `messages`.
- Message type is `location`.
- Payload fragment:

```json
{
  "messages": [
    {
      "from": "16315555555",
      "id": "wamid.HBgL...",
      "timestamp": "1660000000",
      "location": {
        "latitude": 37.483307,
        "longitude": 122.148981,
        "name": "Facebook HQ",
        "address": "1 Hacker Way, Menlo Park, CA 94025"
      },
      "type": "location"
    }
  ]
}
```

- **Constraint**: The WhatsApp Business API **does not support "Live Location"** (shifting real-time pin). It only supports "Current Location" (static snapshot).

**Decision**:

- Update `WhatsAppService` webhook handler to detect `type="location"` messages.
- Extract `location.latitude` and `location.longitude` directly from the JSON.

## 2. Google Maps URL Parsing (Fallback) - SMS Only

**Research Question**: What URL formats do we need to parse for SMS fallback?
**Finding**:

- Short links (Android/iOS share): `https://maps.app.goo.gl/randomString`
- Desktop links: `https://www.google.com/maps/place/.../@lat,lng,zoom...`
- Search links: `https://www.google.com/maps/search/?api=1&query=lat,lng`

**Decision**:

- We will use an internal service method `LocationService.resolve_url(url)` that:
  1. Follows redirects (HEAD request) to get the full URL if it is a short link.
  2. Extracts `lat` and `lng` using regex from the final URL.

## 3. OpenRouteService Integration

**Research Question**: What is the most efficient API for 1-to-1 ETA?
**Finding**:

- **Matrix API**: Best for 1-to-Many or Many-to-Many. Returns duration/distance table.
- **Directions API**: Best for 1-to-1 with detailed path.
- **Decision**: Use **Directions API** or **Matrix API** via the adapter from Spec 013. We will prioritize using the `RoutingService` interface to allow implementation swapping.
