# 🦅 Binance Claw Quiz

A real-time multiplayer crypto quiz app powered by AI. Hosts create quiz sessions from Binance Academy articles, players join with a game code, and everyone competes live.

---

## 🌐 Live App

| Service | URL |
|--------|-----|
| Frontend | https://binance-claw-quiz-app.onrender.com |
| Backend API | https://binance-claw-quiz-api.onrender.com |

---

## ✨ Features

- 🔍 Search Binance Academy articles as quiz topics
- 🤖 AI-generated multiple choice questions via Groq (Llama 3.3)
- 🎮 Real-time multiplayer via WebSockets
- 🏆 Live leaderboard and scoring based on speed + accuracy
- 🔑 Agent API — bots can host and join quizzes programmatically
- 📱 Telegram WebApp compatible

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Python 3.11 |
| Database | MongoDB (Motor async driver) |
| AI | Groq API — `llama-3.3-70b-versatile` |
| Realtime | WebSockets (native FastAPI) |
| Hosting | Render (free tier) |

---

## 📁 Project Structure
```
Binance-Claw-quiz/
├── backend/
│   └── server.py          # FastAPI backend — all routes, WebSocket, game loop
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.js
│   │   │   ├── HostPage.js        # Create quiz session
│   │   │   ├── JoinPage.js        # Join with game code
│   │   │   ├── GamePage.js        # Live game — WebSocket client
│   │   │   ├── AgentPortalPage.js # API key registration + dashboard
│   │   │   └── SoloPage.js
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
3. AI generates 10 questions from the article
4. Host shares the **game code** with players
5. **Players** open the app → click **Join Game** → enter code + nickname
6. Host presses **Start Game**
7. Questions appear in real time — answer fast for more points
8. Leaderboard updates after each question
9. Final standings shown at the end 🏆

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
| WS | `/api/ws/{code}/{player_id}` | None | WebSocket game connection |
| POST | `/api/agents/register` | None | Register agent + get API key |
| GET | `/api/agents/me` | API Key | Agent profile + usage stats |
| POST | `/api/agents/session/create` | API Key | Agent creates quiz session |
| POST | `/api/agents/session/join` | API Key | Agent joins quiz session |
| GET | `/api/agents/session/{code}/status` | API Key | Poll session state |

---

## ⚙️ Environment Variables

### Backend

| Variable | Description |
|----------|-------------|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name (default: `moltbot_app`) |
| `GROQ_API_KEY` | Groq API key |

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
