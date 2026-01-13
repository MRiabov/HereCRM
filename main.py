from fastapi import FastAPI, Request, Response
import requests
import os

app = FastAPI()

TOKEN = os.environ["WA_TOKEN"]
PHONE_ID = os.environ["WA_PHONE_ID"]


VERIFY_TOKEN = "vibecoding"


@app.get("/webhook")
async def verify_webhook(req: Request):
    if req.query_params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(
            content=req.query_params.get("hub.challenge"), media_type="text/plain"
        )
    return "error"


@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()
    print(data)

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        from_number = msg["from"]
        msg_body = msg.get("text", {}).get("body", "No text body")
        print(f"Received message from {from_number}: {msg_body}")

        requests.post(
            f"https://graph.facebook.com/v22.0/{PHONE_ID}/messages",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "type": "text",
                "text": {"body": "ok"},
            },
        )
    except Exception as e:
        print("No message:", e)

    return "ok"
