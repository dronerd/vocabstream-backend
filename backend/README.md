📘 VocabStream Backend (FastAPI)

This is the backend API for the VocabStream application.
It provides English conversation features powered by OpenAI, with adjustable language levels and specialties.
Built using FastAPI, designed for future integration with machine learning models in Python.

🚀 Features

🌍 REST API built with FastAPI

🧠 AI chat powered by OpenAI API

⚙️ Adjustable English level and specialty

🔐 Secure environment variable management

☁️ Deployable on Render with one file (render.yaml)

🔄 Supports auto-deployment from GitHub pushes

🧩 Ready for ML model integration (PyTorch, Transformers, etc.)

🧱 Project Structure
backend/
 ├─ main.py               # FastAPI entry point
 ├─ requirements.txt      # Python dependencies
 ├─ .env                  # Environment variables (not committed)
 ├─ .gitignore            # Git ignore rules
 ├─ render.yaml           # Render deployment blueprint
 └─ README.md             # Documentation (this file)

⚙️ Setup (Local Development)
1. Clone the repository
git clone https://github.com/<yourusername>/vocabstream-backend.git
cd vocabstream-backend

2. Create a virtual environment
python -m venv venv
source venv/bin/activate       # macOS/Linux
venv\Scripts\activate          # Windows

3. Install dependencies
pip install -r requirements.txt

4. Create a .env file

Create a file named .env in the project root:

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxx


⚠️ Never commit your .env file to GitHub — it’s private.

5. Run the FastAPI app
uvicorn main:app --reload


✅ Open http://127.0.0.1:8000
 to confirm it’s running.
✅ You can test the chat endpoint using http://127.0.0.1:8000/docs
.

🧠 Example API Call

Endpoint:

POST /api/chat


Body (JSON):

{
  "message": "Hello!",
  "level": "B2",
  "specialty": "Computer Science"
}


Response:

{
  "reply": "Hi there! How are you today?"
}

☁️ Deployment (Render)
1. Push to GitHub

Commit your code and push it:

git add .
git commit -m "Initial backend setup"
git push origin main

2. Create a Render Blueprint

Render uses render.yaml to auto-configure everything.
Here’s what it does:

services:
  - type: web
    name: vocabstream-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    autoDeploy: true
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
      - key: OPENAI_API_KEY
        sync: false

3. Deploy

Go to Render.com

Click “New +” → “Blueprint”

Connect your GitHub repo

Render auto-detects render.yaml

Add your OPENAI_API_KEY in Environment Variables

Click Deploy Blueprint

https://vocabstream-backend.onrender.com

🔗 Connecting to Frontend

In your React app, update your fetch URL:

const res = await fetch("https://vocabstream-backend.onrender.com/api/chat", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    message: userInput,
    level,
    specialty,
  }),
});

🧩 Future Enhancements

Add user authentication (JWT / OAuth)

Integrate custom ML models (e.g. BERT, T5, Whisper)

Store chat history in a database (PostgreSQL, MongoDB)

Implement speech input/output endpoints

Add rate limiting for public API safety

