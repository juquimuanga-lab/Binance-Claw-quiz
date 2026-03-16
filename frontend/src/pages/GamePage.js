import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Trophy, Clock, ChevronRight, Crown, Copy, Check, Play, Home, Triangle, Diamond, Circle, Square } from 'lucide-react';
import { fireCelebration } from '@/utils/celebration';

const API = process.env.REACT_APP_BACKEND_URL;
const WS_URL = API.replace('https://', 'wss://').replace('http://', 'ws://');

const COLORS = ['#FF2E63', '#00F0FF', '#F3BA2F', '#00FF29'];
const ICONS = [Triangle, Diamond, Circle, Square];

export default function GamePage() {
  const { code } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const role = searchParams.get('role') || 'player';
  const playerId = searchParams.get('pid') || `host_${code}`;
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

  const ws = useRef(null);
  const answerTime = useRef(null);

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

  useEffect(() => {
    const socket = new WebSocket(`${WS_URL}/api/ws/${code}/${playerId}`);
    ws.current = socket;

    socket.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      switch (msg.type) {
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
          setTimeout(() => fireCelebration(), 400);
          break;
        default:
          break;
      }
    };

    socket.onclose = () => {};
    return () => socket.close();
  }, [code, playerId]);

  const startGame = () => ws.current?.send(JSON.stringify({ type: 'start_game' }));
  const nextQuestion = () => ws.current?.send(JSON.stringify({ type: 'next_question' }));

  const submitAnswer = (opt) => {
    if (selected !== null || isHost) return;
    const ms = Date.now() - (answerTime.current || Date.now());
    setSelected(opt);
    ws.current?.send(JSON.stringify({ type: 'answer', option: opt, time_ms: ms }));
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

          <div
            data-testid="join-code-display"
            className="rounded-2xl p-6 mb-6 pulse-glow cursor-pointer"
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
                <span
                  key={p.player_id}
                  data-testid={`player-${p.player_id}`}
                  className="px-3 py-1 rounded-full text-sm"
                  style={{ background: '#1E1E1E', color: '#00F0FF' }}
                >
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
              disabled={players.length === 0}
              className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all disabled:opacity-30"
              style={{ background: '#F3BA2F', color: '#000' }}
            >
              <Play size={20} /> Start Game
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
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-center"
        >
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
            <span
              className="text-xl font-bold font-mono"
              style={{ color: progress < 0.3 ? '#FF2E63' : '#F3BA2F' }}
            >
              {timer}
            </span>
          </div>
          {isHost && (
            <span className="text-gray-600 text-xs">{answeredCount}/{players.length} answered</span>
          )}
        </div>

        <div className="w-full h-1.5 rounded-full mb-6" style={{ background: '#1E1E1E' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: progress < 0.3 ? '#FF2E63' : '#F3BA2F' }}
            animate={{ width: `${progress * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>

        <motion.div
          key={qIndex}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl p-6 mb-6"
          style={{ background: '#121212', border: '1px solid #27272A' }}
        >
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
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center text-gray-500 text-sm mt-4"
          >
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
          {results.explanation && (
            <p className="text-gray-500 text-xs mt-2">{results.explanation}</p>
          )}
        </div>

        <div className="rounded-xl p-4 mb-6" style={{ background: '#121212', border: '1px solid #27272A' }}>
          <div className="flex items-center gap-2 mb-3">
            <Trophy size={16} style={{ color: '#F3BA2F' }} />
            <span className="text-sm font-semibold" style={{ color: '#F3BA2F' }}>Leaderboard</span>
          </div>
          <div className="space-y-2">
            {results.scores?.map((s, i) => (
              <div
                key={s.player_id}
                data-testid={`score-${s.player_id}`}
                className="flex items-center justify-between px-3 py-2 rounded-lg"
                style={{ background: i === 0 ? '#F3BA2F15' : '#1E1E1E' }}
              >
                <div className="flex items-center gap-2">
                  {i === 0 && <Crown size={14} style={{ color: '#F3BA2F' }} />}
                  <span className="text-gray-400 text-xs w-5">#{i + 1}</span>
                  <span className="text-sm font-medium">{s.nickname}</span>
                </div>
                <div className="flex items-center gap-3">
                  {s.delta > 0 && (
                    <span className="text-xs" style={{ color: '#00FF29' }}>+{s.delta}</span>
                  )}
                  {s.is_correct === false && s.answered && (
                    <span className="text-xs" style={{ color: '#FF2E63' }}>X</span>
                  )}
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
            className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all"
            style={{ background: '#F3BA2F', color: '#000' }}
          >
            Next Question <ChevronRight size={20} />
          </button>
        )}
        {!isHost && (
          <p className="text-center text-gray-500 text-sm mt-2">Waiting for host...</p>
        )}
      </div>
    );
  }

  // ===== GAME OVER =====
  if (state === 'game_over' && standings) {
    const winner = standings[0];
    const myRank = standings.find(s => s.player_id === playerId);
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-5 py-8 relative z-10 max-w-lg mx-auto">
        <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="text-center w-full">
          <img src="/logo.png" alt="Binance Claw Quiz" className="w-20 h-20 mx-auto mb-2 object-contain" />
          <Trophy size={36} style={{ color: '#F3BA2F' }} className="mx-auto mb-3 float-anim" />
          <h2 data-testid="game-over-title" className="text-3xl font-bold mb-1" style={{ color: '#F3BA2F' }}>Game Over!</h2>

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
                <div
                  key={s.player_id}
                  data-testid={`final-rank-${i}`}
                  className="flex items-center justify-between px-3 py-2 rounded-lg"
                  style={{ background: i === 0 ? '#F3BA2F15' : '#1E1E1E' }}
                >
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

  // fallback
  return (
    <div className="min-h-screen flex items-center justify-center relative z-10">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[#F3BA2F] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Connecting...</p>
      </div>
    </div>
  );
}
