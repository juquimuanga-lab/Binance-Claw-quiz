# Binance Claw Quiz - Kahoot-Style Crypto Quiz Telegram Mini App

## Original Problem Statement
Transform the MoltBot/OpenClaw installation into a Kahoot.it-style quiz Telegram Mini App called "Binance Claw Quiz" where all quiz questions, articles, and content come from Binance Academy (binance.com/en/academy). Supports real-time multiplayer and single-player modes with per-session leaderboards.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Framer Motion + Telegram Web App SDK
- **Backend**: FastAPI + MongoDB (Motor async driver)
- **Real-time**: WebSocket for multiplayer quiz game engine
- **AI**: OpenAI GPT-4o via Emergent LLM Key for quiz generation
- **Content**: Binance Academy scraping + LLM fallback for article content
- **Bot**: Telegram Bot API for Mini App integration

## Branding
- **App Name**: Binance Claw Quiz
- **Logo**: Custom emblem with claw/quiz motifs in gold/black/blue
- **Telegram Bot**: Commands updated to "Start Binance Claw Quiz"

## What's Been Implemented (2026-03-12)
### Backend
- Binance Academy search + article scraping (with LLM fallback)
- Reduced timeouts (10s scrape → fast LLM fallback)
- Quiz generation via GPT-4o
- Session management (high-entropy codes ≥32 bits)
- WebSocket game engine (timer, scoring, per-session leaderboards)
- Telegram bot setup (commands, menu button, webhook)
- Solo quiz endpoint

### Frontend
- HomePage: Logo + Host/Join/Solo mode selection
- HostPage: Search → Select → Generate (with progress + cancel)
- JoinPage: Enter code + nickname
- GamePage: Lobby (with logo) → Questions → Results → Final Standings
- SoloPage: Search → Generate → Play → Results
- AbortController timeouts on all API calls
- Cancel buttons during long operations

### Bug Fixes (2026-03-12)
- Fixed /start message: CryptoQuiz → Binance Claw Quiz
- Fixed host page sticking: Added progress indicators, cancel buttons, AbortController timeouts
- Reduced backend scrape timeout from 20s to 10s
- Reduced LLM content generation prompt (400 words vs 800)

## Testing Status
- Backend: 100%
- Frontend: 95%

## Deployment Notes
- Emergent Native Deployment recommended (50 credits/month, 24/7 uptime)
- Vercel not ideal: WebSocket not supported in serverless, FastAPI needs modifications
- If Vercel needed: Save to GitHub → deploy frontend separately, backend needs Railway/Render

## Prioritized Backlog
### P0
- WebSocket reconnection handling
### P1
- Sound effects, animated timer, Telegram inline share
### P2
- Quiz history, custom duration, multi-language
