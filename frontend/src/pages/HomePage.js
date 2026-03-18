import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Zap, Users, User, HelpCircle, Terminal } from 'lucide-react';
import GuideModal from '@/components/GuideModal';

const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;

export default function HomePage() {
  const navigate = useNavigate();
  const [showGuide, setShowGuide] = useState(false);

  const cards = [
    {
      title: 'Host a Quiz',
      desc: 'Search Binance Academy, generate questions & challenge friends',
      icon: Zap,
      color: '#F3BA2F',
      path: '/host',
      testId: 'host-quiz-btn',
    },
    {
      title: 'Join a Game',
      desc: 'Enter a game code and compete in real-time',
      icon: Users,
      color: '#00F0FF',
      path: '/join',
      testId: 'join-quiz-btn',
    },
    {
      title: 'Solo Mode',
      desc: 'Learn at your own pace with timed quizzes',
      icon: User,
      color: '#00FF29',
      path: '/solo',
      testId: 'solo-quiz-btn',
    },
    {
      title: 'Agent Portal',
      desc: 'Get an API key and host quizzes programmatically as a Claw Agent',
      icon: Terminal,
      color: '#BF5AF2',
      path: '/agents',
      testId: 'agent-portal-btn',
    },
  ];

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-5 py-10 relative z-10">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-center mb-8"
      >
        <motion.img
          src="/logo.png"
          alt="Binance Claw Quiz"
          data-testid="app-logo"
          className="w-36 h-36 mx-auto mb-4 object-contain drop-shadow-[0_0_30px_rgba(243,186,47,0.4)]"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.4, type: 'spring' }}
        />
        <h1
          data-testid="app-title"
          className="text-3xl md:text-4xl font-bold tracking-tight"
          style={{ color: '#F3BA2F' }}
        >
          Binance Claw Quiz
        </h1>
        <p className="text-gray-400 text-base max-w-md mx-auto mt-2">
          Fun crypto quizzes powered by Binance Academy
        </p>
        {tgUser && (
          <p className="text-gray-500 text-sm mt-2">
            Hey {tgUser.first_name}!
          </p>
        )}
      </motion.div>

      <div className="w-full max-w-sm space-y-4">
        {cards.map((card, i) => (
          <motion.button
            key={card.path}
            data-testid={card.testId}
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1, duration: 0.25 }}
            onClick={() => navigate(card.path)}
            className="w-full flex items-center gap-4 p-5 rounded-2xl border transition-all active:scale-[0.97]"
            style={{
              background: '#121212',
              borderColor: `${card.color}30`,
            }}
            whileHover={{ borderColor: card.color, scale: 1.01 }}
          >
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: `${card.color}15` }}
            >
              <card.icon size={24} color={card.color} />
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-lg" style={{ color: card.color }}>
                {card.title}
              </h3>
              <p className="text-gray-500 text-sm">{card.desc}</p>
            </div>
          </motion.button>
        ))}
      </div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className="text-gray-600 text-xs mt-10 text-center"
      >
        Content sourced from Binance Academy
      </motion.p>

      <motion.button
        data-testid="how-to-play-btn"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        onClick={() => setShowGuide(true)}
        className="mt-4 flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium transition-all active:scale-95"
        style={{ background: '#1E1E1E', border: '1px solid #27272A', color: '#9CA3AF' }}
        whileHover={{ borderColor: '#F3BA2F', color: '#F3BA2F' }}
      >
        <HelpCircle size={15} />
        How to Play
      </motion.button>

      <GuideModal isOpen={showGuide} onClose={() => setShowGuide(false)} />
    </div>
  );
}
