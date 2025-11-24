# main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv
from typing import Optional, List
import io

load_dotenv()
app = FastAPI()

# Allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        #ここで/を最後に付けてはいけない。
        "https://vocabstream.vercel.app",  # production frontend
        "http://localhost:3000",           # local frontend (Vite dev)
        "https://vocabstream-for-testing.vercel.app"            # test frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# New request models for casual and lesson modes
class ComponentTiming(BaseModel):
    component: str
    startSeconds: int
    endSeconds: int
    durationSeconds: int

class CasualChatRequest(BaseModel):
    message: str
    level: str
    topics: List[str]
    mode: str = "casual"

class LessonChatRequest(BaseModel):
    message: str
    level: str
    topics: List[str]
    tests: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    duration: Optional[int] = None
    durationMinutes: Optional[int] = None
    currentComponent: Optional[int] = None
    currentComponentName: Optional[str] = None
    components: Optional[List[str]] = None
    componentTiming: Optional[List[ComponentTiming]] = None
    totalTimeElapsed: Optional[int] = None
    timeElapsedSeconds: Optional[int] = None
    vocabCategory: Optional[str] = None
    vocabLessons: Optional[List[str]] = None
    mode: str = "lesson"

def build_casual_system_prompt(level: str, topics: List[str]) -> str:
    """Build system prompt for casual conversation mode"""
    topics_str = ", ".join(topics)
    return f"""You are a friendly and engaging English conversation partner. 

Your role:
- Have natural, enjoyable conversations in English
- Help the user practice English at level {level} (CEFR scale)
- Focus on topics: {topics_str}
- Ask follow-up questions to keep the conversation flowing
- Gently correct grammar mistakes naturally within conversation
- Use vocabulary and structures appropriate for level {level}
- Encourage the user to share more and express themselves

Conversation style:
- Warm and encouraging
- Natural and colloquial
- Ask open-ended questions
- Show genuine interest in the user's thoughts and experiences
- Adapt complexity based on their level

Remember to keep conversations dynamic and interesting!"""

def build_lesson_system_prompt(
    level: str, 
    topics: List[str], 
    tests: List[str],
    skills: List[str],
    current_component: str,
    component_timing: dict,
    vocab_category: Optional[str] = None
) -> str:
    """Build system prompt for lesson mode with time awareness"""
    topics_str = ", ".join(topics)
    tests_str = ", ".join(tests) if tests else "General English"
    skills_str = ", ".join(skills) if skills else "All skills"
    
    # Calculate remaining time in current component
    remaining_time = ""
    if component_timing:
        remaining_seconds = component_timing.get('durationSeconds', 300)
        remaining_minutes = remaining_seconds / 60
        remaining_time = f"⏱️ You have approximately {remaining_minutes:.0f} minutes for this section."
    
    # Determine component-specific guidance
    component_guidance = ""
    if current_component == "Vocab Practice":
        component_guidance = f"""Focus on vocabulary practice{f' from {vocab_category}' if vocab_category else ''}. 
- Present new vocabulary in context
- Include example sentences
- Ask the user to use the words in sentences
- Provide pronunciation guidance"""
    elif current_component == "Reading Comprehension":
        component_guidance = """Focus on reading comprehension:
- Provide a short reading passage (appropriate for the remaining time)
- Ask comprehension questions
- Explain difficult vocabulary
- Encourage the user to summarize the passage"""
    elif current_component == "Speaking Practice":
        component_guidance = """Focus on speaking practice:
- Generate conversation prompts or discussion topics
- Ask detailed questions that require extended responses
- Provide feedback on pronunciation and fluency
- Encourage more natural, longer answers"""
    elif current_component == "Pronunciation Practice":
        component_guidance = """Focus on pronunciation:
- Provide words and phrases to practice
- Explain pronunciation rules
- Ask the user to practice and provide feedback
- Use phonetic explanations"""
    elif current_component == "Grammar":
        component_guidance = """Focus on grammar practice:
- Explain grammar rules clearly
- Provide examples and exercises
- Ask the user to create sentences using the grammar point
- Correct errors constructively"""
    else:
        component_guidance = f"""Focus on {current_component}:
- Tailor activities to this specific component
- Maintain engagement and clarity
- Adapt difficulty to level {level}"""
    
    return f"""You are a professional English tutor preparing the student for {tests_str} exams.

STUDENT PROFILE:
- English Level: {level} (CEFR scale)
- Target Skills: {skills_str}
- Topics of Interest: {topics_str}
- Exam Focus: {tests_str}

CURRENT LESSON COMPONENT: {current_component}
{remaining_time}

COMPONENT-SPECIFIC GUIDANCE:
{component_guidance}

LESSON DELIVERY PRINCIPLES:
1. Adapt all content to level {level}:
   - A1-A2: Simple sentences, frequent repetition, basic vocabulary
   - B1-B2: More complex structures, varied vocabulary, nuanced explanations
   - C1-C2: Advanced concepts, sophisticated vocabulary, subtle nuances

2. Time-Aware Teaching:
   - Respect the time allocation for this component
   - Provide value even if time is limited
   - Prepare to wrap up gracefully when component time ends
   - Make efficient use of remaining time

3. Skills Integration:
   - Prioritize the selected skills: {skills_str}
   - For Reading: provide appropriate length materials
   - For Listening: use natural speech patterns
   - For Writing: focus on structure and accuracy
   - For Speaking: encourage extended responses

4. Engagement:
   - Ask follow-up questions to deepen learning
   - Provide constructive feedback
   - Maintain motivation and enthusiasm
   - Celebrate progress

5. Context Awareness:
   - Keep track of student responses
   - Build on previous points in the lesson
   - Make connections to exam requirements if relevant
   - Adapt explanations based on student understanding

RESPONSE FORMAT:
- Keep responses focused and purposeful
- Structure complex content clearly
- Use formatting (bold, bullet points) when helpful
- Provide explanations before asking questions when teaching new content"""

def get_component_info(component_timing: List[dict], current_component_idx: int) -> Optional[dict]:
    """Extract timing info for current component"""
    if current_component_idx < len(component_timing):
        return component_timing[current_component_idx]
    return None

@app.post("/api/chat")
async def chat(req: dict):
    """Handle both casual chat and lesson modes"""
    try:
        # Determine mode and validate request
        mode = req.get("mode", "casual")
        
        if mode == "casual":
            return await handle_casual_chat(req)
        elif mode == "lesson":
            return await handle_lesson_chat(req)
        else:
            return {"error": "Unknown mode. Use 'casual' or 'lesson'."}
            
    except Exception as e:
        return {"error": str(e), "details": repr(e)}

async def handle_casual_chat(req: dict):
    """Handle casual conversation mode"""
    try:
        message = req.get("message", "")
        level = req.get("level", "A1")
        topics = req.get("topics", ["General"])
        
        system_prompt = build_casual_system_prompt(level, topics)
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        
        reply = completion.choices[0].message.content
        return {"reply": reply, "mode": "casual"}
        
    except Exception as e:
        return {"error": str(e), "mode": "casual"}

async def handle_lesson_chat(req: dict):
    """Handle lesson mode with timing awareness"""
    try:
        message = req.get("message", "")
        level = req.get("level", "A1")
        topics = req.get("topics", ["General"])
        tests = req.get("tests", [])
        skills = req.get("skills", ["Reading", "Listening", "Writing", "Speaking"])
        current_component = req.get("currentComponentName", "General")
        component_timing_list = req.get("componentTiming", [])
        current_component_idx = req.get("currentComponent", 0)
        time_elapsed = req.get("timeElapsedSeconds", 0)
        vocab_category = req.get("vocabCategory")
        
        # Get timing info for current component
        current_timing = get_component_info(component_timing_list, current_component_idx)
        
        system_prompt = build_lesson_system_prompt(
            level=level,
            topics=topics,
            tests=tests,
            skills=skills,
            current_component=current_component,
            component_timing=current_timing if current_timing else {},
            vocab_category=vocab_category
        )
        
        # Determine max tokens based on remaining time (rough estimate)
        # Assume ~100 tokens per minute
        time_remaining = current_timing.get('durationSeconds', 300) if current_timing else 300
        max_tokens = min(int((time_remaining / 60) * 100), 500)
        max_tokens = max(max_tokens, 150)  # Minimum 150 tokens
        
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        
        reply = completion.choices[0].message.content
        return {
            "reply": reply,
            "mode": "lesson",
            "currentComponent": current_component,
            "timeRemaining": time_remaining if current_timing else None
        }
        
    except Exception as e:
        return {"error": str(e), "mode": "lesson"}

@app.get("/")
def root():
    return {"status": "ok", "version": "2.0", "modes": ["casual", "lesson"]}


@app.post("/api/voice")
async def voice(req: dict):
    """Generate speech audio for given text.

    Expects JSON: { "text": "...", "voice": "alloy" }

    Tries to use the configured OpenAI client to synthesize TTS. Returns audio binary (audio/mpeg).
    If OpenAI TTS API is unavailable or an error occurs, returns a JSON error response.
    """
    try:
        text = req.get("text", "")
        voice = req.get("voice", "alloy")
        if not text:
            return JSONResponse({"error": "No text provided"}, status_code=400)

        # Attempt to call OpenAI TTS (SDK may expose audio generation differently depending on version).
        # This code attempts a best-effort call using the OpenAI Python client wrapper used elsewhere.
        try:
            # Many OpenAI SDKs provide an `audio.speech.create` or similar method for TTS.
            # We call it and attempt to extract raw bytes from the response.
            resp = client.audio.speech.create(model="gpt-4o-mini-tts", voice=voice, input=text)

            # resp may be a bytes-like object, or have attributes/stream. Try common access patterns.
            audio_bytes = None
            if isinstance(resp, (bytes, bytearray)):
                audio_bytes = bytes(resp)
            else:
                # Try common attributes
                for attr in ("audio", "data", "content", "raw", "raw_audio"):
                    if hasattr(resp, attr):
                        candidate = getattr(resp, attr)
                        if isinstance(candidate, (bytes, bytearray)):
                            audio_bytes = bytes(candidate)
                            break
                        # file-like
                        if hasattr(candidate, "read"):
                            audio_bytes = candidate.read()
                            break

            if audio_bytes is None:
                # As a last resort, try to stringify the response (not ideal)
                return JSONResponse({"error": "Could not extract audio bytes from OpenAI response", "raw": str(resp)}, status_code=500)

            return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")

        except Exception as inner_e:
            # If OpenAI TTS is not configured or call fails, return error
            return JSONResponse({"error": "OpenAI TTS error", "details": str(inner_e)}, status_code=500)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)