import streamlit as st
import json
import os
import base64
from datetime import datetime, timedelta
from streamlit_oauth import OAuth2Component

# =====================================================================
# 1. SETUP & AUTHENTICATION CONFIGURATION
# =====================================================================
st.set_page_config(page_title="Secure Flashcards", page_icon="🧠", layout="centered")

try:
    client_id = st.secrets["GOOGLE_CLIENT_ID"]
    client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
except KeyError as e:
    st.error(f"❌ Missing Secret Key in Dashboard: {e}")
    st.stop()

AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

oauth2 = OAuth2Component(
    client_id,
    client_secret,
    AUTHORIZE_ENDPOINT,
    TOKEN_ENDPOINT
)

# =====================================================================
# 2. THE LOGIN GATEWAY 
# =====================================================================
if "auth" not in st.session_state:
    st.title("🧠 Secure Daily Flashcards")
    st.write("Please sign in with your Google account to access your private study deck.")
    
    result = oauth2.authorize_button(
        name="Continue with Google",
        icon="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg",
        redirect_uri="https://daily-flashcards.streamlit.app",
        scope="openid email profile",
        key="google_auth",
    )
    
    if result:
        st.session_state["auth"] = result
        # Flush the Google tracking code from the URL before rebooting
        if hasattr(st, "query_params"):
            st.query_params.clear()
        elif hasattr(st, "experimental_set_query_params"):
            st.experimental_set_query_params()
        st.rerun()
    else:
        st.stop()

# =====================================================================
# 3. USER PROFILE RESOLUTION
# =====================================================================
token_data = st.session_state["auth"]

try:
    id_token = token_data["token"]["id_token"]
    payload = id_token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    decoded_payload = base64.urlsafe_b64decode(payload)
    user_info = json.loads(decoded_payload)
    
    user_email = user_info.get("email", "unknown@gmail.com")
    user_name = user_info.get("name", "User")
    user_id = user_info.get("sub", user_email.split('@')[0])
except Exception as e:
    st.error(f"Token Decoding Error: {e}")
    user_email = "unknown@gmail.com"
    user_name = "User"
    user_id = "default_user"

with st.sidebar:
    st.write(f"Logged in as: **{user_name}**")
    st.caption(user_email)
    if st.button("Log Out", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# =====================================================================
# 4. MULTI-USER STORAGE LOGIC
# =====================================================================
DATA_FILE = "global_flashcards_db.json"

def load_all_users_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_all_users_data(global_data):
    with open(DATA_FILE, "w") as f:
        json.dump(global_data, f, indent=4)

def get_user_cards(user_key):
    global_data = load_all_users_data()
    user_space = global_data.get(user_key, {})
    
    for date, card in user_space.items():
        if "level" not in card:
            card["level"] = 1
        if "streak" not in card:
            card["streak"] = 0
        if "reviews" not in card:
            card["reviews"] = 0
    return user_space

def save_user_cards(user_key, user_cards):
    global_data = load_all_users_data()
    global_data[user_key] = user_cards
    save_all_users_data(global_data)

user_key = f"user_{user_id}"
data = get_user_cards(user_key)
today_str = datetime.now().strftime("%Y-%m-%d")

if "review_index"
