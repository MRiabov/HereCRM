import streamlit as st
import httpx
import hmac
import hashlib
import json
import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add src to path to import settings if possible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.config import settings
    DEFAULT_SECRET = settings.whatsapp_app_secret
except Exception:
    DEFAULT_SECRET = os.getenv("WHATSAPP_APP_SECRET", "dummy_secret")

st.set_page_config(page_title="WhatsApp AI CRM Simulator", page_icon="💬")

st.title("WhatsApp AI CRM Simulator")

with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("API Base URL", value=os.getenv("API_BASE_URL", "http://localhost:8000"))
    secret = st.text_input("WhatsApp Secret", value=DEFAULT_SECRET, type="password")
    phone_number = st.text_input("Phone Number", value="1234567890")

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Type a message..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare payload
    payload = {"from_number": phone_number, "body": prompt}
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Calculate signature
    if secret:
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()
    else:
        signature = ""

    headers = {
        "X-Hub-Signature-256": f"sha256={signature}",
        "Content-Type": "application/json",
    }

    # Send request
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = httpx.post(
                    f"{api_url}/webhook",
                    content=payload_bytes,
                    headers=headers,
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    reply = data.get("reply", "No reply received.")
                else:
                    reply = f"Error {response.status_code}: {response.text}"
            except Exception as e:
                reply = f"Request failed: {str(e)}"

        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
