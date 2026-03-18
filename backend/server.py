from fastapi import FastAPI, APIRouter, Query, Request
from fastapi.responses import Response
from fastapi.routing import APIRoute
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import secrets
import httpx
import re
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Optional
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

GEMINI_MODEL = "gemini-2.0-flash"

app = FastAPI()

# ✅ CORS middleware — must be added BEFORE include_router
@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Max-Age": "86400",
            }
        )
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= MODELS =================

class ArticleFetchRequest(BaseModel):
    url: str

class GenerateQuizRequest(BaseModel):
    article_url: str
    article_title: Optional[str] = None
    article_content: Optional[str] = None
    num_questions: int = 10

# ================= SEARCH =================

async def search_binance_academy(query: str) -> list:
    query = query.lower()

    mapping = {
        "bitcoin": "what-is-bitcoin",
        "ethereum": "what-is-ethereum",
        "defi": "what-is-defi",
        "nft": "what-are-nfts",
        "staking": "what-is-staking",
        "blockchain": "what-is-blockchain",
        "web3": "what-is-web3",
        "wallet": "crypto-wallet-types-explained",
        "trading": "spot-trading-explained",
        "security": "crypto-security"
    }

    results = []

    for key, slug in mapping.items():
        if key in query:
            results.append({
                "title": key.title(),
                "url": f"https://academy.binance.com/en/articles/{slug}"
            })

    if not results:
        results = [
            {
                "title": k.title(),
                "url": f"https://academy.binance.com/en/articles/{v}"
            }
            for k, v in mapping.items()
        ]

    return results[:10]

# ================= FETCH ARTICLE =================

async def fetch_article_content(url: str) -> dict:
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15.0,
            follow_redirects=True
        ) as http:
            resp = await http.get(url)
            raw_html = resp.text

        soup = BeautifulSoup(raw_html, "lxml")

        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Crypto Article"

        paragraphs = soup.find_all(["p", "h2", "h3"])
        content = "\n".join(
            p.get_text(strip=True)
            for p in paragraphs
            if len(p.get_text(strip=True)) > 50
        )

        if len(content) < 200:
            raise ValueError("Content too small")

        return {
            "title": title,
            "content": content[:6000],
            "url": url
        }

    except Exception as e:
        logger.error(f"Scrape failed, using AI fallback: {e}")

        model = genai.GenerativeModel(GEMINI_MODEL)
        prompt = f"""
Write a 400-word educational crypto article about:

{url.split("/")[-1].replace("-", " ")}

Make it clear and informative.
"""
        res = model.generate_content(prompt)

        return {
            "title": url.split("/")[-1].replace("-", " ").title(),
            "content": res.text,
            "url": url
        }

# ================= QUIZ =================

async def generate_quiz_questions(title: str, content: str, num: int):
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)

        summary_prompt = f"""
Summarize this crypto article in 200 words:

{content[:4000]}
"""
        summary_res = model.generate_content(summary_prompt)
        summary = summary_res.text

        quiz_prompt = f"""
Generate {num} multiple choice questions.

Return JSON only, no markdown, no backticks:
[
 {{
  "question":"...",
  "options":["A","B","C","D"],
  "correct":0,
  "explanation":"..."
 }}
]

Context:
{summary}
"""
        response = model.generate_content(quiz_prompt)
        text = response.text.strip()

        # ✅ Strip markdown code fences if Gemini wraps in ```json
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            raise ValueError("No JSON returned")

        questions = json.loads(match.group())
        return questions[:num]

    except Exception as e:
        logger.error(f"Quiz error: {str(e)}")
        return [
            {
                "question": f"What is {title}?",
                "options": ["A crypto concept", "A food", "A car", "A game"],
                "correct": 0,
                "explanation": "Fallback question"
            }
        ]

# ================= ROUTES =================
# ✅ Define routes directly on app — no separate router to avoid prefix/registration issues

@app.get("/")
async def root():
    return {"message": "API is live"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "model": GEMINI_MODEL}

@app.get("/api/academy/search")
async def search_academy(q: str = Query(...)):
    return {"results": await search_binance_academy(q)}

@app.post("/api/academy/article")
async def get_article(req: ArticleFetchRequest):
    return await fetch_article_content(req.url)

@app.post("/api/quiz/generate")
async def generate_quiz(req: GenerateQuizRequest):
    try:
        if not req.article_content:
            article = await fetch_article_content(req.article_url)
            title = article["title"]
            content = article["content"]
        else:
            title = req.article_title
            content = req.article_content

        questions = await generate_quiz_questions(
            title,
            content,
            req.num_questions
        )

        doc = {
            "quiz_id": f"quiz_{secrets.token_hex(8)}",
            "article_title": title,
            "questions": questions,
        }

        await db.quizzes.insert_one(doc)
        doc.pop("_id", None)

        return doc

    except Exception as e:
        logger.error(f"Quiz endpoint error: {str(e)}")
        return {"error": str(e)}

# ================= APP =================
app.include_router(api_router)
