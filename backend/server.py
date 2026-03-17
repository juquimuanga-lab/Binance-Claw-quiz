from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import secrets
import httpx
import re
from pathlib import Path
from pydantic import BaseModel
from typing import Dict
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import google.generativeai as genai

# ================= INIT =================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ.get('DB_NAME', 'moltbot_app')]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= SAFE ARTICLE STORE =================

ARTICLES = [
    {"title": "What Is Bitcoin?", "url": "https://academy.binance.com/en/articles/what-is-bitcoin"},
    {"title": "What Is Ethereum?", "url": "https://academy.binance.com/en/articles/what-is-ethereum"},
    {"title": "What Is Blockchain?", "url": "https://academy.binance.com/en/articles/what-is-blockchain"},
    {"title": "What Is DeFi?", "url": "https://academy.binance.com/en/articles/what-is-defi"},
    {"title": "What Are NFTs?", "url": "https://academy.binance.com/en/articles/what-are-nfts"},
]

ARTICLE_CACHE: Dict[str, dict] = {}

# ================= MODELS =================

class ArticleFetchRequest(BaseModel):
    url: str

class GenerateQuizRequest(BaseModel):
    article_url: str
    article_title: str
    article_content: str
    num_questions: int = 10

# ================= SEARCH =================

async def search_binance_academy(query: str) -> list:
    query_lower = query.lower()

    # 1️⃣ local search
    local_results = [
        article for article in ARTICLES
        if query_lower in article["title"].lower()
    ]

    if local_results:
        return local_results[:10]

    # 2️⃣ Gemini dynamic topics (REAL FIX)
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
Generate 5 Binance Academy-style crypto topics related to: "{query}"

Return JSON:
[
  {{"title":"What Is Bitcoin?","url":"https://academy.binance.com/en/articles/what-is-bitcoin"}}
]
"""

        response = model.generate_content(prompt)
        text = response.text

        match = re.search(r'\[[\s\S]*\]', text)

        if not match:
            return ARTICLES

        data = json.loads(match.group())

        results = []
        for item in data:
            if "title" in item and "url" in item:
                results.append(item)

        # cache new topics
        ARTICLES.extend(results)

        return results

    except Exception as e:
        logger.error(e)
        return ARTICLES

# ================= FETCH ARTICLE =================

async def fetch_article_content(url: str) -> dict:
    if url in ARTICLE_CACHE:
        return ARTICLE_CACHE[url]

    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(url)

        soup = BeautifulSoup(resp.text, 'lxml')

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Crypto Article"

        paras = soup.find_all("p")
        content = "\n".join(p.get_text(strip=True) for p in paras[:50])

        result = {
            "title": title,
            "content": content,
            "url": url
        }

        ARTICLE_CACHE[url] = result
        return result

    except Exception as e:
        logger.error(f"Fetch error: {e}")
        return {
            "title": "Error",
            "content": "",
            "url": url
        }

# ================= QUIZ =================

async def generate_quiz_questions(title: str, content: str, num: int):

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")

        # STEP 1 — SUMMARIZE (IMPORTANT)
        summary_prompt = f"""
Summarize this crypto article in 200 words:

{content[:4000]}
"""

        summary_res = model.generate_content(summary_prompt)
        summary = summary_res.text

        # STEP 2 — GENERATE GAME-QUALITY QUIZ
        quiz_prompt = f"""
You are creating a Kahoot-style crypto quiz.

Generate {num} engaging multiple-choice questions.

Rules:
- Mix easy, medium, and hard questions
- Some questions should be tricky
- Keep questions short and exciting
- Avoid obvious answers
- Make it feel like a game show

Return JSON:
[
 {{
  "question":"...",
  "options":["A","B","C","D"],
  "correct":0,
  "explanation":"Short explanation"
 }}
]

Context:
{summary}
"""

        response = model.generate_content(quiz_prompt)
        text = response.text

        match = re.search(r'\[[\s\S]*\]', text)

        if not match:
            raise ValueError("No JSON returned")

        questions = json.loads(match.group())

        # validation (VERY IMPORTANT)
        cleaned = []
        for q in questions:
            if (
                isinstance(q, dict)
                and "question" in q
                and "options" in q
                and "correct" in q
                and len(q["options"]) == 4
            ):
                cleaned.append(q)

        if not cleaned:
            raise ValueError("No valid questions")

        return cleaned[:num]

    except Exception as e:
        logger.error(f"Quiz error: {e}")
        raise HTTPException(status_code=500, detail="Quiz generation failed")

# ================= ROUTES =================

@api_router.get("/health")
async def health():
    return {"status": "ok"}

@api_router.get("/academy/search")
async def search_academy(q: str = Query(...)):
    return {"results": await search_binance_academy(q)}

@api_router.post("/academy/article")
async def get_article(req: ArticleFetchRequest):
    return await fetch_article_content(req.url)

@api_router.post("/quiz/generate")
async def generate_quiz(req: GenerateQuizRequest):

    questions = await generate_quiz_questions(
        req.article_title,
        req.article_content,
        req.num_questions
    )

    doc = {
        "quiz_id": f"quiz_{secrets.token_hex(8)}",
        "article_title": req.article_title,
        "questions": questions,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.quizzes.insert_one(doc)
    doc.pop("_id", None)

    return doc

# ================= APP =================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
