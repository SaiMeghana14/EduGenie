import streamlit as st
import json, os, time, jwt, requests
from utils import GeminiClient
from db import DB
import streamlit.components.v1 as components
from streamlit_webrtc import webrtc_streamer

# ---------------------- Config ----------------------
st.set_page_config(page_title='EduGenie ', layout='wide', initial_sidebar_state='expanded')
st.markdown("<style> .stApp { background: #F8FAFC; } </style>", unsafe_allow_html=True)
st.markdown("""
<style>
a {
    color: #2563EB;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
footer, .stAppFooter {
    visibility: hidden;
}
a {
    text-decoration: none;
    color: #2563EB;
}
a:hover {
    color: #1D4ED8;
}
</style>
""", unsafe_allow_html=True)

# Load assets
ASSETS = {}
try:
    with open('assets/config.json', 'r') as f:
        ASSETS = json.load(f)
except:
    ASSETS = {}

# ---------------------- Clients ----------------------
gemini = GeminiClient(api_key=os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
db = DB('edugenie.db')
JWT_SECRET = st.secrets.get("JWT_SECRET", "supersecret123")  # fallback if missing

# ---------------------- Sidebar ----------------------
st.sidebar.image(ASSETS.get('logo',''), width=120)
st.sidebar.title("EduGenie 🚀")
name = st.sidebar.text_input("Your Name", value="Guest")

page = st.sidebar.radio(
    "Navigate to",
    [
        "Landing",
        "AI Tutor",
        "Upload & Summarize",
        "Quizzes",
        "Peer Rooms",
        "Live Room",
        "Progress & Leaderboard",
        "Settings"
    ]
)
st.sidebar.markdown("---")
st.sidebar.info("Made with ❤️ for learners by EduGenie Team")
# ---------------------- Landing Page ----------------------
if page == "Landing":
    col1, col2 = st.columns([2,3])
    with col1:
        st.title("EduGenie — Gemini-Powered Learning 📚✨")
        st.markdown("### 🧠 Personalized | 📊 Gamified | 🎯 Fun Learning Experience")
        st.markdown("- Chat with AI Tutor (text + voice) 🤖🎤")
        st.markdown("- Upload notes & get instant summaries 📄💡")
        st.markdown("- Earn XP, badges & climb the leaderboard 🏆🔥")
        if st.button("Start Learning! 🚀"):
            st.balloons()
            st.success("Welcome aboard, learner! ✨")
    with col2:
        st.image("assets/hero.gif", width=320)
        st.markdown("### 🌟 Features")
        st.progress(100, text="AI Tutor • Quizzes • Live Peer Rooms • XP Tracker")

# ---------------------- AI Tutor ----------------------
elif page == "AI Tutor":
    st.header("AI Tutor 🤖")
    st.caption("Ask EduGenie anything! Type your question or upload an image for visual analysis.")

    query = st.text_area("💬 Ask a question:", value="Explain Nyquist sampling theorem in simple terms.")

    def get_cached_response(prompt):
        resp = gemini.chat(prompt)
        return resp.get("text") or resp.get("mock") or resp.get("error") or ""

    col1, col2 = st.columns([3,1])
    with col1:
        if st.button("Ask Gemini 🧠"):
            with st.spinner("Thinking and reasoning... 💭"):
                text = get_cached_response(query)
                st.markdown("### 📘 EduGenie says:")
                st.write(text)
                # TTS via GeminiClient
                audio_file = gemini.tts(text)
                st.audio(audio_file)
                db.cache_set(f"chat:{query[:64]}", text, int(time.time()))
                st.balloons()
    with col2:
        st.subheader("📷 Image Analysis")
        img = st.file_uploader("Upload image (png/jpg/jpeg)", type=['png','jpg','jpeg'])
        if img is not None and st.button("Analyze Image 🧩"):
            with st.spinner("Analyzing... 🔍"):
                result = gemini.chat("Analyze this image step-by-step.")
                st.write(result.get('text', 'No response.'))

# ---------------------- Upload & Summarize ----------------------
elif page == "Upload & Summarize":
    st.header("📄 Upload Notes or PDFs")
    uploaded = st.file_uploader("Upload PDF or TXT", type=['pdf','txt'])
    if uploaded:
        st.info(f"📂 File: {uploaded.name} uploaded successfully!")
        raw = ""
        if uploaded.type == "application/pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(uploaded)
            for p in reader.pages: raw += p.extract_text() + "\n"
        else:
            raw = uploaded.getvalue().decode('utf-8')
        st.write(raw[:800])
        if st.button("Summarize & Generate Flashcards ✨"):
            with st.spinner("Processing your notes... ⚡"):
                summ = gemini.summarize(raw)
                flashcards = gemini.generate_quiz(raw[:120], difficulty='Medium', n_questions=5)
                st.subheader("📜 Summary")
                st.write(summ)
                st.subheader("🎴 Flashcards")
                for i, fc in enumerate(flashcards if isinstance(flashcards, list) else []):
                    q = fc.get('q', f"Card {i+1}")
                    a = fc.get('a', "No answer provided")
                    st.markdown(f"**Q{i+1}.** {q}")
                    st.write(f"**A.** {a}")
                st.balloons()

# ---------------------- Quizzes ----------------------
elif page == "Quizzes":
    st.header("🧩 Quick Quiz Generator")
    topic = st.text_input("Enter a topic:", value="Fourier Transform")
    diff = st.selectbox("Difficulty Level", ["Easy","Medium","Hard"])
    n = st.slider("Number of Questions", 1, 10, 5)
    if st.button("Generate Quiz 🧠"):
        with st.spinner("Crafting smart questions..."):
            quiz = gemini.generate_quiz(topic, difficulty=diff, n_questions=n)
            st.session_state['quiz'] = quiz
    if st.session_state.get('quiz'):
        quiz = st.session_state['quiz']
        score = 0
        for idx, q in enumerate(quiz):
            st.markdown(f"**Q{idx+1}.** {q.get('q', 'No question')}")
            ans = st.text_input(f"Your Answer Q{idx+1}", key=f"q{idx}")
            if st.button(f"Submit Q{idx+1}"):
                feedback = gemini.chat(f'Grade: Q: {q.get("q")} | User: {ans}. Give correct/incorrect + feedback.')
                st.write(feedback.get('text','Feedback not available'))
                if q.get('answer') and ans.strip().lower() == q.get('answer','').lower():
                    score += 1
        if st.button("Finish Quiz 🏁"):
            xp = score * (1 if diff=='Easy' else 2 if diff=='Medium' else 3)
            db.add_xp(name, xp)
            st.success(f"✅ Score: {score}/{len(quiz)} | XP earned: {xp} ✨")
            st.balloons()

# ---------------------- Peer Rooms ----------------------
elif page == "Peer Rooms":
    st.header("👥 Peer Study Rooms")
    st.write("Collaborate in real time with your friends using JWT-secured peer rooms.")
    room = st.text_input("Room name:", value="demo-room")
    if room:
        payload = {"room": room, "user": name, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        if isinstance(token, bytes): token = token.decode("utf-8")
    if st.button("Join Peer Room 🔑"):
        with open("peer_room.html","r",encoding="utf-8") as f:
            html = f.read()
        html = html.replace("<!--JWT_TOKEN-->", token)
        html = html.replace("<!--FIREBASE_CONFIG-->", json.dumps({
            "apiKey": st.secrets["FIREBASE_API_KEY"],
            "authDomain": st.secrets["FIREBASE_AUTH_DOMAIN"],
            "databaseURL": st.secrets["FIREBASE_DB_URL"],
            "projectId": st.secrets["FIREBASE_PROJECT_ID"],
            "storageBucket": st.secrets["FIREBASE_STORAGE_BUCKET"],
            "messagingSenderId": st.secrets["FIREBASE_MESSAGING_SENDER_ID"],
            "appId": st.secrets["FIREBASE_APP_ID"],
        }))
        components.html(html, height=600, scrolling=True)

# ---------------------- WebRTC Live Room ----------------------
elif page == "Live Room":
    st.header("🎥 Live Video Study Room")
    st.info("Start your camera and mic to join the real-time study session!")
    webrtc_streamer(key="edu_webrtc")

# ---------------------- Progress & Leaderboard ----------------------
elif page == "Progress & Leaderboard":
    st.header("Progress & Leaderboard 🏆")
    xp = db.get_xp(name)
    st.metric("XP", xp)
    st.progress(min(xp / 200, 1.0))

    # 🎖️ Show badges based on XP level
    st.subheader("Your Learning Badge:")
    if xp < 100:
        st.image(ASSETS.get("badge_easy", ""), width=120)
        st.caption("Level: Beginner 🌱 — Keep going!")
    elif xp < 250:
        st.image(ASSETS.get("badge_medium", ""), width=120)
        st.caption("Level: Intermediate 🚀 — You’re doing great!")
    else:
        st.image(ASSETS.get("badge_hard", ""), width=120)
        st.caption("Level: Expert 🧠 — You’re unstoppable!")

    # 🏁 Leaderboard
    st.subheader("Top Learners")
    lb = db.get_leaderboard(limit=10)
    st.table(lb)

# ---------------------- Settings ----------------------
elif page == "Settings":
    st.header("⚙️ Settings / Debug")
    st.write("Gemini Available:", gemini.available)
    st.write("Model:", gemini.model)
    if st.button("Reset DB 🔄"):
        db.reset_db()
        st.success("✅ Database reset complete.")
    st.markdown("### Assets Configuration")
    st.write(ASSETS)

# ---------------------- Footer ----------------------
st.markdown(
    f"""
    <hr style="margin-top: 50px; border: 1px solid #e5e7eb;">
    <div style="text-align: center; color: #6b7280; font-size: 14px; padding: 10px;">
        {ASSETS.get('footer_text', '© 2025 EduGenie — Built with ❤️ using Gemini + Streamlit')}
        <br>
    
    """,
    unsafe_allow_html=True
)
