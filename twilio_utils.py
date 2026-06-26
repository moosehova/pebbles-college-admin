import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

def get_twilio_client():
    """Safely initialize the Twilio client using environment context."""
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if account_sid and auth_token:
        return Client(account_sid, auth_token)
    return None

def send_direct_sms(to_phone, message_body):
    """Dispatches a standard text message to a mobile number."""
    client = get_twilio_client()
    if not client:
        print("Twilio credentials not configured.")
        return False
        
    try:
        message = client.messages.create(
            body=message_body,
            from_=os.environ.get("TWILIO_SMS_NUMBER"),
            to=to_phone
        )
        return message.sid
    except TwilioRestException as e:
        print(f"Twilio SMS Failure: {e}")
        return False

def send_whatsapp_message(to_phone, message_body):
    """Dispatches a WhatsApp message. Phone format must include country code (e.g., +260...)"""
    client = get_twilio_client()
    if not client:
        print("Twilio credentials not configured.")
        return False
        
    # Ensure phone formatting aligns with the 'whatsapp:' protocol prefix
    formatted_to = f"whatsapp:{to_phone.strip()}" if not to_phone.startswith("whatsapp:") else to_phone.strip()
    formatted_from = f"whatsapp:{os.environ.get('TWILIO_WHATSAPP_NUMBER')}"
    
    try:
        message = client.messages.create(
            body=message_body,
            from_=formatted_from,
            to=formatted_to
        )
        return message.sid
    except TwilioRestException as e:
        print(f"Twilio WhatsApp Failure: {e}")
        return False
