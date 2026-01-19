import streamlit as st
import httpx
import hmac
import hashlib
import json
import os
import sys
import re
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

st.set_page_config(page_title="HereCRM - Text-based CRM", page_icon="src/assets/favicon.webp")

def is_valid_phone(phone: str) -> bool:
    # Basic international format validation: + followed by 1-15 digits
    # Or just digits if no plus. 
    # We strip spaces/dashes before checking in our backend, but let's be 
    # helpful in the UI.
    clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
    return bool(re.match(r"^\+?[1-9]\d{1,14}$", clean_phone))

# --- Phone Number Modal/Overlay ---
if "phone_number" not in st.session_state:
    st.title("Welcome to HereCRM")
    st.subheader("Please enter your phone number to continue")
    
    with st.container(border=True):
        temp_phone = st.text_input(
            "Phone Number", 
            placeholder="+1 234 567 8900",
            help="Enter your international phone number."
        )
        
        is_valid = True
        if temp_phone:
            if not is_valid_phone(temp_phone):
                st.error("⚠️ Invalid phone format. Please use international format (e.g. +353 89 948 5670)")
                is_valid = False
            else:
                st.success("✅ Phone format looks good!")
        
        if st.button("Start Chatting", disabled=not temp_phone or not is_valid):
            # Normalize before saving
            st.session_state.phone_number = "".join(c for c in temp_phone if c.isdigit() or c == "+")
            st.rerun()
    st.stop()

phone_number = st.session_state.phone_number

st.title("HereCRM")
st.caption("Advanced Text-based CRM")

# Multi-user session management
col1, col2 = st.columns([2, 1])
with col1:
    st.info(f"Connected as: **{phone_number}**")
with col2:
    if st.button("Change Number", help="Change the active phone number"):
        del st.session_state.phone_number
        st.session_state.messages = []
        st.rerun()

# Load configuration from environment variables
api_url = os.getenv("API_BASE_URL", "http://localhost:8000")
secret = DEFAULT_SECRET

with st.sidebar:
    st.header("Settings")
    st.text_input("API Base URL", value=api_url, disabled=True)
    if secret:
        st.text_input("Security Protocol", value="HMAC-SHA256 Enabled", disabled=True)
    else:
        st.error("Security Key Missing")
    
    if st.button("Clear Chat History", type="secondary"):
        st.session_state.messages = []
        st.rerun()
    
    dev_mode = st.checkbox("Dev Mode", value=False, help="Show technical details and traces")

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
    st.session_state.messages = []  
    load_history()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message.get("metadata") and dev_mode:
            with st.expander("🔍 Trace: Technical Details"):
                st.json(message["metadata"])

if prompt := st.chat_input("Type a message..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Prepare payload
    payload = {"from_number": phone_number, "body": prompt}
    payload_bytes = json.dumps(payload).encode("utf-8")

    # Calculate signature
    signature = ""
    if secret:
        signature = hmac.new(
            secret.encode("utf-8"), payload_bytes, hashlib.sha256
        ).hexdigest()

    headers = {
        "X-Hub-Signature-256": f"sha256={signature}",
        "Content-Type": "application/json",
    }

    # Send request
    with st.chat_message("assistant"):
        with st.spinner("Processing..."):
            try:
                response = httpx.post(
                    f"{api_url}/webhook",
                    content=payload_bytes,
                    headers=headers,
                    timeout=60.0
                )

                if response.status_code == 200:
                    data = response.json()
                    reply = data.get("reply", "No response.")
                    load_history()
                    st.rerun()
                else:
                    st.error(f"Backend Error {response.status_code}: {response.text}")
            except Exception as e:
                st.error(f"Connection failed: {str(e)}")

