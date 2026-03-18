from fastapi import FastAPI, Query, Request
from fastapi.responses import Response
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
from groq import Groq

# ================= INIT =================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ.get('DB_NAME', 'moltbot_app')]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_API_KEY)

GROQ_MODEL = "llama3-8b-8192"  # fast + generous free tier

app = FastAPI()

# ✅ Single CORS middleware
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

# ================= HELPERS =================

def groq_complete(prompt: str) -> str:
    """Simple wrapper — calls Groq and returns text."""
    chat = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048,
    )
    return chat.choices[0].message.content

# ================= MODELS =================

class ArticleFetchRequest(BaseModel):
    url: str

class GenerateQuizRequest(BaseModel):
    article_url: str
    article_title: Optional[str] = None
    article_content: Optional[str] = None
    num_questions: int = 10

class SessionCreateRequest(BaseModel):
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
    # Step 1 — try scraping first (no AI needed)
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

        if len(content) >= 200:
            logger.info(f"Scraped article OK: {title}")
            return {
                "title": title,
                "content": content[:6000],
                "url": url
            }

        logger.warning("Scraped content too short, trying AI fallback")

    except Exception as e:
        logger.error(f"Scrape failed: {e}")

    # Step 2 — Groq AI fallback
    try:
        topic = url.split("/")[-1].replace("-", " ")
        prompt = f"Write a 400-word educational crypto article about: {topic}. Make it clear and informative."
        text = groq_complete(prompt)
        return {
            "title": topic.title(),
            "content": text,
            "url": url
        }

    except Exception as e:
        logger.error(f"Groq fallback failed: {e}")
        topic = url.split("/")[-1].replace("-", " ").title()
        return {
            "title": topic,
            "content": f"{topic} is an important concept in the cryptocurrency and blockchain space. "
                       f"Understanding {topic} is essential for anyone interested in the future of finance and technology.",
            "url": url
        }

# ================= QUIZ =================

async def generate_quiz_questions(title: str, content: str, num: int):
    try:
        summary_prompt = f"Summarize this crypto article in 200 words:\n\n{content[:4000]}"
        summary = groq_complete(summary_prompt)

        quiz_prompt = f"""
Generate {num} multiple choice questions about this crypto topic.

Return JSON only, no markdown, no backticks, no explanation outside the JSON:
[
 {{
  "question":"...",
  "options":["A","B","C","D"],
  "correct":0,
  "explanation":"..."
 }}
]

Topic: {title}
Context: {summary}
"""
        text = groq_complete(quiz_prompt).strip()

        # Strip markdown fences if present
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            raise ValueError("No JSON array found in response")

        questions = json.loads(match.group())
        return questions[:num]

    except Exception as e:
        logger.error(f"Quiz generation error: {str(e)}")
        return [
            {
                "question": f"What is {title}?",
                "options": ["A blockchain concept", "A type of food", "A car brand", "A video game"],
                "correct": 0,
                "explanation": f"{title} is a concept in the crypto and blockchain space."
            }
        ]

# ================= ROUTES =================

@app.get("/")
async def root():
    return {"message": "API is live", "model": GROQ_MODEL}

@app.get("/api/health")
async def health():
    return {"status": "ok", "model": GROQ_MODEL}

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
            title = req.article_title or "Crypto Quiz"
            content = req.article_content

        questions = await generate_quiz_questions(title, content, req.num_questions)

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

@app.post("/api/session/create")
async def create_session(req: SessionCreateRequest):
    try:
        if not req.article_content:
            article = await fetch_article_content(req.article_url)
            title = article["title"]
            content = article["content"]
        else:
            title = req.article_title or "Crypto Quiz"
            content = req.article_content

        questions = await generate_quiz_questions(title, content, req.num_questions)

        code = secrets.token_hex(4).upper()

        import datetime
        session_doc = {
            "code": code,
            "article_title": title,
            "article_url": req.article_url,
            "questions": questions,
            "status": "waiting",
            "players": [],
            "created_at": str(datetime.datetime.utcnow()),
        }

        await db.sessions.insert_one(session_doc)
        session_doc.pop("_id", None)

        return session_doc

    except Exception as e:
        logger.error(f"Session create error: {str(e)}")
        return {"error": str(e)}
