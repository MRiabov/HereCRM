# Research: Live Location Tracking

## 1. Twilio WhatsApp Location Protocol

**Research Question**: How does Twilio deliver location messages from WhatsApp?
**Finding**:

- Twilio webhooks for WhatsApp location messages include `Latitude` and `Longitude` fields in the POST body (application/x-www-form-urlencoded).
- Additional fields: `Address`, `Label`.
- **Constraint**: The WhatsApp Business API **does not support "Live Location"** (shifting real-time pin). It only supports "Current Location" (static snapshot).
- **Implication**: We cannot subscribe to a stream. The employee must share their "Current Location" periodically or at specific events (Start Shift, Depart Job).

**Decision**:

- We will process standard messages where `Latitude` and `Longitude` are present.
- We will instruct employees to use "Send Your Current Location" rather than "Share Live Location".

## 2. Google Maps URL Parsing (Fallback)

**Research Question**: What URL formats do we need to parse for SMS fallback?
**Finding**:

- Short links (Android/iOS share): `https://maps.app.goo.gl/randomString`
- Desktop links: `https://www.google.com/maps/place/.../@lat,lng,zoom...`
- Search links: `https://www.google.com/maps/search/?api=1&query=lat,lng`

**Decision**:

- We will use an internal service method `LocationService.resolve_url(url)` that:
  1. Follows redirects (HEAD request) to get the full URL if it is a short link.
  2. Extracts `lat` and `lng` using regex from the final URL.
  3. Uses `GeocodingService` (Nominatim) as a final fallback if only an address string is found (less reliable).

## 3. OpenRouteService Integration

**Research Question**: What is the most efficient API for 1-to-1 ETA?
**Finding**:

- **Matrix API**: Best for 1-to-Many or Many-to-Many. Returns duration/distance table.
- **Directions API**: Best for 1-to-1 with detailed path.
- **Decision**: Use **Matrix API** even for 1-to-1 if possible as it is often faster and returns just the summary we need (seconds, meters). However, `Directions` is fine and often simpler to debug. We will use `Directions` for `get_eta` initially as we only need "duration".

## 4. Spec 013 Coordination

**Finding**:

- Spec 013 implements `OpenRouteServiceAdapter`.
- We must verify if it uses `openrouteservice-py` library or raw HTTP.
- **Decision**: We will inspect the code base (or 013 PR) and extend `RoutingService`. We will implement a `get_eta(origin, dest)` method on the provider interface.
