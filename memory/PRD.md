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
- **Theme**: Dark crypto aesthetic with Binance yellow (#F3BA2F), cyber cyan (#00F0FF), neon green (#00FF29)

## What's Been Implemented (2026-03-12)
### Backend
- Binance Academy search + article scraping (with LLM fallback)
- Quiz generation via GPT-4o (emergentintegrations library)
- Session management (create/join with high-entropy codes ≥32 bits)
- WebSocket game engine (timer, scoring, per-session leaderboards)
- Telegram bot setup (commands, menu button, webhook)
- Solo quiz endpoint

### Frontend
- HomePage: Logo + Host/Join/Solo mode selection
- HostPage: Search → Select Article → Generate Quiz → Create Session
- JoinPage: Enter code + nickname to join
- GamePage: Lobby (with logo) → Questions → Results → Final Standings (with logo)
- SoloPage: Search → Generate → Play → Results
- Telegram Web App SDK integration
- Mobile-first design

### Telegram Bot
- Token configured
- Commands: /start, /quiz, /join
- Menu button "Claw Quiz" opens Mini App
- Webhook for message handling

## Testing Status
- Backend: 100%
- Frontend: 90%

## Prioritized Backlog
### P0
- Optimize article fetching speed
- WebSocket reconnection handling

### P1
- Sound effects, animated timer, Telegram inline share

### P2
- Quiz history, custom duration, multi-language, bookmarking
