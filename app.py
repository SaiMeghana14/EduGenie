import streamlit as st
import json, os, time, jwt, requests
from utils import GeminiClient
from db import DB
from streamlit_lottie import st_lottie
import streamlit.components.v1 as components
from streamlit_webrtc import webrtc_streamer

# ---------------------- Config ----------------------
st.set_page_config(page_title='EduGenie (Gemini)', layout='wide', initial_sidebar_state='expanded')
st.markdown("<style> .stApp { background: #F8FAFC; } </style>", unsafe_allow_html=True)

# Load assets
ASSETS = {}
try:
    with open('assets/config.json', 'r') as f:
        ASSETS = json.load(f)
except Exception:
    ASSETS = {}

def load_lottie_file(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return None

# ---------------------- Clients ----------------------
gemini = GeminiClient(api_key=os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
db = DB('edugenie.db')
JWT_SECRET = st.secrets["JWT_SECRET"]

# ---------------------- Sidebar ----------------------
st.sidebar.image(ASSETS.get('logo_url',''), width=120)
st.sidebar.title("EduGenie")
name = st.sidebar.text_input("Your Name", value="Guest")
page = st.sidebar.radio("Navigate to", ["Landing", "AI Tutor", "Upload & Summarize", "Quizzes", "Peer Rooms", "Live Room", "Progress & Leaderboard", "Settings"])

# ---------------------- Landing Page ----------------------
if page == "Landing":
    col1, col2 = st.columns([2,3])
    with col1:
        st.title("EduGenie — Gemini-Powered Learning 🚀")
        st.write("Personalized, multimodal, gamified learning demo — no AWS required.")
        st.markdown("- Gemini AI Tutor (text + voice)")
        st.markdown("- Upload notes/PDFs → Summaries & Flashcards")
        st.markdown("- Quizzes, XP & Leaderboard")
        st.button("Get Started")
    with col2:
        lottie = load_lottie_file('assets/your_animation.json')
        if lottie:
            st_lottie(lottie, height=320)
        else:
            st.image(ASSETS.get("logo_url", ""), width=200)

        st.markdown("### Features")
        st.write("Gemini multimodal tutor, offline caching, collaborative peer rooms, WebRTC live sessions.")

# ---------------------- AI Tutor ----------------------
elif page == "AI Tutor":
    st.header("AI Tutor")
    st.write("Chat with EduGenie. Use text or upload images/diagrams.")
    query = st.text_area("Ask a question:", value="Explain Nyquist sampling theorem in simple terms.")

    def get_cached_response(prompt):
        resp = gemini.chat(prompt)
        return resp.get("text") or resp.get("mock") or resp.get("error") or ""

    col1, col2 = st.columns([3,1])
    with col1:
        if st.button("Ask Gemini"):
            with st.spinner("Thinking..."):
                text = get_cached_response(query)
                st.markdown("**EduGenie:**")
                st.write(text)
                
                # TTS via GeminiClient
                audio_file = gemini.tts(text)
                st.audio(audio_file)
                
                # Cache in local DB
                db.cache_set(f"chat:{query[:64]}", text, int(time.time()))

    with col2:
        st.subheader("Upload diagram / image")
        img = st.file_uploader("Image (png/jpg/jpeg)", type=['png','jpg','jpeg'])
        if img is not None and st.button("Analyze Image"):
            with st.spinner("Analyzing..."):
                prompt = "Analyze this image and explain what it likely shows, step-by-step."
                result = gemini.chat(prompt + " (image attached).")
                st.write(result.get('text', 'No response.'))

# ---------------------- Upload & Summarize ----------------------
elif page == "Upload & Summarize":
    st.header("Upload Notes / PDF")
    uploaded = st.file_uploader("Upload PDF or TXT", type=['pdf','txt'])
    if uploaded:
        raw = ""
        if uploaded.type == "application/pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(uploaded)
            for p in reader.pages: raw += p.extract_text() + "\n"
        else:
            raw = uploaded.getvalue().decode('utf-8')
        st.write(raw[:800])
        if st.button("Summarize & Generate Flashcards"):
            with st.spinner("Generating..."):
                summ = gemini.summarize(raw)
                flashcards = gemini.generate_quiz(raw[:120], difficulty='Medium', n_questions=6)
                st.subheader("Summary")
                st.write(summ)
                st.subheader("Flashcards")
                for i,fc in enumerate(flashcards if isinstance(flashcards, list) else []):
                    q = fc.get('q') if isinstance(fc, dict) else fc[0]
                    a = fc.get('a') if isinstance(fc, dict) else fc[1]
                    st.markdown(f"**Q{i+1}.** {q}")
                    st.write(f"**A.** {a}")

# ---------------------- Quizzes ----------------------
elif page == "Quizzes":
    st.header("Generate Quiz")
    topic = st.text_input("Topic:", value="Fourier Transform")
    diff = st.selectbox("Difficulty", ["Easy","Medium","Hard"])
    n = st.slider("Number of Questions", 1, 10, 5)
    if st.button("Generate Quiz"):
        with st.spinner("Generating..."):
            quiz = gemini.generate_quiz(topic, difficulty=diff, n_questions=n)
            st.session_state['quiz'] = quiz
    if st.session_state.get('quiz'):
        quiz = st.session_state['quiz']
        score = 0
        for idx,q in enumerate(quiz):
            st.markdown(f"**Q{idx+1}.** {q.get('q') if isinstance(q, dict) else q['q']}")
            ans = st.text_input(f"Answer Q{idx+1}", key=f"q{idx}")
            if st.button(f"Submit Q{idx+1}", key=f"sub{idx}"):
                feedback = gemini.chat(f'Grade this answer: Q: {q.get("q")} A_user: {ans}. Respond correct/incorrect and give feedback.')
                st.write(feedback.get('text','Feedback not available'))
                if q.get('answer') and ans.strip().lower() == q.get('answer','').lower():
                    score += 1
        if st.button("Finish Quiz"):
            xp = score * (1 if diff=='Easy' else 2 if diff=='Medium' else 3)
            db.add_xp(name, xp)
            st.success(f"Score: {score}/{len(quiz)}, XP earned: {xp}")

# ---------------------- Peer Rooms ----------------------
elif page == "Peer Rooms":
    st.header("Peer Rooms — collaborative notes & whiteboard")
    st.write("Collaborative notes & whiteboard with Firebase Realtime DB and JWT-secured access.")
    room = st.text_input("Room name:", value="demo-room")
    if room:
        payload = {"room": room, "user": name, "iat": int(time.time()), "exp": int(time.time()) + 3600}
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        if isinstance(token, bytes):
            token = token.decode("utf-8")
    if st.button("Open Peer Room"):
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
    st.header("Live Video Room 🎥")
    from streamlit_webrtc import webrtc_streamer
    webrtc_streamer(key="edu_webrtc")

# ---------------------- Progress & Leaderboard ----------------------
elif page == "Progress & Leaderboard":
    st.header("Progress & Leaderboard")
    xp = db.get_xp(name)
    st.metric("XP", xp)
    st.progress(min(xp/200,1.0))
    st.subheader("Leaderboard")
    lb = db.get_leaderboard(limit=10)
    st.table(lb)

# ---------------------- Settings ----------------------
elif page == "Settings":
    st.header("Settings / Debug")
    st.write("Gemini available:", gemini.available)
    st.write("Model:", gemini.model)
    if st.button("Reset DB (demo)"):
        db.reset_db()
        st.success("DB reset done.")
    st.markdown("Assets Config")
    st.write(ASSETS)
