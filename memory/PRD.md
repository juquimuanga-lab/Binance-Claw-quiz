# Binance Claw Quiz - Fun Crypto Quiz Telegram Mini App

## Architecture
- **Frontend**: React + Tailwind CSS + Framer Motion + Telegram Web App SDK + canvas-confetti
- **Backend**: FastAPI + MongoDB Atlas + WebSocket
- **AI**: OpenAI GPT-4o via Emergent LLM Key
- **Content**: Binance Academy scraping + LLM fallback
- **Bot**: Telegram Bot API
- **Deployment**: Render.com (backend web service + frontend static site) + MongoDB Atlas free tier

## Render Deployment
- Backend: https://binance-claw-quiz-api.onrender.com (srv-d6rgeh24d50c73btfu1g)
- Frontend: https://binance-claw-quiz-app.onrender.com (srv-d6rgelhaae7s739veq1g)
- MongoDB Atlas: ClawQuizCluster (Project: 69b702ec58ef22e29e238157)

## What's Been Implemented
- Full quiz platform: Host, Join, Solo modes
- Real-time multiplayer via WebSocket
- AI quiz generation from Binance Academy content
- High-entropy join codes (>=32 bits)
- Per-session leaderboards
- Telegram Mini App integration
- "How to Play" in-app guide with tabbed sections (Host/Join/Solo), scoring, tips
- Confetti celebration effect on quiz completion (both multiplayer and solo)
- Deployed to Render + MongoDB Atlas
- Removed Emergent branding, clean production build

## Backlog
- P0: WebSocket reconnection
- P1: Sound effects, animated timer, Telegram inline share
- P2: Quiz history, custom duration, multi-language
