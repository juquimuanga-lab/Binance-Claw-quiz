import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, LogIn, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useLanguage } from '@/context/LanguageContext';
import { useTranslations } from '@/i18n/translations';

const API = process.env.REACT_APP_BACKEND_URL;
const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;

export default function JoinPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [code, setCode] = useState(searchParams.get('code') || '');
  const [nickname, setNickname] = useState(tgUser?.first_name || '');
  const [joining, setJoining] = useState(false);

  const joinGame = async () => {
    if (!code.trim() || !nickname.trim()) {
      toast.error('Enter both game code and nickname');
      return;
    }
    setJoining(true);
    try {
      const res = await fetch(`${API}/api/session/join`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: code.trim().toUpperCase(), nickname: nickname.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to join');
      }
      const data = await res.json();
      navigate(`/game/${data.session.code}?role=player&pid=${data.player_id}`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setJoining(false);
    }
  };
  const { langCode } = useLanguage();
  const t = useTranslations(langCode);
  
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-5 py-8 relative z-10">
      <div className="w-full max-w-sm">
        <button
          data-testid="back-btn"
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors"
        >
          <ArrowLeft size={18} /> Back
        </button>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h2 data-testid="join-title" className="text-3xl font-bold mb-2" style={{ color: '#00F0FF' }}>
            Join Game
          </h2>
          <p className="text-gray-500 text-sm mb-8">Enter the game code from your host</p>

          <div className="space-y-4 mb-8">
            <div>
              <label className="text-gray-400 text-sm mb-2 block">Game Code</label>
              <input
                data-testid="join-code-input"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="XXXXXXXX"
                maxLength={12}
                className="w-full h-14 px-4 rounded-xl text-white text-center text-2xl font-mono tracking-widest placeholder:text-gray-700 outline-none uppercase"
                style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
              />
            </div>
            <div>
              <label className="text-gray-400 text-sm mb-2 block">Nickname</label>
              <input
                data-testid="nickname-input"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                placeholder="Your name"
                maxLength={20}
                className="w-full h-12 px-4 rounded-xl text-white placeholder:text-gray-600 outline-none"
                style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
              />
            </div>
          </div>

          <button
            data-testid="join-game-btn"
            onClick={joinGame}
            disabled={joining}
            className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all disabled:opacity-50"
            style={{ background: '#00F0FF', color: '#000' }}
          >
            {joining ? (
              <Loader2 size={20} className="animate-spin" />
            ) : (
              <>
                <LogIn size={20} /> Join Game
              </>
            )}
          </button>
        </motion.div>
      </div>
    </div>
  );
}
