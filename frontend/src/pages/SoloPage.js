import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ArrowLeft, Loader2, BookOpen, Play, Clock, Trophy, Home, Triangle, Diamond, Circle, Square, Check, X } from 'lucide-react';
import { toast } from 'sonner';
import { fireCelebration } from '@/utils/celebration';

const API = process.env.REACT_APP_BACKEND_URL;
const COLORS = ['#FF2E63', '#00F0FF', '#F3BA2F', '#00FF29'];
const ICONS = [Triangle, Diamond, Circle, Square];

export default function SoloPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState('search'); // search, playing, result, done
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [questions, setQuestions] = useState([]);
  const [qIndex, setQIndex] = useState(0);
  const [timer, setTimer] = useState(20);
  const [selected, setSelected] = useState(null);
  const [score, setScore] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [answers, setAnswers] = useState([]);
  const [articleTitle, setArticleTitle] = useState('');

  const timerRef = useRef(null);
  const startTimeRef = useRef(null);

  const searchAcademy = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API}/api/academy/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data.results || []);
      if (!data.results?.length) toast.info('No results. Try different keywords.');
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const selectAndGenerate = async (article) => {
    setGenerating(true);
    try {
      const contentRes = await fetch(`${API}/api/academy/article`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: article.url }),
      });
      const content = await contentRes.json();
      setArticleTitle(content.title || article.title);

      const quizRes = await fetch(`${API}/api/quiz/solo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article_url: article.url,
          article_title: content.title || article.title,
          article_content: content.content || '',
          num_questions: 10,
        }),
      });
      if (!quizRes.ok) {
        const errData = await quizRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to generate quiz. Please try again.');
      }
      const quiz = await quizRes.json();
      setQuestions(quiz.questions || []);
      setStep('playing');
      setTimer(20);
      startTimeRef.current = Date.now();
    } catch (err) {
      toast.error(err.message || 'Failed to generate quiz');
    } finally {
      setGenerating(false);
    }
  };

  // Timer
  useEffect(() => {
    if (step !== 'playing' || showResult) return;
    timerRef.current = setInterval(() => {
      setTimer((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current);
          handleTimeUp();
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current);
  }, [step, qIndex, showResult]);

  const handleTimeUp = () => {
    setShowResult(true);
    setAnswers((prev) => [...prev, { question_index: qIndex, option: -1, correct: false }]);
  };

  const submitAnswer = (opt) => {
    if (selected !== null || showResult) return;
    clearInterval(timerRef.current);
    const ms = Date.now() - (startTimeRef.current || Date.now());
    const correct = questions[qIndex].correct;
    const isCorrect = opt === correct;
    const points = isCorrect ? Math.max(500, 1000 - Math.floor(ms / 20)) : 0;

    setSelected(opt);
    setShowResult(true);
    setScore((s) => s + points);
    setAnswers((prev) => [...prev, { question_index: qIndex, option: opt, correct: isCorrect }]);
  };

  const nextQ = () => {
    if (qIndex + 1 >= questions.length) {
      setStep('done');
      setTimeout(() => fireCelebration(), 400);
      return;
    }
    setQIndex((i) => i + 1);
    setSelected(null);
    setShowResult(false);
    setTimer(20);
    startTimeRef.current = Date.now();
  };

  // ===== SEARCH =====
  if (step === 'search') {
    return (
      <div className="min-h-screen px-5 py-8 relative z-10 max-w-lg mx-auto">
        <button
          data-testid="back-btn"
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft size={18} /> Back
        </button>

        <h2 data-testid="solo-title" className="text-2xl font-bold mb-1" style={{ color: '#00FF29' }}>
          Solo Quiz
        </h2>
        <p className="text-gray-500 text-sm mb-6">Pick a Binance Academy topic to quiz yourself</p>

        <div className="flex gap-2 mb-6">
          <input
            data-testid="solo-search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchAcademy()}
            placeholder="e.g. Ethereum, Staking, Web3..."
            className="flex-1 h-12 px-4 rounded-xl text-white placeholder:text-gray-600 outline-none"
            style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
          />
          <button
            data-testid="solo-search-btn"
            onClick={searchAcademy}
            disabled={searching}
            className="h-12 px-5 rounded-xl font-semibold flex items-center gap-2 active:scale-95 transition-all"
            style={{ background: '#00FF29', color: '#000' }}
          >
            {searching ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
          </button>
        </div>

        {generating && (
          <div className="flex flex-col items-center py-16 gap-3">
            <Loader2 size={32} className="animate-spin" style={{ color: '#00FF29' }} />
            <p className="text-gray-400">Generating quiz...</p>
          </div>
        )}

        {!generating && (
          <div className="space-y-2">
            {results.map((r, i) => (
              <motion.button
                key={`${r.url}-${i}`}
                data-testid={`solo-article-${i}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                onClick={() => selectAndGenerate(r)}
                className="w-full text-left p-4 rounded-xl border flex items-center gap-3 transition-all hover:border-[#00FF29]/50 active:scale-[0.98]"
                style={{ background: '#121212', borderColor: '#27272A' }}
              >
                <BookOpen size={18} className="text-gray-500 shrink-0" />
                <span className="text-sm text-gray-200 line-clamp-2">{r.title}</span>
                <Play size={14} className="text-gray-600 shrink-0 ml-auto" />
              </motion.button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ===== PLAYING =====
  if (step === 'playing') {
    const q = questions[qIndex];
    if (!q) return null;
    const progress = timer / 20;
    const correctIdx = q.correct;

    return (
      <div className="min-h-screen flex flex-col px-4 py-6 relative z-10 max-w-lg mx-auto">
        <div className="flex items-center justify-between mb-4">
          <span className="text-gray-500 text-sm font-mono">{qIndex + 1}/{questions.length}</span>
          <div className="flex items-center gap-2">
            <Clock size={16} style={{ color: progress < 0.3 ? '#FF2E63' : '#00FF29' }} />
            <span className="text-xl font-bold font-mono" style={{ color: progress < 0.3 ? '#FF2E63' : '#00FF29' }}>
              {timer}
            </span>
          </div>
          <span className="text-sm font-mono" style={{ color: '#F3BA2F' }}>{score} pts</span>
        </div>

        <div className="w-full h-1.5 rounded-full mb-6" style={{ background: '#1E1E1E' }}>
          <motion.div
            className="h-full rounded-full"
            style={{ background: progress < 0.3 ? '#FF2E63' : '#00FF29' }}
            animate={{ width: `${progress * 100}%` }}
          />
        </div>

        <div className="rounded-2xl p-5 mb-5" style={{ background: '#121212', border: '1px solid #27272A' }}>
          <h3 data-testid="solo-question-text" className="text-lg md:text-xl font-semibold text-center leading-tight">
            {q.question}
          </h3>
        </div>

        <div className="grid grid-cols-1 gap-3 flex-1">
          {q.options.map((opt, i) => {
            const Icon = ICONS[i];
            const isSelected = selected === i;
            const isCorrectOpt = i === correctIdx;
            const showCorrect = showResult && isCorrectOpt;
            const showWrong = showResult && isSelected && !isCorrectOpt;

            let bg = `${COLORS[i]}20`;
            let borderColor = `${COLORS[i]}40`;
            let textColor = '#F2F3F5';

            if (showCorrect) {
              bg = '#00FF2940';
              borderColor = '#00FF29';
            } else if (showWrong) {
              bg = '#FF2E6340';
              borderColor = '#FF2E63';
            } else if (isSelected) {
              bg = COLORS[i];
              textColor = '#000';
              borderColor = COLORS[i];
            }

            return (
              <motion.button
                key={i}
                data-testid={`solo-option-${i}`}
                onClick={() => submitAnswer(i)}
                disabled={showResult}
                className="h-18 md:h-20 rounded-xl font-semibold text-base flex items-center gap-3 px-5 transition-all active:scale-[0.97]"
                style={{
                  background: bg,
                  border: `2px solid ${borderColor}`,
                  color: textColor,
                  borderBottom: `4px solid ${showCorrect ? '#00FF2950' : showWrong ? '#FF2E6350' : `${COLORS[i]}30`}`,
                  opacity: showResult && !isSelected && !isCorrectOpt ? 0.3 : 1,
                }}
              >
                <Icon size={18} fill={isSelected && !showResult ? '#000' : COLORS[i]} color={isSelected && !showResult ? '#000' : COLORS[i]} />
                <span className="text-left flex-1 break-words leading-snug">{opt}</span>
                {showCorrect && <Check size={18} color="#00FF29" />}
                {showWrong && <X size={18} color="#FF2E63" />}
              </motion.button>
            );
          })}
        </div>

        {showResult && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="mt-4">
            {q.explanation && (
              <p className="text-gray-500 text-xs text-center mb-3">{q.explanation}</p>
            )}
            <button
              data-testid="solo-next-btn"
              onClick={nextQ}
              className="w-full h-12 rounded-xl font-bold flex items-center justify-center gap-2 active:scale-95 transition-all"
              style={{ background: '#00FF29', color: '#000' }}
            >
              {qIndex + 1 >= questions.length ? 'See Results' : 'Next Question'}
            </button>
          </motion.div>
        )}
      </div>
    );
  }

  // ===== DONE =====
  if (step === 'done') {
    const correctCount = answers.filter((a) => a.correct).length;
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-5 py-8 relative z-10 max-w-md mx-auto">
        <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="text-center w-full">
          <Trophy size={48} style={{ color: '#F3BA2F' }} className="mx-auto mb-4 float-anim" />
          <h2 data-testid="solo-done-title" className="text-3xl font-bold mb-2" style={{ color: '#F3BA2F' }}>
            Quiz Complete!
          </h2>
          <p className="text-gray-400 mb-1">{articleTitle}</p>
          <p className="text-4xl font-bold font-mono mb-2" style={{ color: '#00FF29' }}>
            {score}
          </p>
          <p className="text-gray-500 mb-6">
            {correctCount}/{questions.length} correct
          </p>

          <div className="rounded-xl p-4 mb-6" style={{ background: '#121212', border: '1px solid #27272A' }}>
            {questions.map((q, i) => {
              const a = answers[i];
              return (
                <div key={i} className="flex items-center gap-2 py-2 border-b border-[#27272A] last:border-0">
                  {a?.correct ? (
                    <Check size={14} color="#00FF29" className="shrink-0" />
                  ) : (
                    <X size={14} color="#FF2E63" className="shrink-0" />
                  )}
                  <span className="text-sm text-gray-300 text-left line-clamp-1">{q.question}</span>
                </div>
              );
            })}
          </div>

          <div className="flex gap-3">
            <button
              data-testid="solo-home-btn"
              onClick={() => navigate('/')}
              className="flex-1 h-12 rounded-xl font-semibold flex items-center justify-center gap-2 active:scale-95 transition-all"
              style={{ background: '#1E1E1E', border: '1px solid #27272A', color: '#F2F3F5' }}
            >
              <Home size={18} /> Home
            </button>
            <button
              data-testid="solo-retry-btn"
              onClick={() => {
                setStep('search');
                setQuestions([]);
                setQIndex(0);
                setScore(0);
                setAnswers([]);
                setSelected(null);
                setShowResult(false);
              }}
              className="flex-1 h-12 rounded-xl font-semibold flex items-center justify-center gap-2 active:scale-95 transition-all"
              style={{ background: '#00FF29', color: '#000' }}
            >
              <Play size={18} /> New Quiz
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  return null;
}
