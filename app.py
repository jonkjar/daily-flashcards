import streamlit as st
import json
import os
from datetime import datetime, timedelta

DATA_FILE = "flashcards_data.json"

st.set_page_config(page_title="Smart Flashcards", page_icon="🧠", layout="centered")

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            raw_data = json.load(f)
            # Backward compatibility: Upgrade old data structure if needed
            for date, card in raw_data.items():
                if "level" not in card:
                    card["level"] = 1
                    card["streak"] = 0
                    card["reviews"] = 0
            return raw_data
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# Session state initialization
if "review_index" not in st.session_state:
    st.session_state.review_index = 0
if "show_answer" not in st.session_state:
    st.session_state.show_answer = False

data = load_data()
today_str = get_today_str()

st.title("🧠 Smart Flashcards")
st.write("Track your learning progress and master long-term memory.")
st.divider()

# --- SECTION 1: METRICS DASHBOARD ---
st.header("📊 Your Memory Stats")

total_cards = len(data)
memorized_cards = sum(1 for card in data.values() if card.get("level", 1) >= 5)
learning_cards = total_cards - memorized_cards
avg_streak = sum(card.get("streak", 0) for card in data.values()) / total_cards if total_cards > 0 else 0

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Cards", total_cards)
with col2:
    st.metric("Fully Memorized (Lvl 5)", memorized_cards, delta=f"{memorized_cards} mastered" if memorized_cards else None)
with col3:
    st.metric("Still Learning", learning_cards)

# Quick insight message
if total_cards > 0:
    st.caption(f"📈 Your current average correct streak across all cards is **{avg_streak:.1f}**.")

st.divider()

# --- SECTION 2: ADD DAILY CARD ---
st.header("📝 Today's New Card")
if today_str in data:
    st.success(f"✨ Today's card is locked in!")
    st.info(f"**Front:** {data[today_str]['front']}  \n**Back:** {data[today_str]['back']}  \n**Current Mastery:** Level {data[today_str]['level']}/5")
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
                save_data(data)
                st.success("Card saved! Dashboard updated.")
                st.rerun()
            else:
                st.error("Please fill out both sides of the card.")

st.divider()

# --- SECTION 3: GENERATE REVIEW QUEUE ---
today_dt = datetime.now()
review_queue = []

milestones = [
    {"label": "Exactly 1 Week Ago", "days": 7},
    {"label": "Exactly 2 Weeks Ago", "days": 14},
    {"label": "Exactly 3 Weeks Ago", "days": 21},
    {"label": "Exactly 1 Month Ago", "days": 30},
    {"label": "Exactly 2 Months Ago", "days": 60},
]

# 1. Grab Milestone Cards
for milestone in milestones:
    target_date_str = (today_dt - timedelta(days=milestone["days"])).strftime("%Y-%m-%d")
    if target_date_str in data:
        card = data[target_date_str]
        if not any(q_card == card for _, q_card, _ in review_queue):
            review_queue.append((f"{milestone['label']}", card, target_date_str))

# 2. Grab Rolling Past Week Cards
for i in range(7):
    check_date_str = (today_dt - timedelta(days=i)).strftime("%Y-%m-%d")
    if check_date_str in data:
        card = data[check_date_str]
        if not any(q_card == card for _, q_card, _ in review_queue):
            review_queue.append((f"Past Week", card, check_date_str))

# --- SECTION 4: INTERACTIVE REVIEW INTERFACE ---
st.header("🧠 Today's Review")

if not review_queue:
    st.write("No cards to review yet. Keep adding them daily!")
elif st.session_state.review_index >= len(review_queue):
    st.balloons()
    st.success("🎉 You finished all of today's reviews! Statistics updated.")
    if st.button("Review Queue Again", use_container_width=True):
        st.session_state.review_index = 0
        st.session_state.show_answer = False
        st.rerun()
else:
    label, current_card, original_date = review_queue[st.session_state.review_index]
    
    # Progress Bar
    progress = (st.session_state.review_index) / len(review_queue)
    st.progress(progress, text=f"Card {st.session_state.review_index + 1} of {len(review_queue)}")
    
    # Card Meta Info
    st.markdown(f"**Origin:** {label} ({original_date}) | **Mastery Level:** {current_card['level']}/5 | **Streak:** {current_card['streak']} 🔥")
    
    # Styled Flashcard Concept box
    st.markdown(
        f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px;">
            <p style="color: #31333F; font-size: 14px; margin: 0;">CONCEPT</p>
            <h3 style="color: #31333F; margin-top: 5px;">{current_card['front']}</h3>
        </div>
        """, 
        unsafe_allow_html=True,
    )

    if st.session_state.show_answer:
        st.markdown(
            f"""
            <div style="background-color: #e8f5e9; padding: 20px; border-radius: 10px; border-left: 5px solid #4caf50; margin-bottom: 20px;">
                <p style="color: #2e7d32; font-size: 14px; margin: 0;">ANSWER</p>
                <h3 style="color: #2e7d32; margin-top: 5px;">{current_card['back']}</h3>
            </div>
            """, 
            unsafe_allow_html=True,
        )
        
        # Performance Tracking Buttons
        st.write("How did you do?")
        pass_col, fail_col = st.columns(2)
        
        with pass_col:
            if st.button("✅ I Got It Right!", type="primary", use_container_width=True):
                # Upgrade card metrics
                data[original_date]["level"] = min(5, current_card["level"] + 1)
                data[original_date]["streak"] += 1
                data[original_date]["reviews"] += 1
                save_data(data)
                
                # Move to next card
                st.session_state.review_index += 1
                st.session_state.show_answer = False
                st.rerun()
                
        with fail_col:
            if st.button("❌ I Missed It", type="secondary", use_container_width=True):
                # Penalty for missing card
                data[original_date]["level"] = 1 # Drops back to level 1
                data[original_date]["streak"] = 0 # Resets streak
                data[original_date]["reviews"] += 1
                save_data(data)
                
                # Move to next card
                st.session_state.review_index += 1
                st.session_state.show_answer = False
                st.rerun()
    else:
        if st.button("👀 Reveal Answer", type="secondary", use_container_width=True):
            st.session_state.show_answer = True
            st.rerun()