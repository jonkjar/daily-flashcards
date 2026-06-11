import streamlit as st
from streamlit_google_auth import Authenticate
import json

# Fetching secrets from your Streamlit Dashboard safely
try:
    cookie_secret = st.secrets["STREAMLIT_COOKIE_SECRET"]
    client_id = st.secrets["GOOGLE_CLIENT_ID"]
    client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
except KeyError as e:
    st.error(f"❌ Missing Secret Key in Dashboard: {e}")
    st.stop()

# Structuring the target schema required by the PyPI package
google_creds = {
    "web": {
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
    }
}

# Writing the credentials file the library reads on initialization
TEMP_CREDS_FILE = "temp_google_creds.json"
with open(TEMP_CREDS_FILE, "w") as f:
    json.dump(google_creds, f)

# Instantiating the clean interface
authenticator = Authenticate(
    secret_credentials_path=TEMP_CREDS_FILE,
    cookie_name="google_auth_cookie",
    cookie_key=cookie_secret,
    redirect_uri="https://daily-flashcards.streamlit.app", # No trailing slash
)

authenticator.check_authentification()
