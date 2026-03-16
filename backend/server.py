from fastapi import FastAPI, APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import secrets
import asyncio
import httpx
import re
import uuid
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import google.generativeai as genai

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ.get('DB_NAME', 'moltbot_app')]

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', '')
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArticleFetchRequest(BaseModel):
    url: str


class GenerateQuizRequest(BaseModel):
    article_url: str
    article_title: str
    article_content: str
    num_questions: int = 10


class CreateSessionRequest(BaseModel):
    host_name: str
    quiz_id: str


class JoinSessionRequest(BaseModel):
    code: str
    nickname: str


ACADEMY_BASE = "https://www.binance.com/en/academy"
ARTICLE_CACHE: Dict[str, dict] = {}


async def search_binance_academy(query: str) -> list:
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as http:
            resp = await http.get(ACADEMY_BASE, headers=headers)
            soup = BeautifulSoup(resp.text, 'lxml')

            seen = set()
            for a in soup.find_all('a', href=True):
                href = a.get('href', '')
                if '/academy/articles/' in href:
                    text = a.get_text(strip=True)
                    if text and text not in seen:
                        seen.add(text)
                        full_url = href if href.startswith('http') else f"https://www.binance.com{href}"
                        results.append({"title": text, "url": full_url})

    except Exception as e:
        logger.error(e)

    return results[:15]


async def fetch_article_content(url: str) -> dict:
    if url in ARTICLE_CACHE:
        return ARTICLE_CACHE[url]

    async with httpx.AsyncClient() as http:
        resp = await http.get(url)

    soup = BeautifulSoup(resp.text, 'lxml')

    title = soup.find('h1').get_text(strip=True)

    paras = soup.find_all("p")
    content = "\n".join(p.get_text(strip=True) for p in paras)

    result = {"title": title, "content": content[:6000], "url": url}
    ARTICLE_CACHE[url] = result

    return result


async def generate_quiz_questions(article_title: str, article_content: str, num_questions: int = 10) -> list:

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = f"""
Generate {num_questions} quiz questions from this Binance Academy article.

Title: {article_title}

Content:
{article_content[:4500]}

Return ONLY JSON:

[
 {{
  "question":"...",
  "options":["A","B","C","D"],
  "correct":0,
  "explanation":"..."
 }}
]
"""

    response = model.generate_content(prompt)
    text = response.text

    match = re.search(r'\[.*\]', text, re.DOTALL)
    questions = json.loads(match.group())

    return questions[:num_questions]


active_games: Dict[str, dict] = {}


@api_router.get("/health")
async def health():
    return {"status": "ok"}


@api_router.get("/academy/search")
async def search_academy(q: str = Query(..., min_length=1)):
    results = await search_binance_academy(q)
    return {"results": results}


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

    quiz_id = f"quiz_{secrets.token_hex(8)}"

    doc = {
        "quiz_id": quiz_id,
        "article_title": req.article_title,
        "article_url": req.article_url,
        "questions": questions,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await db.quizzes.insert_one(doc)
    doc.pop("_id", None)

    return doc


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
