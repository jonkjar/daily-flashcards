# --- 1. CONFIGURATION & SECRETS ---
st.set_page_config(page_title="Secure Flashcards", page_icon="🧠", layout="centered")

try:
    client_id = st.secrets["GOOGLE_CLIENT_ID"]
    client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
except KeyError as e:
    st.error(f"❌ Missing Secret Key in Dashboard: {e}")
    st.stop()

# Define core endpoints
AUTHORIZE_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Initialize using positional arguments in order:
# 1. client_id, 2. client_secret, 3. authorize_endpoint, 4. token_endpoint
oauth2 = OAuth2Component(
    client_id,
    client_secret,
    AUTHORIZE_ENDPOINT,
    TOKEN_ENDPOINT
)

# Render Authentication Gates
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
        st.rerun()
    else:
        st.stop()

# Your application dashboard and flashcard loops go here...

if not st.session_state.get("connected", False):
    st.title("🧠 Secure Daily Flashcards")
    st.write("Please sign in with your Google account to access your private study deck.")
    authenticator.login()
    st.stop()

# --- 2. USER IS AUTHENTICATED ---
user_email = st.session_state.get("user_info", {}).get("email")
user_name = st.session_state.get("user_info", {}).get("name")
user_id = st.session_state.get("oauth_id") # Unique ID updated by the package

# Add a logout button in the sidebar
with st.sidebar:
    st.write(f"Logged in as: **{user_name}**")
    st.caption(user_email)
    if st.button("Log Out"):
        authenticator.logout()
        st.rerun()

# --- 3. MULTI-USER STORAGE LOGIC ---
DATA_FILE = "global_flashcards_db.json"

def load_all_users_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
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
            card["streak"] = 0
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

# Initialize session states for tracking review progress
if "review_index" not in st.session_state:
    st.session_state.review_index = 0
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False

st.title(f"🧠 {user_name.split()[0]}'s Flashcards")
st.divider()

# --- SECTION 4: METRICS DASHBOARD ---
st.header("📊 Your Memory Stats")
total_cards = len(data)
memorized_cards = sum(1 for card in data.values() if card.get("level", 1) >= 5)
learning_cards = total_cards - memorized_cards
avg_streak = sum(card.get("streak", 0) for card in data.values()) / total_cards if total_cards > 0 else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Cards", total_cards)
with col2:
    st.metric("Mastered (Lvl 5)", memorized_cards)
with col3:
    st.metric("Learning", learning_cards)

st.divider()

# --- SECTION 5: ADD DAILY CARD ---
st.header("📝 Today's New Card")
if today_str in data:
    st.success("✨ Today's card is locked in!")
    st.info(f"**Front:** {data[today_str]['front']}  \n**Back:** {data[today_str]['back']}")
else:
    with st.form("add_card_form", clear_on_submit=True):
        front = st.text_input("Front (Concept/Question)")
        back = st.text_input("Back (Answer/Definition)")
        submitted = st.form_submit_button("Save Today's Card", use_container_width=True)
        
        if submitted:
            if front.strip() and back.strip():
                data[today_str] = {
                    "front": front.strip(), 
                    "back": back.strip(),
                    "level": 1,
                    "streak": 0,
                    "reviews": 0
                }
                save_user_cards(user_key, data)
                st.success("Card saved!")
                st.rerun()
            else:
                st.error("Please fill out both sides of the card.")

st.divider()

# --- SECTION 6: GENERATE REVIEW QUEUE ---
today_dt = datetime.now()
review_queue = []
milestones = [
    {"label": "Exactly 1 Week Ago", "days": 7},
    {"label": "Exactly 2 Weeks Ago", "days": 14},
    {"label": "Exactly 3 Weeks Ago", "days": 21},
    {"label": "Exactly 1 Month Ago", "days": 30},
    {"label": "Exactly 2 Months Ago", "days": 60},
]

for milestone in milestones:
    target_date_str = (today_dt - timedelta(days=milestone["days"])).strftime("%Y-%m-%d")
    if target_date_str in data:
        card = data[target_date_str]
        if not any(q_card == card for _, q_card, _ in review_queue):
            review_queue.append((f"{milestone['label']}", card, target_date_str))

for i in range(7):
    check_date_str = (today_dt - timedelta(days=i)).strftime("%Y-%m-%d")
    if check_date_str in data:
        card = data[check_date_str]
        if not any(q_card == card for _, q_card, _ in review_queue):
            review_queue.append(("Past Week", card, check_date_str))

# --- SECTION 7: INTERACTIVE REVIEW INTERFACE ---
st.header("🧠 Today's Review")

if not review_queue:
    st.write("No reviews due today.")
elif st.session_state.review_index >= len(review_queue):
    st.balloons()
    st.success("🎉 Review complete!")
    if st.button("Review Again", use_container_width=True):
        st.session_state.review_index = 0
        st.session_state.show_answer = False
        st.rerun()
else:
    label, current_card, original_date = review_queue[st.session_state.review_index]
    progress = (st.session_state.review_index) / len(review_queue)
    st.progress(progress, text=f"Card {st.session_state.review_index + 1} of {len(review_queue)}")
    
    st.markdown(f"**Origin:** {label} | **Level:** {current_card['level']}/5 | **Streak:** {current_card['streak']} 🔥")
    st.markdown(f'<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;"><h3 style="color: #31333F;">{current_card["front"]}</h3></div>', unsafe_allow_html=True)

    if st.session_state.show_answer:
        st.markdown(f'<div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; border-left: 5px solid #4caf50; margin-bottom: 20px;"><h3 style="color: #2e7d32;">{current_card["back"]}</h3></div>', unsafe_allow_html=True)
        
        pass_col, fail_col = st.columns(2)
        with pass_col:
            if st.button("✅ Got It", type="primary", use_container_width=True):
                data[original_date]["level"] = min(5, current_card["level"] + 1)
                data[original_date]["streak"] += 1
                data[original_date]["reviews"] += 1
                save_user_cards(user_key, data)
                st.session_state.review_index += 1
                st.session_state.show_answer = False
                st.rerun()
        with fail_col:
            if st.button("❌ Missed It", type="secondary", use_container_width=True):
                data[original_date]["level"] = 1
                data[original_date]["streak"] = 0
                data[original_date]["reviews"] += 1
                save_user_cards(user_key, data)
                st.session_state.review_index += 1
                st.session_state.show_answer = False
                st.rerun()
    else:
        if st.button("👀 Reveal Answer", type="secondary", use_container_width=True):
            st.session_state.show_answer = True
            st.rerun()
