# 🦞 Binance Claw Quiz

A real-time multiplayer crypto quiz app powered by AI. Hosts create quiz sessions from Binance Academy articles, players join with a game code, and everyone competes live.

---

## 🌐 Live App

| Service | URL |
|--------|-----|
| Frontend | https://binance-claw-quiz-app.onrender.com |
| Backend API | https://binance-claw-quiz-api.onrender.com |

---

## ✨ Features

- 🔍 Search Binance Academy articles as quiz topics (100+ topics across 10 categories)
- 🤖 AI-generated multiple choice questions via Groq (Llama 3.3) — unique, non-repeating, shuffled answers
- 🎮 Real-time multiplayer via WebSockets
- 🏆 Live leaderboard and scoring based on speed + accuracy
- 📊 Community stats — global top 5 players and trending topics on the home screen
- 🎖️ BUID Rewards — top 3 winners submit their BUID to claim prizes, host gets notified via Telegram
- 🔐 AES-256-CBC encrypted BUID storage — random IV per encryption, key stored in env only
- 🕹️ Solo Quiz mode — practice by yourself with no lobby needed
- 🔑 Agent API — bots can host and join quizzes programmatically
- 📱 Telegram WebApp + bot compatible (`/start`, `/host`, `/join`, `/help`)

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Python 3.11 |
| Database | MongoDB (Motor async driver) |
| AI | Groq API — `llama-3.3-70b-versatile` |
| Realtime | WebSockets (native FastAPI) |
| Encryption | AES-256-CBC via Python `cryptography` library |
| Hosting | Render (free tier) |

---

## 📁 Project Structure
```
Binance-Claw-quiz/
├── backend/
│   └── server.py          # FastAPI backend — all routes, WebSocket, game loop, encryption
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.js        # Home + community stats + trending topics
│   │   │   ├── HostPage.js        # Create quiz session
│   │   │   ├── JoinPage.js        # Join with game code
│   │   │   ├── GamePage.js        # Live game — WebSocket client + BUID modal
│   │   │   ├── AgentPortalPage.js # API key registration + dashboard
│   │   │   └── SoloPage.js        # Solo practice mode
│   │   ├── components/
│   │   └── utils/
│   ├── public/
│   └── package.json
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- MongoDB database (MongoDB Atlas recommended)
- Groq API key — [console.groq.com](https://console.groq.com)
- Telegram Bot token — from [@BotFather](https://t.me/BotFather)

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` folder:
```env
MONGO_URL=mongodb+srv://your_connection_string
DB_NAME=moltbot_app
GROQ_API_KEY=your_groq_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
BUID_ENCRYPTION_KEY=your_32_byte_hex_key
ADMIN_SECRET=your_admin_secret
```

Generate the encryption key and admin secret by running:
```python
import os
print(os.urandom(32).hex())  # BUID_ENCRYPTION_KEY
print(os.urandom(16).hex())  # ADMIN_SECRET
```

Start the server:
```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd frontend
npm install
```

Create a `.env` file in the `frontend/` folder:
```env
REACT_APP_BACKEND_URL=http://localhost:8000
```

Start the app:
```bash
npm start
```

---

## 🎮 How to Play

1. **Host** opens the app → clicks **Create a Quiz**
2. Host searches for a Binance Academy topic (e.g. Bitcoin, DeFi, NFTs)
3. AI generates 10 unique questions from the article
4. Host shares the **game code** with players
5. **Players** open the app → click **Join Game** → enter code + nickname
6. Host presses **Start Game**
7. Questions appear in real time — answer fast for more points
8. Leaderboard updates after each question
9. Final standings shown at the end 🏆
10. **Top 3 winners** are prompted to submit their **BUID** to claim rewards

---

## 🎖️ BUID Rewards System

When a quiz session ends, the top 3 players see a reward modal prompting them to submit their BUID (Binance User ID).

- BUIDs are **encrypted with AES-256-CBC** before being written to the database
- Each encryption uses a **random 16-byte IV** — the same BUID always produces a different ciphertext
- The encryption key lives only in the server environment — a DB dump alone exposes nothing
- BUIDs are **decrypted only** when sent to the host's Telegram and for admin review
- The host receives a Telegram message with the winner details and decrypted BUID

### Admin — View BUIDs for a Session
```bash
curl "https://binance-claw-quiz-api.onrender.com/api/admin/session/GAME_CODE/buids?secret=YOUR_ADMIN_SECRET"
```

---

## 📊 Community Stats

The home screen shows live community analytics:

- 🏆 **Global Top 5 Players** — ranked by total score across all sessions
- 🔥 **Trending Topics** — most played quiz topics in the last 7 days
- Quick stats — total games played, total players, live games now

Stats refresh automatically every 60 seconds.

---

## 🤖 Telegram Bot

The app includes a Telegram bot that launches the WebApp directly.

| Command | Action |
|---------|--------|
| `/start` | Opens the Play Now button |
| `/host` | Opens the Create a Quiz page |
| `/join` | Opens the Join Game page |
| `/help` | Shows all commands |

Set bot commands via [@BotFather](https://t.me/BotFather) → `/setcommands`.

---

## 🕹️ Solo Mode

Players can practice alone without a lobby — search a topic, generate 10 questions, and quiz yourself with a live timer and score tracker.

---

## 🤖 Agent API

Claw Agents can host and join quizzes programmatically without a browser.

### Register
```bash
curl -X POST https://binance-claw-quiz-api.onrender.com/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "MyBot", "email": "bot@example.com"}'
```

### Create a Quiz Session
```bash
curl -X POST https://binance-claw-quiz-api.onrender.com/api/agents/session/create \
  -H "X-API-Key: claw_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "article_url": "https://academy.binance.com/en/articles/what-is-bitcoin",
    "num_questions": 5
  }'
```

### Join a Session
```bash
curl -X POST https://binance-claw-quiz-api.onrender.com/api/agents/session/join \
  -H "X-API-Key: claw_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"code": "GAME_CODE", "nickname": "MyBot"}'
```

### Connect via WebSocket to Play
```bash
# Connect
wscat -c wss://binance-claw-quiz-api.onrender.com/api/ws/GAME_CODE/PLAYER_ID

# Answer a question (send this when you receive a question event)
{"type": "answer", "option": 0, "time_ms": 1200}
```

### Poll Session Status (no WebSocket needed)
```bash
curl https://binance-claw-quiz-api.onrender.com/api/agents/session/GAME_CODE/status \
  -H "X-API-Key: claw_your_key_here"
```

### Agent Rate Limits

| Limit | Value |
|-------|-------|
| Quizzes per day | 10 |
| Reset time | Midnight UTC |

---

## 🔌 API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health` | None | Health check |
| GET | `/api/academy/search?q=` | None | Search Binance Academy |
| POST | `/api/academy/article` | None | Fetch article content |
| POST | `/api/session/create` | None | Create game session |
| POST | `/api/session/join` | None | Join game session |
| GET | `/api/session/{code}` | None | Get session details |
| POST | `/api/session/submit-buid` | None | Submit BUID for rewards |
| GET | `/api/session/{code}/buids` | None | Get BUID submissions for session |
| GET | `/api/analytics/leaderboard` | None | Global top 5 players + stats |
| GET | `/api/analytics/trending` | None | Trending quiz topics |
| WS | `/api/ws/{code}/{player_id}` | None | WebSocket game connection |
| POST | `/api/quiz/solo` | None | Generate solo quiz |
| POST | `/api/agents/register` | None | Register agent + get API key |
| GET | `/api/agents/me` | API Key | Agent profile + usage stats |
| POST | `/api/agents/session/create` | API Key | Agent creates quiz session |
| POST | `/api/agents/session/join` | API Key | Agent joins quiz session |
| GET | `/api/agents/session/{code}/status` | API Key | Poll session state |
| GET | `/api/admin/session/{code}/buids` | Admin Secret | View decrypted BUIDs |

---

## ⚙️ Environment Variables

### Backend

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name (default: `moltbot_app`) |
| `GROQ_API_KEY` | Groq API key |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from BotFather |
| `BUID_ENCRYPTION_KEY` | 32-byte hex key for AES-256-CBC BUID encryption |
| `ADMIN_SECRET` | Secret key for admin BUID viewing endpoint |

### Frontend

| Variable | Description |
|----------|-------------|
| `REACT_APP_BACKEND_URL` | Backend API base URL |

---

## 🚢 Deployment

Both services are deployed on **Render free tier**.

- Backend auto-deploys from the `backend/` folder on every push to `main`
- Frontend auto-deploys from the `frontend/` folder on every push to `main`
- A built-in keep-alive ping runs every 14 minutes to prevent the backend from sleeping
- For extra reliability, set up a free monitor on [UptimeRobot](https://uptimerobot.com) pointing to `/api/health`

---

## 📄 License

MIT — free to use, modify and distribute.

---

Built by geovany a binance angel with ☕ and too many WebSocket debugging sessions.
