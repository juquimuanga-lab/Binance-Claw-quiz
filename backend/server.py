from fastapi import FastAPI, Query, Request, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import Response
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
import os
import logging
import json
import secrets
import httpx
import re
import datetime
import asyncio
import random
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Optional
from bs4 import BeautifulSoup
from groq import Groq
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ================= INIT =================

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ.get('DB_NAME', 'moltbot_app')]

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
groq_client = Groq(api_key=GROQ_API_KEY)
GROQ_MODEL = "llama-3.3-70b-versatile"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
WEBAPP_URL = "https://binance-claw-quiz-app.onrender.com"

DAILY_QUIZ_LIMIT = 10

# ================= ANALYTICS ROUTES =================

@app.get("/api/analytics/leaderboard")
async def global_leaderboard():
    try:
        # Aggregate top players across all finished sessions
        pipeline = [
            {"$match": {"status": "finished"}},
            {"$unwind": "$players"},
            {"$match": {"players.player_id": {"$not": re.compile("^host_")}}},
            {"$group": {
                "_id": "$players.nickname",
                "total_score": {"$sum": "$players.score"},
                "games_played": {"$sum": 1},
                "best_score": {"$max": "$players.score"},
            }},
            {"$sort": {"total_score": -1}},
            {"$limit": 5},
            {"$project": {
                "_id": 0,
                "nickname": "$_id",
                "total_score": 1,
                "games_played": 1,
                "best_score": 1,
            }}
        ]
        top_players = await db.sessions.aggregate(pipeline).to_list(5)

        # Overall stats
        total_sessions = await db.sessions.count_documents({"status": "finished"})
        total_active = await db.sessions.count_documents({"status": "playing"})

        # Total unique players
        player_pipeline = [
            {"$match": {"status": "finished"}},
            {"$unwind": "$players"},
            {"$match": {"players.player_id": {"$not": re.compile("^host_")}}},
            {"$count": "total"}
        ]
        player_result = await db.sessions.aggregate(player_pipeline).to_list(1)
        total_players = player_result[0]["total"] if player_result else 0

        return {
            "top_players": top_players,
            "stats": {
                "total_games": total_sessions,
                "active_games": total_active,
                "total_players": total_players,
            }
        }
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        return {"top_players": [], "stats": {"total_games": 0, "active_games": 0, "total_players": 0}}


@app.get("/api/analytics/trending")
async def trending_topics():
    try:
        # Top topics by number of sessions created in last 7 days
        seven_days_ago = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

        pipeline = [
            {"$match": {"created_date": {"$gte": seven_days_ago}}},
            {"$group": {
                "_id": "$article_title",
                "count": {"$sum": 1},
                "article_url": {"$first": "$article_url"},
            }},
            {"$sort": {"count": -1}},
            {"$limit": 5},
            {"$project": {
                "_id": 0,
                "title": "$_id",
                "count": 1,
                "article_url": 1,
            }}
        ]
        trending = await db.sessions.aggregate(pipeline).to_list(5)

        # Fallback if not enough data yet
        if not trending:
            trending = [
                {"title": "Bitcoin", "count": 0, "article_url": "https://academy.binance.com/en/articles/what-is-bitcoin"},
                {"title": "Ethereum", "count": 0, "article_url": "https://academy.binance.com/en/articles/what-is-ethereum"},
                {"title": "DeFi", "count": 0, "article_url": "https://academy.binance.com/en/articles/what-is-defi"},
                {"title": "NFTs", "count": 0, "article_url": "https://academy.binance.com/en/articles/what-are-nfts"},
                {"title": "Web3", "count": 0, "article_url": "https://academy.binance.com/en/articles/what-is-web3"},
            ]

        return {"trending": trending}
    except Exception as e:
        logger.error(f"Trending error: {e}")
        return {"trending": []}
        
# ================= TELEGRAM BOT =================

tg_bot = None
if TELEGRAM_BOT_TOKEN:
    tg_bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

    @tg_bot.message_handler(commands=['start'])
    def tg_start(message):
        name = message.from_user.first_name or "Player"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            text="🎮 Play Now",
            web_app=WebAppInfo(url=WEBAPP_URL)
        ))
        tg_bot.send_message(
            message.chat.id,
            f"👋 Welcome {name}!\n\n"
            f"🦞 *Binance Claw Quiz*\n\n"
            f"Test your crypto knowledge with AI-generated quizzes from Binance Academy.\n\n"
            f"• 🏆 Compete with friends in real-time\n"
            f"• 🤖 AI-powered questions\n"
            f"• ⚡ Score points based on speed\n\n"
            f"Press *Play Now* to start! 👇",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    @tg_bot.message_handler(commands=['host'])
    def tg_host(message):
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            text="🎯 Create a Quiz",
            web_app=WebAppInfo(url=f"{WEBAPP_URL}/host")
        ))
        tg_bot.send_message(
            message.chat.id,
            "🎯 *Host a Quiz*\n\nSearch Binance Academy, pick a topic, and challenge your friends!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    @tg_bot.message_handler(commands=['join'])
    def tg_join(message):
        parts = message.text.split()
        code = parts[1].upper() if len(parts) > 1 else ""
        url = f"{WEBAPP_URL}/join?code={code}" if code else f"{WEBAPP_URL}/join"
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            text="🚀 Join Game",
            web_app=WebAppInfo(url=url)
        ))
        tg_bot.send_message(
            message.chat.id,
            f"🚀 *Join a Game*\n\nPress Join Game below!",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    @tg_bot.message_handler(commands=['help'])
    def tg_help(message):
        tg_bot.send_message(
            message.chat.id,
            "🦅 *Binance Claw Quiz — Commands*\n\n"
            "/start — Launch the app\n"
            "/host — Create a new quiz session\n"
            "/join — Join a game (e.g. /join ABC123)\n"
            "/help — Show this message",
            parse_mode="Markdown"
        )

# ================= KEEP ALIVE =================

async def keep_alive():
    await asyncio.sleep(60)
    while True:
        try:
            async with httpx.AsyncClient() as client:
                await client.get(
                    "https://binance-claw-quiz-api.onrender.com/api/health",
                    timeout=10
                )
                logger.info("Keep-alive ping sent")
        except Exception as e:
            logger.warning(f"Keep-alive failed: {e}")
        await asyncio.sleep(14 * 60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if TELEGRAM_BOT_TOKEN:
        try:
            async with httpx.AsyncClient() as client:
                webhook_url = f"https://binance-claw-quiz-api.onrender.com/webhook/{TELEGRAM_BOT_TOKEN}"
                await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                    json={"url": webhook_url}
                )
            logger.info("Telegram webhook set successfully")
        except Exception as e:
            logger.error(f"Failed to set webhook: {e}")
    asyncio.create_task(keep_alive())
    yield

app = FastAPI(lifespan=lifespan)

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

# ================= API KEY AUTH =================

async def get_agent(x_api_key: Optional[str] = Header(None)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    agent = await db.agents.find_one({"api_key": x_api_key, "active": True})
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    return agent

async def check_daily_limit(agent: dict):
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    count = await db.sessions.count_documents({
        "created_by": str(agent["_id"]),
        "created_date": today,
    })
    if count >= DAILY_QUIZ_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Daily quiz limit of {DAILY_QUIZ_LIMIT} reached. Resets at midnight UTC."
        )

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

class AgentRegisterRequest(BaseModel):
    agent_name: str
    email: str

class AgentJoinRequest(BaseModel):
    code: str
    nickname: str

# ================= ARTICLE LIBRARY =================

ARTICLE_LIBRARY = {
    # ── BASICS ──
    "bitcoin": "what-is-bitcoin",
    "ethereum": "what-is-ethereum",
    "blockchain": "what-is-blockchain",
    "cryptocurrency": "what-is-cryptocurrency",
    "crypto": "what-is-cryptocurrency",
    "binance": "what-is-binance",
    "bnb": "what-is-bnb",

    # ── DEFI ──
    "defi": "what-is-defi",
    "decentralized finance": "what-is-defi",
    "yield farming": "what-is-yield-farming",
    "liquidity pool": "what-is-liquidity-pool",
    "amm": "what-is-an-automated-market-maker-amm",
    "automated market maker": "what-is-an-automated-market-maker-amm",
    "dex": "what-is-a-decentralized-exchange-dex",
    "decentralized exchange": "what-is-a-decentralized-exchange-dex",
    "uniswap": "what-is-uniswap-and-how-does-it-work",
    "pancakeswap": "what-is-pancakeswap-and-how-does-it-work",
    "flash loan": "what-are-flash-loans",
    "lending": "what-is-crypto-lending",
    "impermanent loss": "impermanent-loss-explained",
    "tvl": "what-is-total-value-locked-tvl",

    # ── NFT & WEB3 ──
    "nft": "what-are-nfts",
    "non fungible token": "what-are-nfts",
    "web3": "what-is-web3",
    "metaverse": "what-is-the-metaverse",
    "gamefi": "what-is-gamefi-and-how-does-it-work",
    "play to earn": "what-is-gamefi-and-how-does-it-work",
    "dao": "decentralized-autonomous-organizations-daos-explained",
    "opensea": "what-is-opensea",
    "mint": "what-does-minting-mean-in-crypto",
    "minting": "what-does-minting-mean-in-crypto",

    # ── LAYER 1 & LAYER 2 ──
    "solana": "what-is-solana-sol",
    "sol": "what-is-solana-sol",
    "cardano": "what-is-cardano",
    "ada": "what-is-cardano",
    "polkadot": "what-is-polkadot-dot",
    "dot": "what-is-polkadot-dot",
    "avalanche": "what-is-avalanche-avax",
    "avax": "what-is-avalanche-avax",
    "polygon": "what-is-polygon-matic",
    "matic": "what-is-polygon-matic",
    "layer 2": "what-is-a-layer-2-blockchain",
    "layer2": "what-is-a-layer-2-blockchain",
    "rollup": "what-are-rollups",
    "zk rollup": "what-are-zk-rollups",
    "zero knowledge": "what-is-zero-knowledge-proof",
    "arbitrum": "what-is-arbitrum",
    "optimism": "what-is-optimism",
    "lightning network": "what-is-the-lightning-network",
    "bnb chain": "what-is-bnb-chain",
    "bsc": "what-is-bnb-chain",

    # ── TRADING ──
    "trading": "a-complete-guide-to-cryptocurrency-trading-for-beginners",
    "spot trading": "spot-trading-explained",
    "futures": "what-are-futures",
    "futures trading": "what-are-futures",
    "margin trading": "what-is-margin-trading",
    "leverage": "what-is-margin-trading",
    "technical analysis": "a-complete-guide-to-cryptocurrency-technical-analysis",
    "candlestick": "a-beginners-guide-to-candlestick-charts",
    "chart": "a-beginners-guide-to-candlestick-charts",
    "moving average": "moving-averages-explained",
    "rsi": "what-is-the-rsi-indicator",
    "macd": "macd-indicator-explained",
    "bollinger": "what-are-bollinger-bands",
    "order book": "what-is-an-order-book",
    "limit order": "what-is-a-limit-order",
    "stop loss": "what-is-a-stop-loss-order",
    "dollar cost averaging": "what-is-dollar-cost-averaging-dca",
    "dca": "what-is-dollar-cost-averaging-dca",
    "risk management": "a-beginners-guide-to-understanding-risk-management",
    "short selling": "what-is-short-selling-in-crypto",
    "liquidation": "what-is-liquidation-in-crypto",

    # ── STAKING & EARNING ──
    "staking": "what-is-staking",
    "proof of stake": "proof-of-stake-explained",
    "pos": "proof-of-stake-explained",
    "validator": "what-is-a-validator",
    "earn": "binance-earn-explained",
    "launchpool": "what-is-binance-launchpool",
    "launchpad": "what-is-binance-launchpad",
    "ieo": "what-is-an-initial-exchange-offering-ieo",

    # ── CONSENSUS & TECH ──
    "proof of work": "proof-of-work-explained",
    "pow": "proof-of-work-explained",
    "mining": "what-is-cryptocurrency-mining",
    "hash": "what-is-hashing",
    "hashing": "what-is-hashing",
    "smart contract": "what-are-smart-contracts",
    "smart contracts": "what-are-smart-contracts",
    "oracle": "blockchain-oracles-explained",
    "chainlink": "what-is-chainlink-link",
    "consensus": "what-is-a-consensus-mechanism",
    "merkle tree": "what-is-a-merkle-tree",
    "gas": "what-is-gas-in-ethereum",
    "gas fees": "what-is-gas-in-ethereum",
    "evm": "what-is-ethereum-virtual-machine-evm",
    "token": "what-is-a-token",
    "tokenomics": "what-is-tokenomics",
    "erc20": "what-is-erc-20",
    "erc721": "what-is-erc-721",

    # ── WALLETS & SECURITY ──
    "wallet": "crypto-wallet-types-explained",
    "crypto wallet": "crypto-wallet-types-explained",
    "hardware wallet": "what-is-a-hardware-wallet",
    "seed phrase": "what-is-a-seed-phrase",
    "private key": "what-is-a-private-key",
    "public key": "what-is-a-public-key",
    "security": "how-to-stay-safe-in-crypto",
    "phishing": "what-is-a-phishing-attack",
    "scam": "common-crypto-scams-and-how-to-avoid-them",
    "rug pull": "what-is-a-rug-pull",
    "two factor": "what-is-two-factor-authentication-2fa",
    "2fa": "what-is-two-factor-authentication-2fa",
    "kyc": "what-is-kyc",
    "custodial": "custodial-vs-non-custodial-wallets",
    "non custodial": "custodial-vs-non-custodial-wallets",

    # ── STABLECOINS ──
    "stablecoin": "what-are-stablecoins",
    "stable coin": "what-are-stablecoins",
    "usdt": "what-is-tether-usdt",
    "tether": "what-is-tether-usdt",
    "usdc": "what-is-usd-coin-usdc",
    "algorithmic stablecoin": "what-are-algorithmic-stablecoins",
    "terra": "what-is-terra-luna",
    "luna": "what-is-terra-luna",

    # ── MARKET CONCEPTS ──
    "bull market": "what-is-a-bull-market",
    "bear market": "what-is-a-bear-market",
    "market cap": "what-is-market-capitalization",
    "market capitalization": "what-is-market-capitalization",
    "volume": "what-is-trading-volume",
    "volatility": "what-is-volatility",
    "hodl": "what-does-hodl-mean",
    "fomo": "what-is-fomo",
    "fud": "what-is-fud",
    "pump and dump": "what-is-a-pump-and-dump-scheme",
    "whale": "who-are-crypto-whales",
    "altcoin": "what-is-an-altcoin",
    "memecoin": "what-are-meme-coins",
    "dogecoin": "what-is-dogecoin-doge",
    "doge": "what-is-dogecoin-doge",
    "shiba": "what-is-shiba-inu-shib",
    "halving": "bitcoin-halving-explained",
    "bitcoin halving": "bitcoin-halving-explained",
    "dominance": "what-is-bitcoin-dominance",

    # ── REGULATION & MACRO ──
    "regulation": "what-is-crypto-regulation",
    "cbdc": "what-is-a-cbdc",
    "central bank digital currency": "what-is-a-cbdc",
    "tax": "crypto-taxes-explained",
    "crypto tax": "crypto-taxes-explained",
    "etf": "what-is-a-bitcoin-etf",
    "bitcoin etf": "what-is-a-bitcoin-etf",

    # ── ADVANCED ──
    "cross chain": "what-is-cross-chain",
    "bridge": "what-is-a-blockchain-bridge",
    "interoperability": "blockchain-interoperability-explained",
    "cosmos": "what-is-cosmos",
    "atom": "what-is-cosmos",
    "derivatives": "what-are-crypto-derivatives",
    "options": "what-are-crypto-options",
    "perpetual": "what-are-perpetual-futures-contracts",
    "funding rate": "what-is-a-funding-rate",
    "copy trading": "what-is-copy-trading",
    "arbitrage": "what-is-arbitrage",
    "on chain": "what-is-on-chain-analysis",
    "tokenization": "what-is-asset-tokenization",
    "rwa": "what-is-asset-tokenization",
    "real world asset": "what-is-asset-tokenization",
    "ai crypto": "ai-and-crypto-explained",
    "artificial intelligence": "ai-and-crypto-explained",
    "soulbound": "what-are-soulbound-tokens",
    "sbt": "what-are-soulbound-tokens",
}

# ================= SEARCH =================

async def search_binance_academy(query: str) -> list:
    query_lower = query.lower().strip()
    results = []
    seen_slugs = set()

    for keyword, slug in ARTICLE_LIBRARY.items():
        if keyword in query_lower and slug not in seen_slugs:
            results.append({
                "title": keyword.replace("-", " ").title(),
                "url": f"https://academy.binance.com/en/articles/{slug}"
            })
            seen_slugs.add(slug)

    if not results:
        popular = [
            ("Bitcoin", "what-is-bitcoin"),
            ("Ethereum", "what-is-ethereum"),
            ("DeFi", "what-is-defi"),
            ("NFTs", "what-are-nfts"),
            ("Staking", "what-is-staking"),
            ("Blockchain", "what-is-blockchain"),
            ("Web3", "what-is-web3"),
            ("Trading", "a-complete-guide-to-cryptocurrency-trading-for-beginners"),
            ("Smart Contracts", "what-are-smart-contracts"),
            ("Stablecoins", "what-are-stablecoins"),
        ]
        for title, slug in popular:
            results.append({
                "title": title,
                "url": f"https://academy.binance.com/en/articles/{slug}"
            })

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
        summary = groq_complete(
            f"Summarize this crypto article in 200 words:\n\n{content[:4000]}"
        )

        quiz_prompt = f"""
You are a crypto quiz generator. Generate exactly {num} UNIQUE multiple choice questions.

STRICT RULES:
- Every question must be about a DIFFERENT aspect of the topic
- No two questions can ask the same thing in different words
- Questions must vary in difficulty: mix easy, medium and hard
- Wrong answer options must be plausible but clearly incorrect
- Never repeat the same wrong answer across questions
- Cover different angles: definitions, how it works, use cases, history, risks, comparisons
- Return JSON only, no markdown, no backticks, no text outside the array

Format:
[
 {{
  "question": "...",
  "options": ["correct answer", "wrong1", "wrong2", "wrong3"],
  "correct": 0,
  "explanation": "...",
  "difficulty": "easy|medium|hard"
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

        # Deduplicate by question text
        seen_questions = set()
        unique_questions = []
        for q in questions:
            q_text = q.get("question", "").lower().strip()
            if q_text and q_text not in seen_questions:
                seen_questions.add(q_text)
                unique_questions.append(q)

        # Shuffle answer options so correct answer isn't always first
        for q in unique_questions:
            options = q.get("options", [])
            correct_answer = options[q.get("correct", 0)] if options else None
            if correct_answer and len(options) == 4:
                random.shuffle(options)
                q["options"] = options
                q["correct"] = options.index(correct_answer)

        return unique_questions[:num]

    except Exception as e:
        logger.error(f"Quiz generation error: {e}")
        return [
            {
                "question": f"What is {title}?",
                "options": ["A blockchain concept", "A type of food", "A car brand", "A video game"],
                "correct": 0,
                "explanation": f"{title} is a concept in the crypto space.",
                "difficulty": "easy"
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
                state["waiting_for_next"] = True
                logger.info(f"Waiting for host next_question signal Q{i+1}/{total}")
                for _ in range(60):
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

# ================= STANDARD ROUTES =================

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

@app.post("/api/quiz/solo")
async def solo_quiz(req: GenerateQuizRequest):
    try:
        if not req.article_content:
            article = await fetch_article_content(req.article_url)
            title = article["title"]
            content = article["content"]
        else:
            title = req.article_title or "Crypto Quiz"
            content = req.article_content

        questions = await generate_quiz_questions(title, content, req.num_questions)

        return {
            "article_title": title,
            "questions": questions,
        }

    except Exception as e:
        logger.error(f"Solo quiz error: {e}")
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

# ================= AGENT ROUTES =================

@app.post("/api/agents/register")
async def register_agent(req: AgentRegisterRequest):
    existing = await db.agents.find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    api_key = f"claw_{secrets.token_hex(24)}"
    agent_doc = {
        "agent_name": req.agent_name,
        "email": req.email,
        "api_key": api_key,
        "active": True,
        "daily_limit": DAILY_QUIZ_LIMIT,
        "created_at": str(datetime.datetime.utcnow()),
    }

    await db.agents.insert_one(agent_doc)
    agent_doc.pop("_id", None)

    return {
        "message": "Agent registered successfully",
        "agent_name": req.agent_name,
        "api_key": api_key,
        "daily_quiz_limit": DAILY_QUIZ_LIMIT,
        "note": "Store your API key safely — it will not be shown again."
    }

@app.get("/api/agents/me")
async def get_agent_profile(x_api_key: Optional[str] = Header(None)):
    agent = await get_agent(x_api_key)
    today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    quizzes_today = await db.sessions.count_documents({
        "created_by": str(agent["_id"]),
        "created_date": today,
    })

    history = await db.sessions.find(
        {"created_by": str(agent["_id"])},
        {"_id": 0, "questions": 0}
    ).sort("created_at", -1).limit(20).to_list(20)

    return {
        "agent_name": agent["agent_name"],
        "email": agent["email"],
        "active": agent["active"],
        "daily_limit": agent.get("daily_limit", DAILY_QUIZ_LIMIT),
        "quizzes_today": quizzes_today,
        "quizzes_remaining_today": max(0, DAILY_QUIZ_LIMIT - quizzes_today),
        "quiz_history": history,
    }

@app.post("/api/agents/session/create")
async def agent_create_session(
    req: SessionCreateRequest,
    x_api_key: Optional[str] = Header(None)
):
    agent = await get_agent(x_api_key)
    await check_daily_limit(agent)

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
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d")

        session_doc = {
            "code": code,
            "article_title": title,
            "article_url": req.article_url,
            "questions": questions,
            "status": "waiting",
            "players": [],
            "created_by": str(agent["_id"]),
            "created_by_name": agent["agent_name"],
            "created_date": today,
            "created_at": str(datetime.datetime.utcnow()),
        }

        await db.sessions.insert_one(session_doc)
        session_doc.pop("_id", None)

        return {
            **session_doc,
            "join_url": f"https://binance-claw-quiz-app.onrender.com/join?code={code}",
            "websocket_url": f"wss://binance-claw-quiz-api.onrender.com/api/ws/{code}/{{your_player_id}}",
        }

    except Exception as e:
        logger.error(f"Agent session create error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agents/session/join")
async def agent_join_session(
    req: AgentJoinRequest,
    x_api_key: Optional[str] = Header(None)
):
    agent = await get_agent(x_api_key)

    code = req.code.strip().upper()
    session = await db.sessions.find_one({"code": code})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") == "finished":
        raise HTTPException(status_code=400, detail="Session already finished")

    player_id = f"agent_{secrets.token_hex(6)}"
    player = {
        "player_id": player_id,
        "nickname": req.nickname,
        "score": 0,
        "is_agent": True,
        "agent_name": agent["agent_name"],
        "joined_at": str(datetime.datetime.utcnow()),
    }

    await db.sessions.update_one({"code": code}, {"$push": {"players": player}})

    if code in manager.game_state:
        manager.game_state[code]["players"].append(player)

    session.pop("_id", None)

    return {
        "player_id": player_id,
        "code": code,
        "session": session,
        "websocket_url": f"wss://binance-claw-quiz-api.onrender.com/api/ws/{code}/{player_id}",
        "note": "Connect to websocket_url to receive questions in real time."
    }

@app.get("/api/agents/session/{code}/status")
async def agent_session_status(
    code: str,
    x_api_key: Optional[str] = Header(None)
):
    await get_agent(x_api_key)
    session = await db.sessions.find_one({"code": code.upper()})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    state = manager.game_state.get(code.upper(), {})
    session.pop("_id", None)
    session.pop("questions", None)

    current_q = None
    if state.get("current_question", -1) >= 0:
        questions = state.get("questions", [])
        qi = state["current_question"]
        if qi < len(questions):
            q = questions[qi]
            current_q = {
                "index": qi,
                "total": len(questions),
                "question": q["question"],
                "options": q["options"],
            }

    return {
        "code": code.upper(),
        "status": session.get("status"),
        "players": session.get("players", []),
        "current_question": current_q,
        "waiting_for_next": state.get("waiting_for_next", False),
    }

# ================= TELEGRAM WEBHOOK =================

@app.post("/webhook/{token}")
async def telegram_webhook(token: str, request: Request):
    if token != TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not tg_bot:
        raise HTTPException(status_code=500, detail="Bot not configured")
    try:
        json_data = await request.json()
        update = telebot.types.Update.de_json(json_data)
        tg_bot.process_new_updates([update])
        logger.info(f"Telegram update processed: {update.update_id}")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"ok": True}

# ================= WEBSOCKET =================

@app.websocket("/api/ws/{code}/{player_id}")
async def websocket_endpoint(ws: WebSocket, code: str, player_id: str):
    code = code.upper()

    await ws.accept()
    if code not in manager.rooms:
        manager.rooms[code] = {}
    manager.rooms[code][player_id] = ws

    logger.info(f"WS connected: {player_id} -> room {code}")

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
        session = await db.sessions.find_one({"code": code})
        if session:
            await manager.broadcast(code, {
                "type": "player_joined",
                "players": session.get("players", []),
            })

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
                    logger.info(f"Host triggered next question for room {code}")

            elif msg_type == "ping":
                await ws.send_json({"type": "pong"})

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
