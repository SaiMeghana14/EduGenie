# 🌟 EduGenie — Personalized AI Learning Companion

**Empower students to learn smarter, not harder.**  
EduGenie combines **Google Gemini AI**, **interactive quizzes**, **real-time collaboration**, and **live video rooms** — all inside a single Streamlit app.  

[Hero](assets/hero.gif)

---

## 🚀 Overview

EduGenie is a next-gen learning platform that makes studying **engaging, multimodal, and personalized**.  
Built for hackathons and education innovators, it merges **AI tutoring**, **PDF summarization**, **gamified learning**, and **real-time peer collaboration**.

---

## ✨ Key Features

| Feature | Description |
|----------|-------------|
| 🤖 **AI Tutor (Gemini-Powered)** | Ask natural-language questions, get instant AI explanations, and listen to TTS voice answers. |
| 📄 **Upload & Summarize Notes** | Upload PDFs or text files — auto-summarized and converted into flashcards and quizzes. |
| 🧠 **Auto-Generated Quizzes** | Dynamic quizzes with instant feedback, XP points, and leaderboard ranking. |
| 🎥 **Live Rooms (WebRTC)** | Host real-time study sessions with camera/mic via `streamlit-webrtc`. |
| 👩‍🏫 **Peer Rooms (Firebase + JWT)** | Secure collaborative whiteboard & notes synced live using Firebase Realtime DB. |
| 🧩 **Offline Caching** | Frequently asked questions cached locally for instant re-responses. |
| 🏆 **Progress & Leaderboard** | Earn XP, track progress, and see your rank among peers. |
| ⚙️ **Settings / Debug Mode** | Manage secrets, reset DB, and view model info easily. |

---

## 🧰 Tech Stack

| Category | Tools Used |
|-----------|------------|
| **Frontend** | Streamlit, HTML/CSS, Custom Components |
| **AI Backend** | Google Gemini API (via `google-genai`) |
| **Speech** | Google Text-to-Speech (`gTTS`) |
| **Database** | SQLite (local XP + caching) |
| **Collaboration** | Firebase Realtime Database |
| **Video/Audio** | Streamlit WebRTC |
| **Security** | JWT Authentication |
| **Deployment** | Streamlit Cloud / Hugging Face Spaces |

---

## 📦 Installation & Setup

### 1️⃣ Clone the repository
```bash
git clone https://github.com/<yourusername>/edugenie.git
cd edugenie
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 3️⃣ Add your environment variables  
Create a `.streamlit/secrets.toml` file (or use Streamlit Cloud’s Secrets Manager):

```toml
GEMINI_API_KEY = "your_gemini_api_key"
FIREBASE_API_KEY = "your_firebase_api_key"
FIREBASE_AUTH_DOMAIN = "your_project.firebaseapp.com"
FIREBASE_DB_URL = "https://your_project.firebaseio.com"
FIREBASE_PROJECT_ID = "your_project_id"
FIREBASE_STORAGE_BUCKET = "your_project.appspot.com"
FIREBASE_MESSAGING_SENDER_ID = "your_sender_id"
FIREBASE_APP_ID = "your_app_id"
JWT_SECRET = "your_random_strong_secret"
```

Generate a strong secret key (for JWT):
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 4️⃣ Run the app
```bash
streamlit run app.py
```

Open your browser at 👉 `http://localhost:8501`

---

## 🗂️ Project Structure
```
edugenie/
│
├── app.py                    # Main Streamlit app
├── db.py                     # Local SQLite database (XP, cache)
├── utils.py                  # Gemini + TTS helper class
├── peer_room.html            # Collaborative Firebase room template
├── learning_path.py
├── api_server.py
├── assets/
│   ├── logo.png
│   ├── hero.gif
│   ├── upload.gif
│   ├── badge_easy.gif
│   ├── badge_medium.gif
│   ├── badge_hard.gif
│   └── config.json
├──  firebase_utils.py
├── .github/workflows/main.yml
├── Dockerfile
├── quizzes.py
├── token_server.py
├── requirements.txt
└── README.md
```

---

## 🧑‍💻 Usage Flow

1. **Start on the Landing Page** → Learn features, click *Start Learning!*  
2. **AI Tutor** → Ask any topic question, get AI + TTS explanation.  
3. **Upload Notes** → Auto-summarize and generate flashcards.  
4. **Take Quizzes** → Earn XP and badges for correct answers.  
5. **Join Peer Rooms** → Collaborate securely using JWT tokens.  
6. **Go Live!** → Host or join WebRTC study rooms.  
7. **Track Progress** → Check leaderboard and XP growth.  

---

## 🧠 Educational Impact

EduGenie helps students:
- Learn through **conversational AI**.
- Retain better with **gamified quizzes**.
- Collaborate via **real-time rooms**.
- Access study materials **offline**.

---

## 🏁 Roadmap

- [ ] Add speech-to-text for voice input  
- [ ] Integrate adaptive difficulty engine  
- [ ] Add community leaderboard sync  
- [ ] Export notes to PDF/Drive  

---

## 👥 Team

**Project:** *EduGenie – Personalized AI Tutor*  
**Developer:** K.N.V.Sai Meghana   
**Tech Stack:** Python · Streamlit · Google Gemini · Firebase · WebRTC  
**GitHub:** [@SaiMeghana14](https://github.com/SaiMeghana14)

---

## 💖 Acknowledgments
- Google Gemini AI for enabling multimodal learning.  
- Streamlit for its simplicity and UI magic.  
- Firebase Realtime Database for collaboration.  
- `streamlit-webrtc` for seamless live rooms.
