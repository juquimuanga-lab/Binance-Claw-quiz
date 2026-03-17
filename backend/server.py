from fastapi import FastAPI, APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
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
from typing import Dict, Optional, List
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        model = genai.GenerativeModel("gemini-1.5-flash")
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
        model = genai.GenerativeModel("gemini-1.5-flash")

        summary_prompt = f"""
Summarize this crypto article in 200 words:

{content[:4000]}
"""
        summary_res = model.generate_content(summary_prompt)
        summary = summary_res.text

        quiz_prompt = f"""
Generate {num} multiple choice questions.

Return JSON:
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
        text = response.text

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

# ================= WEBSOCKET MANAGER =================

class ConnectionManager:
    def __init__(self):
        self.rooms: Dict[str, List[WebSocket]] = {}
        self.answers: Dict[str, Dict[str, dict]] = {}  # code -> {player_id -> answer}

    async def connect(self, code: str, ws: WebSocket):
        await ws.accept()
        if code not in self.rooms:
            self.rooms[code] = []
        self.rooms[code].append(ws)

    def disconnect(self, code: str, ws: WebSocket):
        if code in self.rooms:
            try:
                self.rooms[code].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, code: str, message: dict):
        if code in self.rooms:
            dead = []
            for ws in self.rooms[code]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(code, ws)

manager = ConnectionManager()

# ================= ROUTES =================

@app.get("/")
async def root():
    return {"message": "API is live"}

@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )

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

# ================= SESSION ROUTES =================

@api_router.get("/session/{code}")
async def get_session(code: str):
    session = await db.sessions.find_one({"code": code}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@api_router.post("/session/create")
async def create_session(req: GenerateQuizRequest):
    try:
        # Generate quiz first
        if not req.article_content:
            article = await fetch_article_content(req.article_url)
            title = article["title"]
            content = article["content"]
        else:
            title = req.article_title
            content = req.article_content

        questions = await generate_quiz_questions(title, content, req.num_questions)

        code = secrets.token_hex(3).upper()  # e.g. "A3F9C1"

        session = {
            "code": code,
            "article_title": title,
            "article_url": req.article_url,
            "questions": questions,
            "total_questions": len(questions),
            "current_index": 0,
            "players": [],
            "state": "lobby",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        await db.sessions.insert_one(session)

        return {"code": code, "total_questions": len(questions), "article_title": title}

    except Exception as e:
        logger.error(f"Session create error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ================= WEBSOCKET =================

@api_router.websocket("/ws/{code}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, code: str, player_id: str):
    await manager.connect(code, websocket)
    logger.info(f"WS connected: {player_id} -> room {code}")

    try:
        # Register player
        nickname = player_id.replace("host_", "Host") if player_id.startswith("host_") else player_id
        await db.sessions.update_one(
            {"code": code, "players.player_id": {"$ne": player_id}},
            {"$push": {"players": {"player_id": player_id, "nickname": nickname, "score": 0}}}
        )

        session = await db.sessions.find_one({"code": code}, {"_id": 0})
        players = session.get("players", []) if session else []
        await manager.broadcast(code, {"type": "player_joined", "players": players})

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            logger.info(f"WS msg from {player_id}: {msg_type}")

            if msg_type == "start_game":
                session = await db.sessions.find_one({"code": code})
                questions = session.get("questions", [])
                await db.sessions.update_one({"code": code}, {"$set": {"state": "playing", "current_index": 0}})

                await manager.broadcast(code, {
                    "type": "game_starting",
                    "total_questions": len(questions)
                })

                if questions:
                    q = questions[0]
                    await manager.broadcast(code, {
                        "type": "question",
                        "index": 0,
                        "total": len(questions),
                        "question": q["question"],
                        "options": q["options"],
                        "duration": 20
                    })

            elif msg_type == "answer":
                session = await db.sessions.find_one({"code": code})
                questions = session.get("questions", [])
                current = session.get("current_index", 0)
                players = session.get("players", [])

                if current < len(questions):
                    correct = questions[current].get("correct", 0)
                    is_correct = data.get("option") == correct
                    time_ms = data.get("time_ms", 20000)
                    points = max(0, int(1000 * (1 - time_ms / 20000))) if is_correct else 0

                    # Update player score
                    await db.sessions.update_one(
                        {"code": code, "players.player_id": player_id},
                        {"$inc": {"players.$.score": points}}
                    )

                    # Count answered
                    if code not in manager.answers:
                        manager.answers[code] = {}
                    manager.answers[code][player_id] = {"correct": is_correct, "points": points}

                    answered_count = len(manager.answers[code])
                    await manager.broadcast(code, {
                        "type": "player_answered",
                        "answered_count": answered_count
                    })

                    # If all players answered, send results
                    non_host_players = [p for p in players if not p["player_id"].startswith("host_")]
                    if answered_count >= len(non_host_players) and len(non_host_players) > 0:
                        session = await db.sessions.find_one({"code": code})
                        updated_players = sorted(session.get("players", []), key=lambda x: x.get("score", 0), reverse=True)
                        scores = [
                            {
                                "player_id": p["player_id"],
                                "nickname": p["nickname"],
                                "score": p.get("score", 0),
                                "delta": manager.answers[code].get(p["player_id"], {}).get("points", 0),
                                "is_correct": manager.answers[code].get(p["player_id"], {}).get("correct", False),
                                "answered": p["player_id"] in manager.answers[code]
                            }
                            for p in updated_players
                        ]
                        await manager.broadcast(code, {
                            "type": "answer_result",
                            "correct": correct,
                            "explanation": questions[current].get("explanation", ""),
                            "question_index": current,
                            "scores": scores
                        })
                        manager.answers[code] = {}  # reset for next question

            elif msg_type == "next_question":
                session = await db.sessions.find_one({"code": code})
                questions = session.get("questions", [])
                current = session.get("current_index", 0) + 1
                await db.sessions.update_one({"code": code}, {"$set": {"current_index": current}})
                manager.answers[code] = {}  # reset answers

                if current < len(questions):
                    q = questions[current]
                    await manager.broadcast(code, {
                        "type": "question",
                        "index": current,
                        "total": len(questions),
                        "question": q["question"],
                        "options": q["options"],
                        "duration": 20
                    })
                else:
                    session = await db.sessions.find_one({"code": code})
                    final_players = sorted(session.get("players", []), key=lambda x: x.get("score", 0), reverse=True)
                    standings = [
                        {
                            "player_id": p["player_id"],
                            "nickname": p["nickname"],
                            "score": p.get("score", 0),
                            "rank": i + 1
                        }
                        for i, p in enumerate(final_players)
                    ]
                    await db.sessions.update_one({"code": code}, {"$set": {"state": "finished"}})
                    await manager.broadcast(code, {
                        "type": "game_over",
                        "final_standings": standings
                    })

    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
        logger.info(f"WS disconnected: {player_id} from room {code}")
        session = await db.sessions.find_one({"code": code}, {"_id": 0})
        players = session.get("players", []) if session else []
        await manager.broadcast(code, {"type": "player_left", "players": players})

    except Exception as e:
        logger.error(f"WS error {player_id}: {str(e)}")
        manager.disconnect(code, websocket)

# ================= APP =================
app.include_router(api_router)
