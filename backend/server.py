from fastapi import FastAPI, Query, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import secrets
import httpx
import re
import datetime
import asyncio
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

# ✅ Updated model — llama3-8b-8192 is decommissioned
GROQ_MODEL = "llama-3.3-70b-versatile"

app = FastAPI()

# ================= CORS =================

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

# ================= WEBSOCKET MANAGER =================

class GameManager:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, WebSocket]] = {}
        self.game_state: Dict[str, dict] = {}

    async def connect(self, code: str, player_id: str, ws: WebSocket):
        await ws.accept()
        if code not in self.rooms:
            self.rooms[code] = {}
        self.rooms[code][player_id] = ws

    def disconnect(self, code: str, player_id: str):
        if code in self.rooms:
            self.rooms[code].pop(player_id, None)

    async def broadcast(self, code: str, message: dict):
        if code not in self.rooms:
            return
        dead = []
        for pid, ws in self.rooms[code].items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(pid)
        for pid in dead:
            self.rooms[code].pop(pid, None)

    async def send_to(self, code: str, player_id: str, message: dict):
        ws = self.rooms.get(code, {}).get(player_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                pass

manager = GameManager()

# ================= HELPERS =================

def groq_complete(prompt: str) -> str:
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

class SessionJoinRequest(BaseModel):
    code: str
    nickname: str

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
            {"title": k.title(), "url": f"https://academy.binance.com/en/articles/{v}"}
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
            p.get_text(strip=True) for p in paragraphs
            if len(p.get_text(strip=True)) > 50
        )
        if len(content) >= 200:
            return {"title": title, "content": content[:6000], "url": url}
        logger.warning("Scraped content too short, trying AI fallback")
    except Exception as e:
        logger.error(f"Scrape failed: {e}")

    try:
        topic = url.split("/")[-1].replace("-", " ")
        text = groq_complete(f"Write a 400-word educational crypto article about: {topic}.")
        return {"title": topic.title(), "content": text, "url": url}
    except Exception as e:
        logger.error(f"Groq fallback failed: {e}")
        topic = url.split("/")[-1].replace("-", " ").title()
        return {
            "title": topic,
            "content": f"{topic} is an important concept in the cryptocurrency and blockchain space.",
            "url": url
        }

# ================= QUIZ GENERATION =================

async def generate_quiz_questions(title: str, content: str, num: int):
    try:
        summary = groq_complete(f"Summarize this crypto article in 200 words:\n\n{content[:4000]}")
        quiz_prompt = f"""
Generate {num} multiple choice questions about this crypto topic.
Return JSON only, no markdown, no backticks:
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
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"^```\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        match = re.search(r'\[[\s\S]*\]', text)
        if not match:
            raise ValueError("No JSON array found")
        questions = json.loads(match.group())
        return questions[:num]
    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        return [
            {
                "question": f"What is {title}?",
                "options": ["A blockchain concept", "A type of food", "A car brand", "A video game"],
                "correct": 0,
                "explanation": f"{title} is a concept in the crypto space."
            }
        ]

# ================= GAME LOOP =================

async def run_question(code: str, q: dict, index: int, total: int):
    duration = 20
    state = manager.game_state[code]

    await manager.broadcast(code, {
        "type": "question",
        "index": index,
        "total": total,
        "question": q["question"],
        "options": q["options"],
        "duration": duration,
    })

    state["current_question"] = index
    state["answers"] = {}
    state["answered_count"] = 0

    for t in range(duration, -1, -1):
        await manager.broadcast(code, {"type": "timer", "seconds": t})
        await asyncio.sleep(1)
        players_count = len([
            p for p in state["players"]
            if not p["player_id"].startswith("host_")
        ])
        if state["answered_count"] >= players_count and players_count > 0:
            break

    correct_idx = q["correct"]
    scores = []
    for player in state["players"]:
        pid = player["player_id"]
        if pid.startswith("host_"):
            continue
        answer_data = state["answers"].get(pid)
        is_correct = answer_data and answer_data["option"] == correct_idx
        delta = 0
        if is_correct:
            time_ms = answer_data.get("time_ms", duration * 1000)
            delta = max(100, 1000 - int(time_ms / 100))
            player["score"] = player.get("score", 0) + delta
        scores.append({
            "player_id": pid,
            "nickname": player["nickname"],
            "score": player.get("score", 0),
            "delta": delta,
            "is_correct": is_correct,
            "answered": answer_data is not None,
        })

    scores.sort(key=lambda x: x["score"], reverse=True)

    await manager.broadcast(code, {
        "type": "answer_result",
        "correct": correct_idx,
        "explanation": q.get("explanation", ""),
        "scores": scores,
        "question_index": index,
    })

    await db.sessions.update_one(
        {"code": code},
        {"$set": {"players": state["players"]}}
    )

async def run_game(code: str):
    try:
        state = manager.game_state[code]
        questions = state["questions"]
        total = len(questions)

        logger.info(f"Game starting for room {code} with {total} questions")

        await manager.broadcast(code, {
            "type": "game_starting",
            "total_questions": total,
        })
        await asyncio.sleep(3)

        for i, q in enumerate(questions):
            await run_question(code, q, i, total)
            if i < total - 1:
                # ✅ Wait for host to press Next Question
                state["waiting_for_next"] = True
                logger.info(f"Waiting for host next_question signal, Q{i+1}/{total}")
                for _ in range(60):  # wait up to 60s
                    await asyncio.sleep(1)
                    if not state.get("waiting_for_next", True):
                        break

        standings = sorted(
            [
                {
                    "player_id": p["player_id"],
                    "nickname": p["nickname"],
                    "score": p.get("score", 0)
                }
                for p in state["players"]
                if not p["player_id"].startswith("host_")
            ],
            key=lambda x: x["score"],
            reverse=True
        )
        for i, s in enumerate(standings):
            s["rank"] = i + 1

        await manager.broadcast(code, {
            "type": "game_over",
            "final_standings": standings,
        })

        await db.sessions.update_one(
            {"code": code},
            {"$set": {"status": "finished", "final_standings": standings}}
        )
        logger.info(f"Game over for room {code}")

    except Exception as e:
        logger.error(f"run_game error for {code}: {e}")

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

@app.get("/api/session/{code}")
async def get_session(code: str):
    session = await db.sessions.find_one({"code": code.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.pop("_id", None)
    session["total_questions"] = len(session.get("questions", []))
    return session

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
        logger.error(f"Quiz endpoint error: {e}")
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
        logger.error(f"Session create error: {e}")
        return {"error": str(e)}

@app.post("/api/session/join")
async def join_session(req: SessionJoinRequest):
    try:
        code = req.code.strip().upper()
        nickname = req.nickname.strip()

        if not code or not nickname:
            raise HTTPException(status_code=400, detail="Code and nickname are required")

        session = await db.sessions.find_one({"code": code})
        if not session:
            raise HTTPException(status_code=404, detail="Game not found. Check your code and try again.")
        if session.get("status") == "finished":
            raise HTTPException(status_code=400, detail="This game has already ended.")

        player_id = f"player_{secrets.token_hex(6)}"
        player = {
            "player_id": player_id,
            "nickname": nickname,
            "score": 0,
            "joined_at": str(datetime.datetime.utcnow()),
        }

        await db.sessions.update_one({"code": code}, {"$push": {"players": player}})

        if code in manager.game_state:
            manager.game_state[code]["players"].append(player)

        session.pop("_id", None)
        return {"player_id": player_id, "session": session}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Join session error: {e}")
        raise HTTPException(status_code=500, detail="Server error while joining game")

# ================= WEBSOCKET =================

@app.websocket("/api/ws/{code}/{player_id}")
async def websocket_endpoint(ws: WebSocket, code: str, player_id: str):
    code = code.upper()

    # ✅ Manually accept with CORS headers to fix 403
    await ws.accept()
    if code not in manager.rooms:
        manager.rooms[code] = {}
    manager.rooms[code][player_id] = ws

    logger.info(f"WS connected: {player_id} -> room {code}")

    # Load session into memory if not already there
    if code not in manager.game_state:
        session = await db.sessions.find_one({"code": code})
        if session:
            manager.game_state[code] = {
                "questions": session.get("questions", []),
                "players": session.get("players", []),
                "current_question": -1,
                "answers": {},
                "answered_count": 0,
                "started": False,
                "waiting_for_next": False,
            }

    try:
        # Broadcast updated player list on connect
        session = await db.sessions.find_one({"code": code})
        if session:
            await manager.broadcast(code, {
                "type": "player_joined",
                "players": session.get("players", []),
            })

        # ✅ Keep-alive ping loop + message handler
        async def receive_loop():
            while True:
                data = await ws.receive_json()
                msg_type = data.get("type")
                logger.info(f"WS message from {player_id}: {msg_type}")

                if msg_type == "start_game" and player_id.startswith("host_"):
                    state = manager.game_state.get(code)
                    if state and not state.get("started"):
                        state["started"] = True
                        session = await db.sessions.find_one({"code": code})
                        if session:
                            state["players"] = session.get("players", [])
                        await db.sessions.update_one(
                            {"code": code},
                            {"$set": {"status": "playing"}}
                        )
                        logger.info(f"Starting game for room {code}")
                        asyncio.create_task(run_game(code))

                elif msg_type == "answer":
                    state = manager.game_state.get(code)
                    if state and player_id not in state["answers"]:
                        state["answers"][player_id] = {
                            "option": data.get("option"),
                            "time_ms": data.get("time_ms", 0),
                        }
                        state["answered_count"] += 1
                        await manager.broadcast(code, {
                            "type": "player_answered",
                            "answered_count": state["answered_count"],
                        })

                elif msg_type == "next_question" and player_id.startswith("host_"):
                    state = manager.game_state.get(code)
                    if state:
                        state["waiting_for_next"] = False

                elif msg_type == "ping":
                    await ws.send_json({"type": "pong"})

        await receive_loop()

    except WebSocketDisconnect:
        manager.disconnect(code, player_id)
        logger.info(f"WS disconnected: {player_id} from {code}")
        session = await db.sessions.find_one({"code": code})
        if session:
            await manager.broadcast(code, {
                "type": "player_left",
                "players": session.get("players", []),
            })
    except Exception as e:
        logger.error(f"WS error for {player_id}: {e}")
        manager.disconnect(code, player_id)
