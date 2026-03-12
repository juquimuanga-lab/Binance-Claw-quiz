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
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ.get('DB_NAME', 'moltbot_app')]

TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', '')

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============== Pydantic Models ==============

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


# ============== Binance Academy ==============

ACADEMY_BASE = "https://www.binance.com/en/academy"
ARTICLE_CACHE: Dict[str, dict] = {}

async def search_binance_academy(query: str) -> list:
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    results = []

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as http:
            resp = await http.get(ACADEMY_BASE, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                seen = set()
                for a in soup.find_all('a', href=True):
                    href = a.get('href', '')
                    if '/academy/articles/' in href:
                        text = a.get_text(strip=True)
                        if text and len(text) > 5 and text not in seen:
                            seen.add(text)
                            full_url = href if href.startswith('http') else f"https://www.binance.com{href}"
                            results.append({"title": text, "url": full_url})
    except Exception as e:
        logger.error(f"Academy scrape error: {e}")

    query_lower = query.lower().split()
    filtered = [r for r in results if any(w in r['title'].lower() for w in query_lower)]

    if not filtered and EMERGENT_LLM_KEY:
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"search-{uuid.uuid4().hex[:8]}",
                system_message="You suggest Binance Academy article topics. Return ONLY a JSON array."
            ).with_model("openai", "gpt-4o")

            resp = await chat.send_message(UserMessage(
                text=f'Suggest 8 Binance Academy article topics related to "{query}". Return JSON array: [{{"title":"What Is Bitcoin?","url":"https://www.binance.com/en/academy/articles/what-is-bitcoin"}}]'
            ))
            match = re.search(r'\[.*\]', resp, re.DOTALL)
            if match:
                filtered = json.loads(match.group())[:8]
        except Exception as e:
            logger.error(f"LLM search error: {e}")

    return filtered[:15] if filtered else results[:15]


async def fetch_article_content(url: str) -> dict:
    if url in ARTICLE_CACHE:
        return ARTICLE_CACHE[url]

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    title = ""
    content = ""

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as http:
            resp = await http.get(url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                h1 = soup.find('h1')
                if h1:
                    title = h1.get_text(strip=True)
                for sel in ['article', 'div[class*="article"]', 'div[class*="content"]', 'main']:
                    elem = soup.select_one(sel)
                    if elem:
                        paras = elem.find_all(['p', 'h2', 'h3', 'h4', 'li'])
                        content = "\n".join(p.get_text(strip=True) for p in paras if p.get_text(strip=True))
                        if len(content) > 200:
                            break
                if len(content) < 200:
                    paras = soup.find_all('p')
                    content = "\n".join(p.get_text(strip=True) for p in paras[:50] if p.get_text(strip=True))
    except Exception as e:
        logger.warning(f"Article scrape failed (fast fallback to LLM): {e}")

    if len(content) < 100 and EMERGENT_LLM_KEY:
        topic = url.split('/')[-1].replace('-', ' ').title()
        if not title:
            title = topic
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"content-{uuid.uuid4().hex[:8]}",
                system_message="You write concise educational crypto articles. Be direct and factual."
            ).with_model("openai", "gpt-4o")
            resp_text = await chat.send_message(UserMessage(
                text=f"Write a 400-word educational summary about '{title}' covering key concepts, how it works, and why it matters in crypto."
            ))
            content = resp_text
        except Exception as e:
            logger.error(f"LLM content error: {e}")

    result = {"title": title or url.split('/')[-1].replace('-', ' ').title(), "content": content[:6000], "url": url}
    ARTICLE_CACHE[url] = result
    return result


# ============== Quiz Generation ==============

async def generate_quiz_questions(article_title: str, article_content: str, num_questions: int = 10) -> list:
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"quiz-{uuid.uuid4().hex[:8]}",
        system_message="You generate quiz questions. Return ONLY valid JSON arrays."
    ).with_model("openai", "gpt-4o")

    prompt = f"""Generate {num_questions} multiple choice quiz questions from this Binance Academy article.

Title: "{article_title}"
Content: {article_content[:4500]}

Return ONLY a JSON array:
[{{"question":"What is...?","options":["A","B","C","D"],"correct":0,"explanation":"Because..."}}]

Rules: exactly 4 options, correct is 0-based index, questions under 120 chars, options under 60 chars."""

    response = await chat.send_message(UserMessage(text=prompt))

    try:
        cleaned = response.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```\w*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned)
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        questions = json.loads(match.group()) if match else json.loads(cleaned)

        validated = []
        for q in questions:
            if (isinstance(q, dict) and
                all(k in q for k in ['question', 'options', 'correct', 'explanation']) and
                isinstance(q['options'], list) and len(q['options']) == 4 and
                isinstance(q['correct'], int) and 0 <= q['correct'] <= 3):
                validated.append({
                    "question": str(q['question']),
                    "options": [str(o) for o in q['options']],
                    "correct": int(q['correct']),
                    "explanation": str(q.get('explanation', ''))
                })
        if not validated:
            raise ValueError("No valid questions")
        return validated[:num_questions]
    except Exception as e:
        logger.error(f"Quiz parse error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate quiz. Please try again.")


# ============== WebSocket Game Engine ==============

active_games: Dict[str, dict] = {}

async def broadcast(code: str, message: dict):
    if code not in active_games:
        return
    game = active_games[code]
    data = json.dumps(message)
    if game.get("host_ws"):
        try:
            await game["host_ws"].send_text(data)
        except Exception:
            pass
    for pid, info in list(game.get("players", {}).items()):
        if info.get("ws"):
            try:
                await info["ws"].send_text(data)
            except Exception:
                pass


async def run_timer(code: str, qi: int, duration: int = 20):
    try:
        for rem in range(duration, 0, -1):
            await asyncio.sleep(1)
            if code not in active_games:
                return
            await broadcast(code, {"type": "timer", "seconds": rem})
        await calculate_results(code, qi)
    except asyncio.CancelledError:
        pass


async def calculate_results(code: str, qi: int):
    session = await db.sessions.find_one({"code": code}, {"_id": 0})
    if not session:
        return
    questions = session.get("questions", [])
    if qi >= len(questions):
        return

    correct_idx = questions[qi]["correct"]
    explanation = questions[qi].get("explanation", "")
    players = await db.players.find({"session_code": code}, {"_id": 0}).to_list(100)

    scores = []
    for p in players:
        ans = next((a for a in p.get("answers", []) if a.get("question_index") == qi), None)
        delta = 0
        is_correct = False
        if ans and ans.get("option") == correct_idx:
            is_correct = True
            time_ms = ans.get("time_ms", 20000)
            delta = max(500, 1000 - int(time_ms / 20))
            await db.players.update_one(
                {"session_code": code, "player_id": p["player_id"]},
                {"$inc": {"score": delta}}
            )
        scores.append({
            "player_id": p["player_id"],
            "nickname": p["nickname"],
            "score": p.get("score", 0) + delta,
            "delta": delta,
            "is_correct": is_correct,
            "answered": ans is not None
        })

    scores.sort(key=lambda x: x["score"], reverse=True)
    for i, s in enumerate(scores):
        s["rank"] = i + 1

    await broadcast(code, {
        "type": "answer_result",
        "question_index": qi,
        "correct": correct_idx,
        "explanation": explanation,
        "scores": scores
    })

    if qi >= len(questions) - 1:
        await asyncio.sleep(3)
        await broadcast(code, {"type": "game_over", "final_standings": scores})
        await db.sessions.update_one({"code": code}, {"$set": {"status": "finished"}})


# ============== API Endpoints ==============

@api_router.get("/health")
async def health():
    return {"status": "ok", "service": "BinanceClawQuiz"}

@api_router.get("/academy/search")
async def search_academy(q: str = Query(..., min_length=1)):
    results = await search_binance_academy(q)
    return {"results": results, "query": q}

@api_router.post("/academy/article")
async def get_article(req: ArticleFetchRequest):
    return await fetch_article_content(req.url)

@api_router.post("/quiz/generate")
async def generate_quiz(req: GenerateQuizRequest):
    questions = await generate_quiz_questions(req.article_title, req.article_content, req.num_questions)
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

@api_router.post("/session/create")
async def create_session(req: CreateSessionRequest):
    quiz = await db.quizzes.find_one({"quiz_id": req.quiz_id}, {"_id": 0})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    code = secrets.token_hex(4).upper()
    slug = f"q-{secrets.token_urlsafe(8)}"

    doc = {
        "code": code,
        "slug": slug,
        "host_name": req.host_name,
        "quiz_id": req.quiz_id,
        "article_title": quiz["article_title"],
        "questions": quiz["questions"],
        "status": "waiting",
        "current_question": -1,
        "duration": 20,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.sessions.insert_one(doc)
    doc.pop("_id", None)

    active_games[code] = {"host_ws": None, "players": {}, "timer_task": None}
    return {"code": code, "slug": slug, "session": doc}

@api_router.post("/session/join")
async def join_session(req: JoinSessionRequest):
    code = req.code.strip().upper()
    session = await db.sessions.find_one(
        {"code": code, "status": {"$in": ["waiting", "playing"]}},
        {"_id": 0}
    )
    if not session:
        raise HTTPException(status_code=404, detail="Game not found or already finished")

    pid = f"p_{secrets.token_hex(6)}"
    doc = {
        "player_id": pid,
        "session_code": code,
        "nickname": req.nickname[:20],
        "score": 0,
        "answers": [],
        "joined_at": datetime.now(timezone.utc).isoformat()
    }
    await db.players.insert_one(doc)
    doc.pop("_id", None)

    safe_session = {k: v for k, v in session.items() if k != "questions"}
    safe_session["total_questions"] = len(session.get("questions", []))
    return {"player_id": pid, "session": safe_session}

@api_router.get("/session/{code}")
async def get_session(code: str):
    session = await db.sessions.find_one({"code": code.upper()}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    safe = {k: v for k, v in session.items() if k != "questions"}
    safe["total_questions"] = len(session.get("questions", []))
    players = await db.players.find(
        {"session_code": code.upper()}, {"_id": 0, "answers": 0}
    ).to_list(100)
    safe["players"] = players
    return safe

@api_router.get("/session/{code}/players")
async def get_players(code: str):
    players = await db.players.find(
        {"session_code": code.upper()}, {"_id": 0, "answers": 0}
    ).to_list(100)
    return {"players": players}

@api_router.post("/quiz/solo")
async def generate_solo_quiz(req: GenerateQuizRequest):
    questions = await generate_quiz_questions(req.article_title, req.article_content, req.num_questions)
    return {
        "quiz_id": f"solo_{secrets.token_hex(8)}",
        "article_title": req.article_title,
        "questions": questions
    }


# ============== WebSocket ==============

@api_router.websocket("/ws/{code}/{player_id}")
async def ws_endpoint(websocket: WebSocket, code: str, player_id: str):
    code = code.upper()
    await websocket.accept()

    is_host = player_id.startswith("host_")

    if code not in active_games:
        active_games[code] = {"host_ws": None, "players": {}, "timer_task": None}
    game = active_games[code]

    if is_host:
        game["host_ws"] = websocket
    else:
        nickname = ""
        player = await db.players.find_one({"player_id": player_id, "session_code": code}, {"_id": 0})
        if player:
            nickname = player.get("nickname", "")
        game["players"][player_id] = {"ws": websocket, "nickname": nickname}

        all_p = await db.players.find({"session_code": code}, {"_id": 0, "answers": 0}).to_list(100)
        await broadcast(code, {
            "type": "player_joined",
            "player": {"id": player_id, "nickname": nickname},
            "player_count": len(all_p),
            "players": all_p
        })

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg["type"] == "start_game" and is_host:
                await db.sessions.update_one(
                    {"code": code},
                    {"$set": {"status": "playing", "current_question": 0}}
                )
                session = await db.sessions.find_one({"code": code}, {"_id": 0})
                qs = session.get("questions", [])
                if qs:
                    await broadcast(code, {"type": "game_starting", "total_questions": len(qs)})
                    await asyncio.sleep(2)
                    q = qs[0]
                    await broadcast(code, {
                        "type": "question", "index": 0, "total": len(qs),
                        "question": q["question"], "options": q["options"],
                        "duration": session.get("duration", 20)
                    })
                    if game.get("timer_task"):
                        game["timer_task"].cancel()
                    game["timer_task"] = asyncio.create_task(
                        run_timer(code, 0, session.get("duration", 20))
                    )

            elif msg["type"] == "next_question" and is_host:
                session = await db.sessions.find_one({"code": code}, {"_id": 0})
                qi = session.get("current_question", 0) + 1
                qs = session.get("questions", [])
                if qi < len(qs):
                    await db.sessions.update_one({"code": code}, {"$set": {"current_question": qi}})
                    q = qs[qi]
                    await broadcast(code, {
                        "type": "question", "index": qi, "total": len(qs),
                        "question": q["question"], "options": q["options"],
                        "duration": session.get("duration", 20)
                    })
                    if game.get("timer_task"):
                        game["timer_task"].cancel()
                    game["timer_task"] = asyncio.create_task(
                        run_timer(code, qi, session.get("duration", 20))
                    )

            elif msg["type"] == "answer" and not is_host:
                option = msg.get("option")
                time_ms = msg.get("time_ms", 20000)
                session = await db.sessions.find_one({"code": code}, {"_id": 0})
                qi = session.get("current_question", 0)

                player = await db.players.find_one(
                    {"player_id": player_id, "session_code": code}, {"_id": 0}
                )
                already = any(a.get("question_index") == qi for a in player.get("answers", []))
                if not already:
                    await db.players.update_one(
                        {"player_id": player_id, "session_code": code},
                        {"$push": {"answers": {
                            "question_index": qi, "option": option, "time_ms": time_ms
                        }}}
                    )
                    total_p = await db.players.count_documents({"session_code": code})
                    all_p = await db.players.find({"session_code": code}, {"_id": 0}).to_list(100)
                    answered_count = sum(
                        1 for p in all_p
                        if any(a.get("question_index") == qi for a in p.get("answers", []))
                    )
                    await broadcast(code, {
                        "type": "player_answered",
                        "answered_count": answered_count,
                        "total_players": total_p
                    })
                    if answered_count >= total_p:
                        if game.get("timer_task"):
                            game["timer_task"].cancel()
                        await calculate_results(code, qi)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error: {e}")
    finally:
        if is_host:
            game["host_ws"] = None
        else:
            game["players"].pop(player_id, None)
            all_p = await db.players.find({"session_code": code}, {"_id": 0, "answers": 0}).to_list(100)
            await broadcast(code, {
                "type": "player_left",
                "player_id": player_id,
                "player_count": len(game.get("players", {})),
                "players": all_p
            })


# ============== Telegram Bot ==============

@api_router.post("/telegram/webhook")
async def telegram_webhook(request: dict):
    try:
        message = request.get("message", {})
        text = message.get("text", "")
        chat_id = message.get("chat", {}).get("id")
        if not chat_id:
            return {"ok": True}

        bot_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
        async with httpx.AsyncClient() as http:
            if text.startswith("/start"):
                parts = text.split()
                join_code = parts[1] if len(parts) > 1 else None
                webapp_url = f"{FRONTEND_URL}?join={join_code}" if join_code else FRONTEND_URL
                await http.post(f"{bot_api}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "Welcome to Binance Claw Quiz! Test your crypto knowledge with friends!",
                    "reply_markup": {"inline_keyboard": [[
                        {"text": "Play Now", "web_app": {"url": webapp_url}}
                    ]]}
                })
            elif text.startswith("/quiz"):
                await http.post(f"{bot_api}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "Create a new quiz from Binance Academy!",
                    "reply_markup": {"inline_keyboard": [[
                        {"text": "Host a Quiz", "web_app": {"url": f"{FRONTEND_URL}/host"}}
                    ]]}
                })
            elif text.startswith("/join"):
                await http.post(f"{bot_api}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": "Join a quiz game!",
                    "reply_markup": {"inline_keyboard": [[
                        {"text": "Join Game", "web_app": {"url": f"{FRONTEND_URL}/join"}}
                    ]]}
                })
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
    return {"ok": True}

@api_router.post("/telegram/setup")
async def setup_telegram():
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=500, detail="No bot token")
    bot_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    results = {}
    async with httpx.AsyncClient() as http:
        r = await http.post(f"{bot_api}/setMyCommands", json={
            "commands": [
                {"command": "start", "description": "Start Binance Claw Quiz"},
                {"command": "quiz", "description": "Create a quiz"},
                {"command": "join", "description": "Join a game"}
            ]
        })
        results["commands"] = r.json()
        if FRONTEND_URL:
            r = await http.post(f"{bot_api}/setChatMenuButton", json={
                "menu_button": {"type": "web_app", "text": "Claw Quiz", "web_app": {"url": FRONTEND_URL}}
            })
            results["menu"] = r.json()
            webhook_url = FRONTEND_URL.rstrip('/') + '/api/telegram/webhook'
            r = await http.post(f"{bot_api}/setWebhook", json={
                "url": webhook_url, "allowed_updates": ["message"]
            })
            results["webhook"] = r.json()
    return results


# ============== App Setup ==============

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    logger.info("Binance Claw Quiz starting...")
    await db.sessions.create_index("code", unique=True)
    await db.sessions.create_index("slug")
    await db.players.create_index([("session_code", 1), ("player_id", 1)])
    await db.quizzes.create_index("quiz_id", unique=True)

    if TELEGRAM_BOT_TOKEN and FRONTEND_URL:
        try:
            bot_api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
            async with httpx.AsyncClient() as http:
                await http.post(f"{bot_api}/setMyCommands", json={
                    "commands": [
                        {"command": "start", "description": "Start Binance Claw Quiz"},
                        {"command": "quiz", "description": "Create a quiz"},
                        {"command": "join", "description": "Join a game"}
                    ]
                })
                await http.post(f"{bot_api}/setChatMenuButton", json={
                    "menu_button": {"type": "web_app", "text": "Claw Quiz", "web_app": {"url": FRONTEND_URL}}
                })
                webhook_url = FRONTEND_URL.rstrip('/') + '/api/telegram/webhook'
                await http.post(f"{bot_api}/setWebhook", json={
                    "url": webhook_url, "allowed_updates": ["message"]
                })
            logger.info("Telegram bot configured")
        except Exception as e:
            logger.error(f"Telegram setup error: {e}")
    logger.info("Binance Claw Quiz ready!")

@app.on_event("shutdown")
async def shutdown():
    for game in active_games.values():
        if game.get("timer_task"):
            game["timer_task"].cancel()
    mongo_client.close()
