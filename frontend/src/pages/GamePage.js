import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Trophy, Clock, ChevronRight, Crown, Copy, Check, Play, Home, Triangle, Diamond, Circle, Square } from 'lucide-react';
import { fireCelebration } from '@/utils/celebration';

const API = process.env.REACT_APP_BACKEND_URL || 'https://binance-claw-quiz-api.onrender.com';
const WS_URL = API.replace('https://', 'wss://').replace('http://', 'ws://');

const COLORS = ['#FF2E63', '#00F0FF', '#F3BA2F', '#00FF29'];
const ICONS = [Triangle, Diamond, Circle, Square];

// ================= BUID MODAL =================

function BuidModal({ rank, nickname, score, code, playerId }) {
  const [buid, setBuid] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  const rankEmoji = { 1: '🥇', 2: '🥈', 3: '🥉' };
  const rankColor = { 1: '#F3BA2F', 2: '#C0C0C0', 3: '#CD7F32' };

  const submitBuid = async () => {
    if (!buid.trim() || !agreedToTerms) return;
    setSubmitting(true);
    try {
      await fetch(`${API}/api/session/submit-buid`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code,
          player_id: playerId,
          nickname,
          buid: buid.trim(),
          rank,
          score,
        }),
      });
      setSubmitted(true);
    } catch (e) {
      console.error('BUID submit failed', e);
    } finally {
      setSubmitting(false);
    }
  };

  if (dismissed) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center px-5"
      style={{ background: 'rgba(0,0,0,0.90)' }}
    >
      {/* ===== TERMS MODAL ===== */}
      <AnimatePresence>
        {showTerms && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="fixed inset-0 z-60 flex items-center justify-center px-5"
            style={{ background: 'rgba(0,0,0,0.95)' }}
          >
            <div
              className="w-full max-w-sm rounded-2xl p-5 max-h-[80vh] overflow-y-auto"
              style={{ background: '#121212', border: '1px solid #27272A' }}
            >
              <h3 className="text-base font-bold mb-4" style={{ color: '#F3BA2F' }}>
                📋 Terms of BUID Submission
              </h3>

              <div className="space-y-4 text-gray-400 text-xs leading-relaxed">
                <p>
                  By submitting your Binance User ID (BUID), you agree to allow Binance to
                  securely store your BUID for the purpose of managing your participation in
                  current and future{' '}
                  <span style={{ color: '#F3BA2F' }}>Binance Telegram</span>{' '}
                  marketing campaigns and activities.
                </p>

                <p>
                  Your personal data submitted through Binance Telegram activities will be
                  managed by Binance in accordance with the{' '}
                  <a
                    href="https://www.binance.com/en/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#00F0FF' }}
                    className="underline"
                  >
                    Binance Privacy Policy
                  </a>
                  {'. Please note that Telegram is a third-party platform with its own privacy policies, and your interactions on Telegram are also subject to Telegram\'s terms and privacy practices.'}
                </p>

                <p>
                  You have the right to withdraw your consent and request the removal of your
                  BUID from the Binance Telegram Activities database at any time. To do so,
                  please contact us via the{' '}
                  <a
                    href="https://t.me/binance"
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#00F0FF' }}
                    className="underline"
                  >
                    official Binance Telegram support channel
                  </a>
                  {'.'}
                </p>

                <div
                  className="rounded-xl p-3 text-xs"
                  style={{ background: '#1E1E1E', border: '1px solid #27272A' }}
                >
                  <p className="font-semibold mb-1" style={{ color: '#F3BA2F' }}>🔐 How we protect your BUID</p>
                  <p className="text-gray-500">
                    Your BUID is encrypted using AES-256-CBC with a unique random key before
                    being stored. It is never exposed publicly and is only decrypted when
                    processing your reward.
                  </p>
                </div>
              </div>

              <button
                onClick={() => {
                  setAgreedToTerms(true);
                  setShowTerms(false);
                }}
                className="w-full h-11 rounded-xl font-bold text-sm mt-5 active:scale-95 transition-all"
                style={{ background: '#F3BA2F', color: '#000' }}
              >
                ✅ I Agree & Accept
              </button>

              <button
                onClick={() => setShowTerms(false)}
                className="w-full h-10 rounded-xl text-xs text-gray-600 hover:text-gray-400 transition-colors mt-2"
              >
                Close
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ===== MAIN BUID MODAL ===== */}
      <motion.div
        initial={{ scale: 0.8, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        className="w-full max-w-sm rounded-2xl p-6 text-center"
        style={{ background: '#121212', border: `2px solid ${rankColor[rank] || '#F3BA2F'}` }}
      >
        {!submitted ? (
          <>
            <div className="text-4xl mb-2">{rankEmoji[rank] || '🎖'}</div>
            <h3 className="text-xl font-black mb-1" style={{ color: rankColor[rank] || '#F3BA2F' }}>
              You placed #{rank}!
            </h3>
            <p className="text-gray-400 text-sm mb-1">{score.toLocaleString()} points</p>
            <p className="text-gray-300 text-sm mb-4">
              Enter your <span style={{ color: '#F3BA2F' }}>BUID</span> to claim your reward
            </p>

            <input
              value={buid}
              onChange={e => setBuid(e.target.value)}
              placeholder="Enter your BUID here"
              className="w-full h-12 px-4 rounded-xl text-white text-center font-mono placeholder:text-gray-600 outline-none mb-4"
              style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
            />

            {/* Terms checkbox */}
            <div className="flex items-start gap-2 mb-4 text-left">
              <input
                type="checkbox"
                id="terms-check"
                checked={agreedToTerms}
                onChange={e => setAgreedToTerms(e.target.checked)}
                className="mt-0.5 shrink-0 accent-yellow-400"
              />
              <label htmlFor="terms-check" className="text-xs text-gray-500 leading-relaxed">
                I agree to the{' '}
                <button
                  onClick={() => setShowTerms(true)}
                  className="underline transition-colors"
                  style={{ color: '#F3BA2F' }}
                >
                  Terms of BUID Submission
                </button>
                {'. My BUID will be securely stored and used only for reward processing.'}
              </label>
            </div>

            <button
              onClick={submitBuid}
              disabled={submitting || !buid.trim() || !agreedToTerms}
              className="w-full h-12 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-all disabled:opacity-40 mb-3"
              style={{ background: rankColor[rank] || '#F3BA2F', color: '#000' }}
            >
              {submitting ? '⏳ Submitting...' : '🎁 Claim Reward'}
            </button>

            <button
              onClick={() => setDismissed(true)}
              className="text-gray-600 text-xs hover:text-gray-400 transition-colors"
            >
              Skip for now
            </button>
          </>
        ) : (
          <motion.div initial={{ scale: 0.8 }} animate={{ scale: 1 }}>
            <div className="text-5xl mb-3">✅</div>
            <h3 className="text-xl font-black mb-2" style={{ color: '#00FF29' }}>
              BUID Submitted!
            </h3>
            <p className="text-gray-400 text-sm mb-1">
              Your BUID has been securely encrypted and sent to the host.
            </p>
            <p className="text-gray-600 text-xs mb-4">
              Rewards will be processed shortly. Thank you for participating!
            </p>
            <button
              onClick={() => setDismissed(true)}
              className="w-full h-12 rounded-xl font-bold"
              style={{ background: '#1E1E1E', color: '#F2F3F5' }}
            >
              Close
            </button>
          </motion.div>
        )}
      </motion.div>
    </motion.div>
  );
}

// ================= GAME PAGE =================

export default function GamePage() {
  const { code } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const role = searchParams.get('role') || 'player';
  const playerId = searchParams.get('pid') || `player_${Math.random().toString(36).slice(2, 7)}`;
  const isHost = role === 'host';

  const [state, setState] = useState('lobby');
  const [players, setPlayers] = useState([]);
  const [question, setQuestion] = useState(null);
  const [qIndex, setQIndex] = useState(0);
  const [totalQ, setTotalQ] = useState(0);
  const [timer, setTimer] = useState(20);
  const [duration, setDuration] = useState(20);
  const [selected, setSelected] = useState(null);
  const [results, setResults] = useState(null);
  const [standings, setStandings] = useState(null);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [session, setSession] = useState(null);
  const [copied, setCopied] = useState(false);
  const [wsReady, setWsReady] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);

  const ws = useRef(null);
  const answerTime = useRef(null);
  const pingInterval = useRef(null);
  const reconnectTimeout = useRef(null);
  const shouldReconnect = useRef(true);
  const pendingMessages = useRef([]);

  useEffect(() => {
    fetch(`${API}/api/session/${code}`)
      .then(r => r.json())
      .then(d => {
        setSession(d);
        setPlayers(d.players || []);
        setTotalQ(d.total_questions || 0);
      })
      .catch(() => {});
  }, [code]);

  const connectWebSocket = useCallback(() => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(`${WS_URL}/api/ws/${code}/${playerId}`);
    ws.current = socket;

    socket.onopen = () => {
      setWsReady(true);
      setReconnecting(false);

      if (isHost) {
        const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;
        if (tgUser?.id) {
          socket.send(JSON.stringify({
            type: 'register_host_chat',
            chat_id: tgUser.id,
          }));
        }
      }

      while (pendingMessages.current.length > 0) {
        const msg = pendingMessages.current.shift();
        socket.send(JSON.stringify(msg));
      }

      clearInterval(pingInterval.current);
      pingInterval.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: 'ping' }));
        }
      }, 20000);
    };

    socket.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      switch (msg.type) {
        case 'pong': break;
        case 'player_joined':
          setPlayers(msg.players || []);
          break;
        case 'player_left':
          setPlayers(msg.players || []);
          break;
        case 'game_starting':
          setTotalQ(msg.total_questions);
          setState('starting');
          break;
        case 'question':
          setQuestion(msg);
          setQIndex(msg.index);
          setTotalQ(msg.total);
          setTimer(msg.duration);
          setDuration(msg.duration);
          setSelected(null);
          setAnsweredCount(0);
          setState('question');
          answerTime.current = Date.now();
          break;
        case 'timer':
          setTimer(msg.seconds);
          break;
        case 'player_answered':
          setAnsweredCount(msg.answered_count);
          break;
        case 'answer_result':
          setResults(msg);
          setState('results');
          break;
        case 'game_over':
          setStandings(msg.final_standings);
          setState('game_over');
          shouldReconnect.current = false;
          setTimeout(() => fireCelebration(), 400);
          break;
        default:
          break;
      }
    };

    socket.onclose = () => {
      setWsReady(false);
      clearInterval(pingInterval.current);
      if (shouldReconnect.current) {
        setReconnecting(true);
        reconnectTimeout.current = setTimeout(() => {
          connectWebSocket();
        }, 2000);
      }
    };

    socket.onerror = (err) => {
      console.error('WS error:', err);
      socket.close();
    };
  }, [code, playerId]);

  useEffect(() => {
    shouldReconnect.current = true;
    connectWebSocket();
    return () => {
      shouldReconnect.current = false;
      clearInterval(pingInterval.current);
      clearTimeout(reconnectTimeout.current);
      ws.current?.close();
    };
  }, [connectWebSocket]);

  const safeSend = (msg) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(msg));
    } else {
      pendingMessages.current.push(msg);
      connectWebSocket();
    }
  };

  const startGame = () => safeSend({ type: 'start_game' });
  const nextQuestion = () => safeSend({ type: 'next_question' });

  const submitAnswer = (opt) => {
    if (selected !== null || isHost) return;
    const ms = Date.now() - (answerTime.current || Date.now());
    setSelected(opt);
    safeSend({ type: 'answer', option: opt, time_ms: ms });
  };

  const copyCode = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ===== LOBBY =====
  if (state === 'lobby') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-5 py-8 relative z-10">
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center w-full max-w-md">
          <img src="/logo.png" alt="Binance Claw Quiz" className="w-20 h-20 mx-auto mb-3 object-contain" />
          <p className="text-gray-500 text-sm mb-2">{session?.article_title}</p>
          <h2 data-testid="lobby-title" className="text-2xl font-bold mb-6" style={{ color: '#F3BA2F' }}>
            {isHost ? 'Game Lobby' : 'Waiting for Host...'}
          </h2>

          <div className="flex items-center justify-center gap-2 mb-4">
            <div className={`w-2 h-2 rounded-full transition-colors ${wsReady ? 'bg-green-500' : reconnecting ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-xs text-gray-500">
              {wsReady ? 'Connected' : reconnecting ? 'Reconnecting...' : 'Disconnected'}
            </span>
          </div>

          <div
            data-testid="join-code-display"
            className="rounded-2xl p-6 mb-6 cursor-pointer"
            style={{ background: '#121212', border: '2px solid #F3BA2F' }}
            onClick={copyCode}
          >
            <p className="text-gray-400 text-xs mb-2 uppercase tracking-widest">Game Code</p>
            <p className="text-4xl md:text-5xl font-mono font-bold tracking-[0.3em]" style={{ color: '#F3BA2F' }}>
              {code}
            </p>
            <div className="flex items-center justify-center gap-2 mt-3 text-gray-500 text-xs">
              {copied ? <Check size={14} /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Tap to copy'}
            </div>
          </div>

          <div className="rounded-xl p-4 mb-6" style={{ background: '#121212', border: '1px solid #27272A' }}>
            <div className="flex items-center gap-2 mb-3">
              <Users size={16} className="text-gray-400" />
              <span className="text-gray-400 text-sm">{players.length} player{players.length !== 1 ? 's' : ''}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {players.map((p) => (
                <span key={p.player_id} className="px-3 py-1 rounded-full text-sm" style={{ background: '#1E1E1E', color: '#00F0FF' }}>
                  {p.nickname}
                </span>
              ))}
              {!players.length && <p className="text-gray-600 text-sm">Waiting for players...</p>}
            </div>
          </div>

          {isHost && (
            <button
              data-testid="start-game-btn"
              onClick={startGame}
              disabled={players.length === 0 || !wsReady}
              className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all disabled:opacity-30"
              style={{ background: '#F3BA2F', color: '#000' }}
            >
              <Play size={20} /> {wsReady ? 'Start Game' : 'Connecting...'}
            </button>
          )}
        </motion.div>
      </div>
    );
  }

  // ===== STARTING =====
  if (state === 'starting') {
    return (
      <div className="min-h-screen flex items-center justify-center relative z-10">
        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} className="text-center">
          <h2 className="text-5xl font-bold" style={{ color: '#F3BA2F' }}>Get Ready!</h2>
          <p className="text-gray-400 mt-3">{totalQ} questions</p>
        </motion.div>
      </div>
    );
  }

  // ===== QUESTION =====
  if (state === 'question') {
    const progress = timer / duration;
    return (
      <div className="min-h-screen flex flex-col px-4 py-6 relative z-10 max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-500 text-sm font-mono">{qIndex + 1}/{totalQ}</span>
          <div className="flex items-center gap-2">
            <Clock size={16} style={{ color: progress < 0.3 ? '#FF2E63' : '#F3BA2F' }} />
            <span className="text-xl font-bold font-mono" style={{ color: progress < 0.3 ? '#FF2E63' : '#F3BA2F' }}>
              {timer}
            </span>
          </div>
          {isHost && <span className="text-gray-600 text-xs">{answeredCount}/{players.length} answered</span>}
        </div>

        <div className="w-full h-1.5 rounded-full mb-6" style={{ background: '#1E1E1E' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: progress < 0.3 ? '#FF2E63' : '#F3BA2F' }}
            animate={{ width: `${progress * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        <motion.div key={qIndex} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-6 mb-6" style={{ background: '#121212', border: '1px solid #27272A' }}>
          <h3 data-testid="question-text" className="text-xl md:text-2xl font-semibold text-center leading-tight">
            {question?.question}
          </h3>
        </motion.div>

        <div className="grid grid-cols-1 gap-3 flex-1">
          {question?.options?.map((opt, i) => {
            const Icon = ICONS[i];
            const isSelected = selected === i;
            return (
              <motion.button
                key={i}
                data-testid={`option-${i}`}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.08 }}
                onClick={() => submitAnswer(i)}
                disabled={selected !== null || isHost}
                className="h-20 md:h-24 rounded-xl font-semibold text-base md:text-lg flex items-center gap-3 px-5 transition-all active:scale-[0.97]"
                style={{
                  background: isSelected ? COLORS[i] : `${COLORS[i]}20`,
                  border: `2px solid ${isSelected ? COLORS[i] : `${COLORS[i]}40`}`,
                  color: isSelected ? '#000' : '#F2F3F5',
                  borderBottom: `4px solid ${isSelected ? '#00000030' : `${COLORS[i]}30`}`,
                  opacity: selected !== null && !isSelected ? 0.4 : 1,
                }}
              >
                <Icon size={20} fill={isSelected ? '#000' : COLORS[i]} color={isSelected ? '#000' : COLORS[i]} />
                <span className="text-left flex-1 break-words leading-snug">{opt}</span>
              </motion.button>
            );
          })}
        </div>

        {selected !== null && !isHost && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-gray-500 text-sm mt-4">
            Answer locked! Waiting for results...
          </motion.p>
        )}
      </div>
    );
  }

  // ===== RESULTS =====
  if (state === 'results' && results) {
    const correctIdx = results.correct;
    return (
      <div className="min-h-screen flex flex-col px-4 py-6 relative z-10 max-w-lg mx-auto">
        <p className="text-gray-500 text-sm text-center mb-2">Question {results.question_index + 1} Results</p>

        <div className="rounded-xl p-4 mb-4 text-center" style={{ background: '#121212', border: '1px solid #27272A' }}>
          <p className="text-gray-400 text-sm mb-1">Correct Answer</p>
          <p className="text-lg font-bold" style={{ color: COLORS[correctIdx] }}>
            {question?.options?.[correctIdx]}
          </p>
          {results.explanation && <p className="text-gray-500 text-xs mt-2">{results.explanation}</p>}
        </div>

        <div className="rounded-xl p-4 mb-6" style={{ background: '#121212', border: '1px solid #27272A' }}>
          <div className="flex items-center gap-2 mb-3">
            <Trophy size={16} style={{ color: '#F3BA2F' }} />
            <span className="text-sm font-semibold" style={{ color: '#F3BA2F' }}>Leaderboard</span>
          </div>
          <div className="space-y-2">
            {results.scores?.map((s, i) => (
              <div key={s.player_id} data-testid={`score-${s.player_id}`}
                className="flex items-center justify-between px-3 py-2 rounded-lg"
                style={{ background: i === 0 ? '#F3BA2F15' : '#1E1E1E' }}>
                <div className="flex items-center gap-2">
                  {i === 0 && <Crown size={14} style={{ color: '#F3BA2F' }} />}
                  <span className="text-gray-400 text-xs w-5">#{i + 1}</span>
                  <span className="text-sm font-medium">{s.nickname}</span>
                </div>
                <div className="flex items-center gap-3">
                  {s.delta > 0 && <span className="text-xs" style={{ color: '#00FF29' }}>+{s.delta}</span>}
                  {s.is_correct === false && s.answered && <span className="text-xs" style={{ color: '#FF2E63' }}>✗</span>}
                  <span className="font-mono font-bold text-sm" style={{ color: '#F3BA2F' }}>{s.score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {isHost && (
          <button
            data-testid="next-question-btn"
            onClick={nextQuestion}
            disabled={!wsReady}
            className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all disabled:opacity-50"
            style={{ background: '#F3BA2F', color: '#000' }}
          >
            {wsReady ? <><ChevronRight size={20} /> Next Question</> : 'Reconnecting...'}
          </button>
        )}
        {!isHost && <p className="text-center text-gray-500 text-sm mt-2">Waiting for host...</p>}
      </div>
    );
  }

  // ===== GAME OVER =====
  if (state === 'game_over' && standings) {
    const winner = standings[0];
    const myRank = standings.find(s => s.player_id === playerId);
    const isTop3 = myRank && myRank.rank <= 3;

    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-5 py-8 relative z-10 max-w-lg mx-auto">

        {isTop3 && !isHost && (
          <BuidModal
            rank={myRank.rank}
            nickname={myRank.nickname}
            score={myRank.score}
            code={code}
            playerId={playerId}
          />
        )}

        <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="text-center w-full">
          <img src="/logo.png" alt="Binance Claw Quiz" className="w-20 h-20 mx-auto mb-2 object-contain" />
          <Trophy size={36} style={{ color: '#F3BA2F' }} className="mx-auto mb-3" />
          <h2 data-testid="game-over-title" className="text-3xl font-bold mb-1" style={{ color: '#F3BA2F' }}>
            Game Over!
          </h2>

          {winner && (
            <p className="text-lg mb-6">
              <span style={{ color: '#00F0FF' }}>{winner.nickname}</span> wins!
            </p>
          )}

          {myRank && !isHost && (
            <div className="rounded-xl p-4 mb-6 inline-block" style={{ background: '#121212', border: '1px solid #F3BA2F50' }}>
              <p className="text-gray-400 text-xs">Your Rank</p>
              <p className="text-2xl font-bold" style={{ color: '#F3BA2F' }}>#{myRank.rank}</p>
              <p className="text-sm text-gray-400">{myRank.score} pts</p>
            </div>
          )}

          <div className="rounded-xl p-4 mb-6 w-full" style={{ background: '#121212', border: '1px solid #27272A' }}>
            <p className="text-sm font-semibold mb-3" style={{ color: '#F3BA2F' }}>Final Standings</p>
            <div className="space-y-2">
              {standings.map((s, i) => (
                <div key={s.player_id} data-testid={`final-rank-${i}`}
                  className="flex items-center justify-between px-3 py-2 rounded-lg"
                  style={{ background: i === 0 ? '#F3BA2F15' : '#1E1E1E' }}>
                  <div className="flex items-center gap-2">
                    {i === 0 && <Crown size={14} style={{ color: '#F3BA2F' }} />}
                    {i === 1 && <span className="text-gray-400 text-xs">2nd</span>}
                    {i === 2 && <span className="text-gray-400 text-xs">3rd</span>}
                    {i > 2 && <span className="text-gray-400 text-xs">#{i + 1}</span>}
                    <span className="text-sm font-medium">{s.nickname}</span>
                  </div>
                  <span className="font-mono font-bold" style={{ color: '#F3BA2F' }}>{s.score}</span>
                </div>
              ))}
            </div>
          </div>

          <button
            data-testid="go-home-btn"
            onClick={() => navigate('/')}
            className="h-12 px-8 rounded-xl font-semibold flex items-center justify-center gap-2 mx-auto active:scale-95 transition-all"
            style={{ background: '#1E1E1E', border: '1px solid #27272A', color: '#F2F3F5' }}
          >
            <Home size={18} /> Play Again
          </button>
        </motion.div>
      </div>
    );
  }

  // ===== FALLBACK =====
  return (
    <div className="min-h-screen flex items-center justify-center relative z-10">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[#F3BA2F] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">{reconnecting ? 'Reconnecting...' : 'Connecting...'}</p>
      </div>
    </div>
  );
}
