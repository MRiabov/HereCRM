from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

# Your Account SID and Auth Token from twilio.com/console
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

try:
    message = client.messages.create(
        from_='+35312657257',  # Your Twilio number
        body='This is a test message from your Twilio script!',
        to='+353899485670'    # Your destination number
    )

    print(f"Message sent successfully! SID: {message.sid}")

except Exception as e:
    print(f"An error occurred: {e}")