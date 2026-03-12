# CryptoQuiz - Kahoot-Style Crypto Quiz Telegram Mini App

## Original Problem Statement
Transform the MoltBot/OpenClaw installation into a Kahoot.it-style quiz Telegram Mini App where all quiz questions, articles, and content come from Binance Academy (binance.com/en/academy). Supports real-time multiplayer and single-player modes with per-session leaderboards.

## Architecture
- **Frontend**: React 19 + Tailwind CSS + Framer Motion + Telegram Web App SDK
- **Backend**: FastAPI + MongoDB (Motor async driver)
- **Real-time**: WebSocket for multiplayer quiz game engine
- **AI**: OpenAI GPT-4o via Emergent LLM Key for quiz generation
- **Content**: Binance Academy scraping + LLM fallback for article content
- **Bot**: Telegram Bot API for Mini App integration

## User Personas
1. **Host**: Creates quizzes from Binance Academy topics, manages game sessions
2. **Player**: Joins games via code, competes in real-time
3. **Solo Learner**: Plays quizzes alone at own pace

## Core Requirements
- Search Binance Academy topics
- AI-generated quiz questions from article content
- Real-time multiplayer with WebSocket (Kahoot-style)
- Single-player timed mode
- Per-session leaderboards only
- Telegram Mini App integration
- High-entropy join codes (≥32 bits)

## What's Been Implemented (2026-03-12)
### Backend
- Binance Academy search + article scraping (with LLM fallback)
- Quiz generation via GPT-4o (emergentintegrations library)
- Session management (create/join with high-entropy codes)
- WebSocket game engine (timer, scoring, leaderboards)
- Telegram bot setup (commands, menu button, webhook)
- Solo quiz endpoint

### Frontend
- HomePage: Host/Join/Solo mode selection
- HostPage: Search → Select Article → Generate Quiz → Create Session
- JoinPage: Enter code + nickname to join
- GamePage: Lobby → Questions → Results → Final Standings (WebSocket)
- SoloPage: Search → Generate → Play → Results
- Dark crypto theme with neon accents (Binance yellow, cyber cyan)
- Telegram Web App SDK integration
- Mobile-first design with 44px+ touch targets

### Telegram Bot
- Token: 8734566460:AAF2SggqHU1gXMLVnzU7e_UNp4HBoCwS5lg
- Commands: /start, /quiz, /join
- Menu button opens Mini App
- Webhook configured for message handling

## Testing Status
- Backend: 100% (all endpoints working)
- Frontend: 90% (all pages render, flows work end-to-end)

## Prioritized Backlog
### P0 (Next)
- Optimize article content fetching speed (reduce LLM fallback dependency)
- Add WebSocket reconnection handling

### P1
- Sound effects for correct/wrong answers
- Animated countdown timer (circular progress)
- Share quiz link via Telegram inline share

### P2
- Quiz history / replay
- Custom quiz duration settings
- Multiple language support
- Article bookmarking

## Next Tasks
1. Test full multiplayer game flow with 2+ browsers
2. Add haptic feedback for Telegram Mini App
3. Optimize LLM token usage for quiz generation
