# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

# Allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://vocabstream.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatRequest(BaseModel):
    message: str
    level: str
    specialty: str

@app.post("/api/chat")
async def chat(req: ChatRequest):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are an English conversation partner focusing on {req.specialty} at level {req.level}."},
                {"role": "user", "content": req.message},
            ],
        )
        reply = completion.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def root():
    return {"status": "ok"}
