# tests/backend/test_twilio.py

from dotenv import load_dotenv
load_dotenv()  # carga .env desde la raíz del proyecto

import os
import pytest
from twilio.rest import Client

@pytest.mark.integration
def test_twilio_credentials_connect():
    sid   = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")

    assert sid, "TWILIO_ACCOUNT_SID no está definido"
    assert token, "TWILIO_AUTH_TOKEN no está definido"

    client = Client(sid, token)
    acct = client.api.accounts(sid).fetch()
    assert acct.friendly_name, "No se pudo obtener friendly_name de la cuenta"
