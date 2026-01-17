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

# Multi-user session management
col1, col2 = st.columns([2, 1])
with col1:
    phone_number = st.text_input("Current Simulator Phone Number", value="1234567890", help="This simulates which user is sending messages.")
with col2:
    if st.button("Reset Session", help="Clears local and remote history for this phone"):
        st.session_state.messages = []
        # Optional: Add remote clear if needed
        st.rerun()

# Load configuration from environment variables
api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
secret = DEFAULT_SECRET

with st.sidebar:
    st.header("Configuration (Read-only)")
    st.text_input("API Base URL", value=api_url, disabled=True, help="Set via API_BASE_URL environment variable")
    if secret:
        st.text_input("WhatsApp Secret", value="******", disabled=True, help="Set via WHATSAPP_APP_SECRET environment variable")
    else:
        st.error("WhatsApp Secret Not Set")

def load_history():
    try:
        response = httpx.get(f"{api_url}/history/{phone_number}")
        if response.status_code == 200:
            st.session_state.messages = response.json()
        else:
            st.error(f"Failed to load history: {response.status_code}")
    except Exception as e:
        st.error(f"Error loading history: {e}")

if "messages" not in st.session_state or st.session_state.get("last_phone") != phone_number:
    st.session_state.last_phone = phone_number
    st.session_state.messages = []  # Initialize with empty list before loading
    load_history()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Debug Inspector for Metadata (Tool Calls)
        if message.get("metadata"):
            with st.expander("🔍 Debug: Tool Call Info"):
                st.json(message["metadata"])

if prompt := st.chat_input("Type a message..."):
    # Clear local session messages to ensure we are in sync or just append
    # To keep it simple, we append locally first for responsiveness
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
                    # Refresh history to get the metadata for the response just received
                    load_history()
                    st.rerun()
                else:
                    reply = f"Error {response.status_code}: {response.text}"
            except Exception as e:
                reply = f"Request failed: {str(e)}"

        st.markdown(reply)
