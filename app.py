import streamlit as st
import json
import os
from datetime import datetime, timedelta
from streamlit_oauth import OAuth2Component

# =====================================================================
# 1. SETUP & AUTHENTICATION CONFIGURATION
# =====================================================================
# Must be the very first running Streamlit command
st.set_page_config(page_title="Secure Flashcards", page_icon="🧠", layout="centered")

try:
    client_id = st.secrets["GOOGLE_CLIENT_ID"]
    client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
except KeyError as e:
    st.error(f"❌ Missing Secret Key in Dashboard: {e}")
    st.stop()

# Define strict positional endpoints for the OAuth component
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Initialize OAuth Component using clean positional arguments
oauth2 = OAuth2Component(
    client_id,
    client_secret,
    AUTHORIZE_ENDPOINT,
    TOKEN_ENDPOINT
)

# =====================================================================
# 2. THE LOGIN GATEWAY (The Guard at the Door)
# =====================================================================
if "auth" not in st.session_state:
    st.title("🧠 Secure Daily Flashcards")
    st.write("Please sign in with your Google account to access your private study deck.")
    
    # Render the dynamic authentication button
    result = oauth2.authorize_button(
        name="Continue with Google",
        icon="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg",
        redirect_uri="https://daily-flashcards.streamlit.app",
        scope="openid email profile",
        key="google_auth",
    )
    
    if result:
        st.session_state["auth"] = result
        st.rerun()
    else:
        # Halt application processing cleanly until a login payload returns
        st.stop()

# =====================================================================
# 3. USER PROFILE RESOLUTION
# =====================================================================
token_data = st.session_state["auth"]

# streamlit-oauth provides a built-in method to safely query Google for the user's profile
try:
    # Pass the active token block directly to the package analyzer
    user_info = oauth2.get_user_info(token_data)
    
    # Extract your clean, verified registration records
    user_email = user_info.get("email", "unknown@gmail.com")
    user_name = user_info.get("name", "User")
    user_id = user_info.get("id", user_email.split('@')[0]) # Use Google's internal ID, or email prefix as fallback
except Exception as e:
    # Ultimate security fallback layout if the query errors out
    user_email = "unknown@gmail.com"
    user_name = "User"
    user_id = "default_user"

# Add a logout button in the sidebar
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
    # Separate space inside the JSON file for this specific user ID
    user_space = global_data.get(user_key, {})
    
    # Backward compatibility checking inside user space
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

# Load data strictly for the logged-in user
user_key = f"user_{user_id}"
data = get_user_cards(user_key)
today_str = datetime.now().strftime("%Y-%m-%d")

# Initialize session states for tracking review
