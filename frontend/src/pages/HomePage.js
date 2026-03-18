import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Users, Zap, Trophy, Crown, Flame,
  BarChart2, Terminal, ChevronRight, Star,
  TrendingUp, Gamepad2, BookOpen
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || 'https://binance-claw-quiz-api.onrender.com';

const RANK_STYLES = [
  { bg: 'linear-gradient(135deg, #F3BA2F20, #F3BA2F08)', border: '#F3BA2F60', color: '#F3BA2F', label: '🥇' },
  { bg: 'linear-gradient(135deg, #C0C0C020, #C0C0C008)', border: '#C0C0C060', color: '#C0C0C0', label: '🥈' },
  { bg: 'linear-gradient(135deg, #CD7F3220, #CD7F3208)', border: '#CD7F3260', color: '#CD7F32', label: '🥉' },
  { bg: 'transparent', border: '#27272A', color: '#6B7280', label: '4' },
  { bg: 'transparent', border: '#27272A', color: '#6B7280', label: '5' },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [leaderboard, setLeaderboard] = useState(null);
  const [trending, setTrending] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);
  const [activeTab, setActiveTab] = useState('leaderboard');

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [lbRes, trRes] = await Promise.all([
          fetch(`${API}/api/analytics/leaderboard`),
          fetch(`${API}/api/analytics/trending`),
        ]);
        const lb = await lbRes.json();
        const tr = await trRes.json();
        setLeaderboard(lb);
        setTrending(tr);
      } catch (e) {
        console.error('Analytics fetch failed', e);
      } finally {
        setLoadingStats(false);
      }
    };
    fetchAnalytics();
  }, []);

  const maxCount = trending?.trending?.[0]?.count || 1;
  const maxScore = leaderboard?.top_players?.[0]?.total_score || 1;

  return (
    <div className="min-h-screen relative z-10">

      {/* ── HERO ── */}
      <div className="flex flex-col items-center justify-center px-5 pt-12 pb-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <img
            src="/logo.png"
            alt="Binance Claw Quiz"
            className="w-24 h-24 mx-auto mb-4 object-contain"
          />
          <h1 className="text-3xl font-black mb-1" style={{ color: '#F3BA2F' }}>
            Binance Claw Quiz
          </h1>
          <p className="text-gray-500 text-sm">
            AI-powered crypto quizzes • Compete in real-time
          </p>
        </motion.div>

        {/* ── ACTION BUTTONS ── */}
        <div className="w-full max-w-sm space-y-3 mb-10">
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            onClick={() => navigate('/host')}
            className="w-full h-16 rounded-2xl font-bold text-lg flex items-center justify-between px-6 active:scale-95 transition-all"
            style={{ background: '#F3BA2F', color: '#000' }}
          >
            <div className="flex items-center gap-3">
              <Zap size={22} />
              <div className="text-left">
                <div>Host a Quiz</div>
                <div className="text-xs font-normal opacity-70">Create & challenge friends</div>
              </div>
            </div>
            <ChevronRight size={20} />
          </motion.button>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            onClick={() => navigate('/join')}
            className="w-full h-16 rounded-2xl font-bold text-lg flex items-center justify-between px-6 active:scale-95 transition-all"
            style={{ background: '#121212', border: '1px solid #00F0FF40', color: '#00F0FF' }}
          >
            <div className="flex items-center gap-3">
              <Users size={22} />
              <div className="text-left">
                <div>Join a Game</div>
                <div className="text-xs font-normal opacity-70">Enter game code to play</div>
              </div>
            </div>
            <ChevronRight size={20} />
          </motion.button>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            onClick={() => navigate('/solo')}
            className="w-full h-16 rounded-2xl font-bold text-lg flex items-center justify-between px-6 active:scale-95 transition-all"
            style={{ background: '#121212', border: '1px solid #00FF2940', color: '#00FF29' }}
          >
            <div className="flex items-center gap-3">
              <Gamepad2 size={22} />
              <div className="text-left">
                <div>Solo Quiz</div>
                <div className="text-xs font-normal opacity-70">Practice by yourself</div>
              </div>
            </div>
            <ChevronRight size={20} />
          </motion.button>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            onClick={() => navigate('/agents')}
            className="w-full h-14 rounded-2xl font-semibold text-base flex items-center justify-between px-6 active:scale-95 transition-all"
            style={{ background: '#121212', border: '1px solid #27272A', color: '#9CA3AF' }}
          >
            <div className="flex items-center gap-3">
              <Terminal size={20} />
              <span>Agent Portal</span>
            </div>
            <ChevronRight size={18} />
          </motion.button>
        </div>

        {/* ── QUICK STATS BAR ── */}
        {leaderboard?.stats && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="w-full max-w-sm grid grid-cols-3 gap-3 mb-8"
          >
            {[
              { label: 'Games Played', value: leaderboard.stats.total_games, icon: Trophy },
              { label: 'Players', value: leaderboard.stats.total_players, icon: Users },
              { label: 'Live Now', value: leaderboard.stats.active_games, icon: Flame },
            ].map(({ label, value, icon: Icon }) => (
              <div
                key={label}
                className="rounded-xl p-3 text-center"
                style={{ background: '#121212', border: '1px solid #27272A' }}
              >
                <Icon size={16} className="mx-auto mb-1" style={{ color: '#F3BA2F' }} />
                <p className="text-xl font-black" style={{ color: '#F3BA2F' }}>{value}</p>
                <p className="text-gray-600 text-xs">{label}</p>
              </div>
            ))}
          </motion.div>
        )}

        {/* ── ANALYTICS SECTION ── */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="w-full max-w-sm"
        >
          {/* Section header */}
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={18} style={{ color: '#F3BA2F' }} />
            <h2 className="text-base font-bold text-white">Community Stats</h2>
          </div>

          {/* Tab switcher */}
          <div
            className="flex gap-1 p-1 rounded-xl mb-4"
            style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
          >
            {[
              { key: 'leaderboard', label: '🏆 Top Players', icon: Crown },
              { key: 'trending', label: '🔥 Trending', icon: TrendingUp },
            ].map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className="flex-1 py-2 rounded-lg text-sm font-semibold transition-all"
                style={{
                  background: activeTab === key ? '#F3BA2F' : 'transparent',
                  color: activeTab === key ? '#000' : '#6B7280',
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <AnimatePresence mode="wait">

            {/* ── LEADERBOARD TAB ── */}
            {activeTab === 'leaderboard' && (
              <motion.div
                key="leaderboard"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                className="space-y-2"
              >
                {loadingStats ? (
                  <div className="flex flex-col gap-2">
                    {[...Array(5)].map((_, i) => (
                      <div
                        key={i}
                        className="h-16 rounded-xl animate-pulse"
                        style={{ background: '#121212' }}
                      />
                    ))}
                  </div>
                ) : leaderboard?.top_players?.length > 0 ? (
                  leaderboard.top_players.map((player, i) => {
                    const style = RANK_STYLES[i] || RANK_STYLES[4];
                    const scorePercent = Math.max(
                      10,
                      Math.round((player.total_score / maxScore) * 100)
                    );
                    return (
                      <motion.div
                        key={player.nickname}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.07 }}
                        className="rounded-xl p-3"
                        style={{
                          background: style.bg,
                          border: `1px solid ${style.border}`,
                        }}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-lg w-6 text-center">{style.label}</span>
                          <div className="flex-1 min-w-0">
                            <p
                              className="font-bold text-sm truncate"
                              style={{ color: i < 3 ? style.color : '#E5E7EB' }}
                            >
                              {player.nickname}
                            </p>
                            <p className="text-gray-600 text-xs">
                              {player.games_played} game{player.games_played !== 1 ? 's' : ''} •
                              best {player.best_score.toLocaleString()} pts
                            </p>
                          </div>
                          <div className="text-right">
                            <p
                              className="font-black text-base font-mono"
                              style={{ color: style.color }}
                            >
                              {player.total_score.toLocaleString()}
                            </p>
                            <p className="text-gray-600 text-xs">total pts</p>
                          </div>
                        </div>
                        {/* Score bar */}
                        <div
                          className="w-full h-1 rounded-full overflow-hidden"
                          style={{ background: '#1E1E1E' }}
                        >
                          <motion.div
                            className="h-full rounded-full"
                            style={{ background: i < 3 ? style.color : '#374151' }}
                            initial={{ width: 0 }}
                            animate={{ width: `${scorePercent}%` }}
                            transition={{ duration: 0.8, delay: i * 0.1 }}
                          />
                        </div>
                      </motion.div>
                    );
                  })
                ) : (
                  <div
                    className="rounded-xl p-8 text-center"
                    style={{ background: '#121212', border: '1px solid #27272A' }}
                  >
                    <Trophy size={32} className="mx-auto mb-3 opacity-20" style={{ color: '#F3BA2F' }} />
                    <p className="text-gray-600 text-sm">No games played yet.</p>
                    <p className="text-gray-700 text-xs mt-1">Be the first on the leaderboard!</p>
                  </div>
                )}
              </motion.div>
            )}

            {/* ── TRENDING TAB ── */}
            {activeTab === 'trending' && (
              <motion.div
                key="trending"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="space-y-2"
              >
                {loadingStats ? (
                  <div className="flex flex-col gap-2">
                    {[...Array(5)].map((_, i) => (
                      <div
                        key={i}
                        className="h-16 rounded-xl animate-pulse"
                        style={{ background: '#121212' }}
                      />
                    ))}
                  </div>
                ) : trending?.trending?.length > 0 ? (
                  trending.trending.map((topic, i) => {
                    const heatPercent = Math.max(
                      8,
                      Math.round(((topic.count || 0) / maxCount) * 100)
                    );
                    const heatColor =
                      i === 0 ? '#FF2E63' :
                      i === 1 ? '#F3BA2F' :
                      i === 2 ? '#00F0FF' :
                      '#6B7280';
                    return (
                      <motion.div
                        key={topic.title}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.07 }}
                        className="rounded-xl p-3"
                        style={{ background: '#121212', border: '1px solid #27272A' }}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <div
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
                            style={{ background: `${heatColor}20`, color: heatColor }}
                          >
                            {i === 0 ? '🔥' : i + 1}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-white text-sm font-semibold truncate">
                              {topic.title}
                            </p>
                            <p className="text-gray-600 text-xs">
                              {topic.count > 0
                                ? `${topic.count} quiz${topic.count !== 1 ? 'zes' : ''} this week`
                                : 'Popular topic'}
                            </p>
                          </div>
                          <BookOpen size={14} className="text-gray-700 shrink-0" />
                        </div>
                        {/* Heat bar */}
                        <div
                          className="w-full h-1.5 rounded-full overflow-hidden"
                          style={{ background: '#1E1E1E' }}
                        >
                          <motion.div
                            className="h-full rounded-full"
                            style={{ background: heatColor }}
                            initial={{ width: 0 }}
                            animate={{ width: `${heatPercent}%` }}
                            transition={{ duration: 0.8, delay: i * 0.1 }}
                          />
                        </div>
                      </motion.div>
                    );
                  })
                ) : (
                  <div
                    className="rounded-xl p-8 text-center"
                    style={{ background: '#121212', border: '1px solid #27272A' }}
                  >
                    <Flame size={32} className="mx-auto mb-3 opacity-20" style={{ color: '#FF2E63' }} />
                    <p className="text-gray-600 text-sm">No trending topics yet.</p>
                    <p className="text-gray-700 text-xs mt-1">Create a quiz to get started!</p>
                  </div>
                )}

                {/* Trending tip */}
                {trending?.trending?.length > 0 && (
                  <p className="text-gray-700 text-xs text-center pt-2">
                    Based on quizzes created in the last 7 days
                  </p>
                )}
              </motion.div>
            )}

          </AnimatePresence>
        </motion.div>

        {/* ── BOTTOM PADDING ── */}
        <div className="h-10" />
      </div>
    </div>
  );
}
