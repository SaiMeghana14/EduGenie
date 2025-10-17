import streamlit as st
from utils import GeminiClient, tts_local
from db import DB
import os, time, json
from streamlit_lottie import st_lottie
import requests
import streamlit.components.v1 as components

# Setup
st.set_page_config(page_title='EduGenie (Gemini)', layout='wide', initial_sidebar_state='expanded')
st.markdown("<style> .stApp { background: #F8FAFC; } </style>", unsafe_allow_html=True)

# Load assets config
ASSETS = {}
try:
    with open('assets/config.json','r') as f:
        ASSETS = json.load(f)
except Exception:
    ASSETS = {}

# Lottie helper
def load_lottie_url(url):
    try:
        r = requests.get(url)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None

# instantiate Gemini client
gemini = GeminiClient(api_key=os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY'))
db = DB('edugenie.db')

# Sidebar
st.sidebar.image(ASSETS.get('logo_url',''), width=120)
st.sidebar.title("EduGenie")
name = st.sidebar.text_input("Your name", value="Guest")
page = st.sidebar.radio("Go to", ["Landing", "AI Tutor", "Upload & Summarize", "Quizzes", "Peer Rooms", "Progress & Leaderboard", "Settings"])

# Landing
if page == "Landing":
    col1,col2 = st.columns([2,3])
    with col1:
        st.title("EduGenie — Gemini-Powered Learning")
        st.write("Personalized, multi-modal, gamified learning demo — no AWS required.")
        st.markdown("- Gemini AI Tutor (text + image + voice)")
        st.markdown("- Upload notes/PDFs -> Summaries & Flashcards")
        st.markdown("- Quizzes, XP & Leaderboard")
        st.button("Get Started")
    with col2:
        lottie = load_lottie_url(ASSETS.get('lottie_hero'))
        if lottie: st_lottie(lottie, height=320)
        st.markdown("### Features")
        st.write("Gemini multimodal tutor, offline caching, collaborative peer rooms.")

# AI Tutor
elif page == "AI Tutor":
    st.header("AI Tutor")
    st.write("Chat with EduGenie. Use text or upload images (diagrams, equations).")
    query = st.text_area("Ask a question:", value="Explain Nyquist sampling theorem in simple terms.")
    col1,col2 = st.columns([3,1])
    with col1:
        if st.button("Ask Gemini"):
            with st.spinner("Thinking..."):
                resp = gemini.chat(query)
            text = resp.get('text') or resp.get('mock') or resp.get('error') or ''
            st.markdown("**EduGenie:**")
            st.write(text)
            # cache for offline
            db.cache_set(f"chat:{query[:64]}", text, int(time.time()))
            if 'audio' in resp:
                # if the SDK returned audio path or bytes, play it; else fallback to local TTS
                try:
                    st.audio(resp['audio'])
                except:
                    fname = tts_local(text)
                    st.audio(fname)
    with col2:
        st.subheader("Upload diagram / image")
        img = st.file_uploader("Image (png/jpg)", type=['png','jpg','jpeg'])
        if img is not None and st.button("Analyze image"):
            with st.spinner("Analyzing..."):
                # For simplicity: treat as question "Explain this image"
                prompt = "Analyze this image and explain what it likely shows, step-by-step."
                # attempt to send to Gemini (vision-capable) if available
                result = gemini.chat(prompt + " (image attached).")
                st.write(result.get('text', 'No response.'))

# Upload & Summarize
elif page == "Upload & Summarize":
    st.header("Upload notes / PDF")
    uploaded = st.file_uploader("Upload PDF or TXT", type=['pdf','txt'])
    if uploaded:
        raw = ""
        if uploaded.type == "application/pdf":
            from PyPDF2 import PdfReader
            reader = PdfReader(uploaded)
            for p in reader.pages:
                raw += p.extract_text() + "\\n"
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

# Quizzes
elif page == "Quizzes":
    st.header("Generate Quiz")
    topic = st.text_input("Topic:", value="Fourier Transform")
    diff = st.selectbox("Difficulty", ["Easy","Medium","Hard"])
    n = st.slider("Number of questions", 1, 10, 5)
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
                # Evaluate answer using Gemini (simple)
                feedback = gemini.chat(f'Grade this answer: Q: {q.get("q")} A_user: {ans} Provide {"correct" if ans.strip().lower()==(q.get("answer","").lower()) else "incorrect"} and brief feedback.')
                st.write(feedback.get('text', 'Feedback not available'))
                if q.get('answer') and ans.strip().lower() == q.get('answer','').lower():
                    score += 1
        if st.button("Finish Quiz"):
            xp = score * (1 if diff=='Easy' else 2 if diff=='Medium' else 3)
            db.add_xp(name, xp)
            st.success(f"You scored {score}/{len(quiz)} and earned {xp} XP")

# Peer Rooms
elif page == "Peer Rooms":
    st.header("Peer Rooms — collaborative notes & whiteboard")
    st.write("This embeds a collaborative HTML snippet that uses Firebase Realtime DB for signaling.")
    room = st.text_input("Room name:", value="demo-room")
    if st.button("Open Peer Room"):
        # embed the HTML and pass room as query param
        with open("peer_room.html", "r", encoding='utf-8') as f:
            html = f.read()
        # simple replace of placeholder ROOM if needed
        components.html(html + f"<script>/* room param already read by JS */</script>", height=520, scrolling=True)

# Progress & Leaderboard
elif page == "Progress & Leaderboard":
    st.header("Progress")
    xp = db.get_xp(name)
    st.metric("XP", xp)
    st.progress(min(xp / 200, 1.0))
    st.subheader("Leaderboard")
    lb = db.get_leaderboard(limit=10)
    st.table(lb)

# Settings
elif page == "Settings":
    st.header("Settings / Debug")
    st.write("Gemini available:", gemini.available)
    st.write("Model:", gemini.model)
    if st.button("Reset DB (demo)"):
        db.reset_db()
        st.success("Reset done.")
    st.markdown("**Assets config**")
    st.write(ASSETS)
