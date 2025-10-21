import streamlit as st
import json, os, time, jwt, requests
import boto3
import math
from utils import GeminiClient
from db import Database
import streamlit.components.v1 as components
from streamlit_webrtc import webrtc_streamer

from learning_path import LearningPath
from streamlit_drawable_canvas import st_canvas
import plotly.express as px
from reportlab.pdfgen import canvas as pdf_canvas
from datetime import datetime, timedelta

# Optional STT
try:
    import speech_recognition as sr
    HAS_STT = True
except Exception:
    HAS_STT = False
    
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
# Model selection is supported; you can switch between 'gemini' and 'gpt' in sidebar
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
gemini = GeminiClient(api_key=GEMINI_API_KEY)
db = Database('edugenie.db')  # sqlite wrapper (see db.py)
learning_path = LearningPath(db=db)
JWT_SECRET = st.secrets.get("JWT_SECRET", os.environ.get("JWT_SECRET", "supersecret123"))
admin_key = st.secrets.get("ADMIN_KEY", "supersecret")

# ---------------------- Sidebar ----------------------
st.sidebar.image(ASSETS.get('logo',''), width=120)
st.sidebar.title("EduGenie 🚀")
name = st.sidebar.text_input("Your Name", value="Guest")

# Model selector (Gemini / placeholder GPT switch)
model_choice = st.sidebar.selectbox("AI Model", ["Gemini", "Gemini (safe)", "Claude (AWS Bedrock)"])
st.sidebar.markdown("---")

# Toggle cloud sync
use_cloud = st.sidebar.checkbox("Use Cloud Sync (Firestore/Supabase)", value=False)

page = st.sidebar.radio(
    "Navigate to",
    [
        "Landing",
        "AI Tutor",
        "AI Learning Planner",
        "Upload & Summarize",
        "Quizzes",
        "Peer Rooms",
        "Live Room",
        "Progress & Leaderboard",
        "Admin Analytics",
        "Settings",
        "Admin Dashboard"
    ]
)
st.sidebar.markdown("---")
st.sidebar.info("Made with ❤️ for learners by EduGenie Team")

# ---------------------- Utilities ----------------------
@st.cache_data
def cached_chat(prompt, model="Gemini"):
    if "Claude" in model:
        return bedrock_claude_chat(prompt)
    else:
        return gemini.chat(prompt).get('text', '')


def create_certificate_pdf(username: str, course_name: str, out_path: str):
    c = pdf_canvas.Canvas(out_path)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, 700, "Certificate of Completion")
    c.setFont("Helvetica", 16)
    c.drawString(100, 650, f"This certifies that {username} has completed:")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, 620, f"{course_name}")
    c.drawString(100, 560, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
    c.save()
    return out_path

def stt_listen_once(timeout=5):
    if not HAS_STT:
        return None
    r = sr.Recognizer()
    with sr.Microphone() as source:
        audio = r.listen(source, timeout=timeout)
    try:
        text = r.recognize_google(audio)
        return text
    except Exception:
        return None

# AWS Bedrock (Claude 3 Sonnet)
bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"
)

def bedrock_claude_chat(prompt: str, model="anthropic.claude-3-sonnet-20240229"):
    body = {
        "modelId": model,
        "contentType": "application/json",
        "accept": "application/json",
        "body": json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}]
        })
    }
    try:
        response = bedrock_client.invoke_model(**body)
        output = json.loads(response["body"].read())
        return output["content"][0]["text"]
    except Exception as e:
        return f"[Error using Claude: {str(e)}]"
        
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
        
    # Daily challenge
    if st.button("Show Today's Challenge 🔥"):
        prompt = "Give one short STEM challenge suitable for a quick study session (one sentence)."
        challenge = cached_chat(prompt)
        st.info(f"🔥 Today's Challenge: {challenge}")

# ---------------------- AI Tutor ----------------------
elif page == "AI Tutor":
    st.header("AI Tutor 🤖")
    st.caption("Ask EduGenie anything! Type, speak, or draw a diagram for analysis.")

    # Contextual memory (previous chat)
    prev_ctx = db.cache_get(f"context:{name}") or ""

    # User input
    query = st.text_area("💬 Type your question here:", placeholder="E.g., Explain Nyquist sampling theorem in simple terms...")

    # Layout for chat + image/sketch
    col1, col2 = st.columns([3, 2])

    # ----------- Text / Voice Interaction -----------
    with col1:
        st.subheader("💬 Ask or Speak")

        # Type-based interaction
        if st.button("Ask EduGenie 🧠"):
            if not query.strip():
                st.warning("Please type a question first.")
            else:
                with st.spinner("Thinking deeply... 💭"):
                    prompt = prev_ctx + "\nUser: " + query
                    text = gemini.chat(prompt).get("text", "")
                    st.markdown("### 📘 EduGenie says:")
                    st.write(text)

                    # 🎧 Text-to-Speech
                    audio_file = gemini.tts(text)
                    if isinstance(audio_file, str) and os.path.exists(audio_file):
                        st.audio(audio_file)

                    # 💾 Cache response + update context memory
                    db.cache_set(f"chat:{query[:64]}", text, int(time.time()))
                    new_ctx = (prev_ctx + f"\nUser: {query}\nAI: {text}")[-4000:]
                    db.cache_set(f"context:{name}", new_ctx, int(time.time()))
                    st.balloons()

        # 🎙️ Speech Input (if available)
        st.markdown("Or try speaking your question 👇")

        if HAS_STT:
            if st.button("🎙️ Speak to EduGenie"):
                import tempfile
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    st.info("Listening... Speak now 🎧")
                    audio = recognizer.listen(source, phrase_time_limit=6)
                    st.success("Got it! Processing your speech...")
                    try:
                        said = recognizer.recognize_google(audio)
                        st.write(f"🗣️ You said: **{said}**")
                        response = gemini.chat(prev_ctx + "\nUser: " + said).get("text", "")
                        st.markdown("### 📘 EduGenie says:")
                        st.write(response)
                        audio_file = gemini.tts(response)
                        if isinstance(audio_file, str) and os.path.exists(audio_file):
                            st.audio(audio_file)
                    except sr.UnknownValueError:
                        st.error("Sorry, I couldn’t understand that. Please try again.")
        else:
            st.info("🎤 Speech recognition not installed. Run `pip install SpeechRecognition pyaudio` to enable it.")

    # ----------- Image / Sketch Analysis -----------
    with col2:
        st.subheader("📷 Image or Sketch Analysis")
        st.markdown("Draw or upload a concept diagram — EduGenie will explain it step by step!")

        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#ffffff",
            height=250,
            width=350,
            drawing_mode="freedraw",
            key="canvas_ai_tutor",
        )

        if canvas_result.image_data is not None and st.button("🖊️ Explain My Sketch"):
            st.image(canvas_result.image_data)
            with st.spinner("Interpreting your sketch... 🧩"):
                result = gemini.chat("Explain this hand-drawn concept diagram in simple, visual terms.").get("text", "")
                st.markdown("### 📘 EduGenie explains your sketch:")
                st.write(result)

        # Image Upload Option
        img = st.file_uploader("Or upload an image (png/jpg/jpeg)", type=['png', 'jpg', 'jpeg'])
        if img is not None and st.button("🔍 Analyze Uploaded Image"):
            with st.spinner("Analyzing your image... 🧠"):
                # Here we simulate visual understanding (if multimodal Gemini access available, replace this)
                result = gemini.chat("Analyze this image and describe it like a teacher would.").get("text", "")
                st.markdown("### 📘 EduGenie explains your image:")
                st.write(result)

# ---------------------- AI Learning Planner ----------------------
elif page == "AI Learning Planner":
    st.header("🎯 AI Learning Planner")
    st.caption("EduGenie analyzes your progress and creates a custom 3-day study plan using Gemini!")

    user_goals = st.text_area(
        "What do you want to achieve this week? ✍️",
        placeholder="e.g., Master Trigonometry and Fourier basics."
    )

    if st.button("✨ Generate My Learning Plan"):
        with st.spinner("Analyzing your quiz history and crafting a plan..."):
            history = db.get_recent_quiz_scores(name, limit=10)
            history_text = json.dumps(history)

            prompt = f"""
You are EduGenie, an AI tutor that creates personalized learning plans.
Analyze the student's quiz history and current goals to build a 3-day study plan.

Quiz History:
{history_text}

User Goal: {user_goals}

Provide a markdown-formatted output with:
- Day 1: Topics, short explanation, and 2 practice questions
- Day 2: Topics, example problem and mini quiz
- Day 3: Review, real-world application, and motivational quote
            """

            plan = cached_chat(prompt)
            st.markdown("### 📘 Your Personalized 3-Day Learning Plan")
            st.markdown(plan)
            db.cache_set(f"learning_plan:{name}", plan)
            st.balloons()
            
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
                    
                # cache summary offline
                db.cache_set(f"summary:{uploaded.name}", summ, int(time.time()))
                st.success("Summary cached for offline access!")
                st.balloons()
                
                # Download summary
                st.download_button("Download Summary (txt)", summ)

# ---------------------- Quizzes ----------------------
elif page == "Quizzes":
    st.header("🧩 Quick Quiz Generator")
    topic = st.text_input("Enter a topic:", value="Fourier Transform")
    diff = st.selectbox("Difficulty Level", ["Easy","Medium","Hard"])
    n = st.slider("Number of Questions", 1, 10, 5)
    
    # show badge preview
    badge_map = {"Easy": "badge_easy", "Medium": "badge_medium", "Hard": "badge_hard"}
    badge_img = ASSETS.get(badge_map.get(diff, "badge_easy"))
    if badge_img and os.path.exists(badge_img):
        st.image(badge_img, width=80)
    if st.button("Generate Quiz 🧠"):
        with st.spinner("Crafting smart questions..."):
            # adapt difficulty using learning_path
            adapted_diff = learning_path.adapt_difficulty(name, diff)
            quiz = gemini.generate_quiz(topic, difficulty=adapted_diff, n_questions=n)
            st.session_state['quiz'] = quiz
    if st.session_state.get('quiz'):
        quiz = st.session_state['quiz']
        score = 0
        
        # store start time to compute speed
        start_time = time.time()
        for idx, q in enumerate(quiz):
            st.markdown(f"**Q{idx+1}.** {q.get('q', 'No question')}")
            ans = st.text_input(f"Your Answer Q{idx+1}", key=f"q{idx}")
            if st.button(f"Submit Q{idx+1}", key=f"sub{idx}"):
                feedback = gemini.chat(f'Grade: Q: {q.get("q")} | User: {ans}. Give correct/incorrect + feedback.')
                st.write(feedback.get('text','Feedback not available'))
                if q.get('answer') and ans.strip().lower() == q.get('answer','').lower():
                    score += 1
        if st.button("Finish Quiz 🏁"):
            elapsed = time.time() - start_time
            xp = score * (1 if diff=='Easy' else 2 if diff=='Medium' else 3)
            
            # small bonus for speed
            if elapsed < max(30, n * 10):
                xp += 1
            db.add_xp(name, xp)
            
            # update learning path with results
            learning_path.record_quiz_result(user=name, topic=topic, score=score, total=len(quiz))
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
    st.header("📊 Your Progress Dashboard")

    col1, col2 = st.columns([2, 1])
    xp = db.get_xp(name)
    level = "Beginner" if xp < 100 else "Intermediate" if xp < 250 else "Expert"
    progress_pct = min(xp / 300, 1.0) * 100

    with col1:
        st.subheader(f"Welcome, {name} 👋")
        st.markdown(f"### 🌟 Level: **{level}**")
        st.progress(progress_pct / 100)
        st.metric("XP", f"{xp} pts")

        # XP Ring
        fig = px.pie(
            values=[xp, max(0, 300 - xp)],
            names=["XP", "Remaining"],
            hole=0.7,
            color_discrete_sequence=["#2563EB", "#E5E7EB"]
        )
        fig.update_traces(textinfo="none")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏅 Badges")
        if xp < 100:
            st.image(ASSETS.get("badge_easy", ""), width=80)
            st.caption("Beginner 🌱")
        elif xp < 250:
            st.image(ASSETS.get("badge_medium", ""), width=80)
            st.caption("Intermediate 🚀")
        else:
            st.image(ASSETS.get("badge_hard", ""), width=80)
            st.caption("Expert 🧠")

        if xp >= 200:
            st.success("🎉 Genie Mentor says: 'You’re ready to unlock Advanced Quizzes!'")
        else:
            st.info("💡 Keep going! Earn 50 more XP to unlock new topics!")

    st.markdown("### 🏁 Leaderboard")
    lb = db.get_leaderboard(limit=10)
    st.table(lb)
    
    # Certificate generation example
    if st.button("Generate Completion Certificate (Sample)"):
        pdf_path = f"certificate_{name.replace(' ','_')}.pdf"
        create_certificate_pdf(name, "EduGenie Quick Course", pdf_path)
        with open(pdf_path, "rb") as fh:
            st.download_button(label="Download Certificate", data=fh, file_name=pdf_path, mime="application/pdf")
            
# ---------------------- Admin Analytics ----------------------
elif page == "Admin Analytics":
    st.header("📊 Admin Analytics")
    st.caption("Visualize engagement and learning metrics.")
    # require a simple admin key (in secrets)
    if st.sidebar.text_input("Admin Key", type="password") != st.secrets.get("ADMIN_KEY",""):
        st.warning("Enter admin key to view analytics.")
    else:
        df = db.get_activity_dataframe()  # returns pandas DataFrame
        if df is None or df.empty:
            st.info("No activity data yet.")
        else:
            fig = px.bar(df, x="topic", y="score", color="user", barmode="group")
            st.plotly_chart(fig, use_container_width=True)
            
# ---------------------- Settings ----------------------
elif page == "Settings":
    st.header("⚙️ Settings / Debug")
    st.write("Gemini Available:", gemini.available)
    st.write("Model:", gemini.model)
    if st.button("Reset DB 🔄"):
        db.reset_db()
        st.success("✅ Database reset complete.")
    
# ---------------------- Admin Dashboard ----------------------
elif page == "Admin Dashboard":
    st.header("🧑‍💼 EduGenie Admin Dashboard")
    st.caption("Restricted access — for authorized administrators only.")

    entered_key = st.text_input("🔑 Enter Admin Key:", type="password")
    if entered_key == admin_key:
        st.success("✅ Admin access granted!")

        tab1, tab2, tab3 = st.tabs(["📊 Analytics", "🧱 Database", "👥 Users"])

        with tab1:
            st.subheader("Engagement Analytics 📈")
            data = db.get_leaderboard(limit=50)
            if data:
                import pandas as pd
                df = pd.DataFrame(data)
                st.bar_chart(df.set_index("name")["xp"])
                st.write(df)
            else:
                st.info("No data available yet.")

            st.markdown("### Time Spent by Users")
            st.progress(0.7, text="Average activity level (mock data)")

        with tab2:
            st.subheader("Database Tools 🧰")
            if st.button("🗑️ Reset Entire Database"):
                db.reset_db()
                st.warning("⚠️ Database has been reset!")
            st.download_button(
                "⬇️ Export Leaderboard CSV",
                data="\n".join([",".join(map(str, row)) for row in data]) if data else "",
                file_name="leaderboard.csv",
                mime="text/csv"
            )

        with tab3:
            st.subheader("User Management 👥")
            users = db.get_all_users() if hasattr(db, "get_all_users") else []
            if users:
                st.table(users)
            else:
                st.info("No registered users found.")
            
            new_xp_user = st.text_input("User Name to Update XP")
            new_xp_value = st.number_input("New XP Value", min_value=0)
            new_profile_data = st.text_area("Profile JSON (optional)")
            
            if st.button("💾 Update User"):
                if new_xp_user:
                    db.ensure_user(new_xp_user)  # create if doesn't exist
                    db.update_xp(new_xp_user, new_xp_value)
                    if new_profile_data:
                        try:
                            import json
                            profile_dict = json.loads(new_profile_data)
                            db.update_profile(new_xp_user, profile_dict)
                        except json.JSONDecodeError:
                            st.error("Invalid JSON for profile")
                    st.success(f"Updated XP and profile for {new_xp_user}")

    else:
        st.warning("🔒 Access denied — invalid admin key.")

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
