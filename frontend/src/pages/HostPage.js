import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ArrowLeft, Loader2, BookOpen, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';

const API =
  process.env.REACT_APP_BACKEND_URL ||
  "https://binance-claw-quiz-api.onrender.com";
const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;

const LOADING_MESSAGES = [
  'Fetching article content...',
  'Analyzing the topic...',
  'Almost there...',
];

const GEN_MESSAGES = [
  'Generating quiz questions with AI...',
  'Crafting challenging options...',
  'Polishing the quiz...',
  'Almost ready...',
];

export default function HostPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [articleContent, setArticleContent] = useState(null);
  const [fetchingContent, setFetchingContent] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [hostName, setHostName] = useState(tgUser?.first_name || '');
  const [step, setStep] = useState('search');
  const [loadingMsg, setLoadingMsg] = useState('');
  const [elapsed, setElapsed] = useState(0);

  const abortRef = useRef(null);
  const timerRef = useRef(null);
  const msgRef = useRef(null);

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
      clearInterval(timerRef.current);
      clearInterval(msgRef.current);
    };
  }, []);

  const startProgress = (messages) => {
    setElapsed(0);
    let idx = 0;
    setLoadingMsg(messages[0]);
    clearInterval(timerRef.current);
    clearInterval(msgRef.current);
    timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
    msgRef.current = setInterval(() => {
      idx = Math.min(idx + 1, messages.length - 1);
      setLoadingMsg(messages[idx]);
    }, 5000);
  };

  const stopProgress = () => {
    clearInterval(timerRef.current);
    clearInterval(msgRef.current);
    setElapsed(0);
    setLoadingMsg('');
  };

  const cancelOperation = () => {
    if (abortRef.current) abortRef.current.abort();
    stopProgress();
    setFetchingContent(false);
    setGenerating(false);
    setSelectedArticle(null);
    toast.info('Cancelled');
  };

  const searchAcademy = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API}/api/academy/search?q=${encodeURIComponent(query)}`, {
        signal: AbortSignal.timeout(20000),
      });
      const data = await res.json();
      setResults(data.results || []);
      if (!data.results?.length) toast.info('No results found. Try different keywords.');
    } catch (err) {
      if (err.name !== 'AbortError') toast.error('Search failed. Try again.');
    } finally {
      setSearching(false);
    }
  };

  const selectArticle = async (article) => {
    if (!article?.url) {
      toast.error('Invalid article');
      return;
    }
    setSelectedArticle(article);
    setFetchingContent(true);
    startProgress(LOADING_MESSAGES);

    abortRef.current = new AbortController();
    try {
      const res = await fetch(`${API}/api/academy/article`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: String(article.url) }),
        signal: abortRef.current.signal,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to fetch article');
      }
      const data = await res.json();
      setArticleContent(data);
      setStep('name');
    } catch (err) {
      if (err.name !== 'AbortError') {
        toast.error(err.message || 'Failed to fetch article. Try another topic.');
        setSelectedArticle(null);
      }
    } finally {
      setFetchingContent(false);
      stopProgress();
    }
  };

  // ✅ FIXED: single call to session/create — no more double quiz generation
  const generateAndCreate = async () => {
    if (!hostName.trim()) {
      toast.error('Enter your name');
      return;
    }
    setGenerating(true);
    startProgress(GEN_MESSAGES);

    abortRef.current = new AbortController();
    try {
      const sessionRes = await fetch(`${API}/api/session/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article_url: selectedArticle.url,
          article_title: articleContent?.title || selectedArticle?.title,
          article_content: articleContent?.content || null,
          num_questions: 10,
        }),
        signal: abortRef.current.signal,
      });

      if (!sessionRes.ok) {
        const errData = await sessionRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Session creation failed');
      }

      const session = await sessionRes.json();
      // ✅ pid included so GamePage correctly identifies the host
      navigate(`/game/${session.code}?role=host&pid=host_${session.code}`);

    } catch (err) {
      if (err.name !== 'AbortError') {
        toast.error(err.message || 'Something went wrong');
      }
    } finally {
      setGenerating(false);
      stopProgress();
    }
  };

  const isLoading = fetchingContent || generating;

  return (
    <div className="min-h-screen px-5 py-8 relative z-10 max-w-lg mx-auto">
      <button
        data-testid="back-btn"
        onClick={() => {
          if (isLoading) {
            cancelOperation();
          } else if (step === 'name') {
            setStep('search');
          } else {
            navigate('/');
          }
        }}
        className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} /> {isLoading ? 'Cancel' : 'Back'}
      </button>

      <AnimatePresence mode="wait">
        {step === 'search' && (
          <motion.div key="search" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <h2 data-testid="host-title" className="text-2xl font-bold mb-1" style={{ color: '#F3BA2F' }}>
              Create a Quiz
            </h2>
            <p className="text-gray-500 text-sm mb-6">Search Binance Academy for a topic</p>

            <div className="flex gap-2 mb-6">
              <input
                data-testid="search-input"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && searchAcademy()}
                placeholder="e.g. Bitcoin, DeFi, NFT..."
                disabled={isLoading}
                className="flex-1 h-12 px-4 rounded-xl text-white placeholder:text-gray-600 outline-none transition-all disabled:opacity-50"
                style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
              />
              <button
                data-testid="search-btn"
                onClick={searchAcademy}
                disabled={searching || isLoading}
                className="h-12 px-5 rounded-xl font-semibold flex items-center gap-2 active:scale-95 transition-all disabled:opacity-50"
                style={{ background: '#F3BA2F', color: '#000' }}
              >
                {searching ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
              </button>
            </div>

            {fetchingContent && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center py-16 gap-4"
              >
                <Loader2 size={32} className="animate-spin" style={{ color: '#F3BA2F' }} />
                <p className="text-gray-300 text-sm">{loadingMsg}</p>
                <p className="text-gray-600 text-xs">{elapsed}s</p>
                <button
                  data-testid="cancel-fetch-btn"
                  onClick={cancelOperation}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white transition-colors mt-2"
                  style={{ background: '#1E1E1E', border: '1px solid #27272A' }}
                >
                  <X size={14} /> Cancel
                </button>
              </motion.div>
            )}

            {!fetchingContent && (
              <div className="space-y-2">
                {results.map((r, i) => (
                  <motion.button
                    key={`${r.url}-${i}`}
                    data-testid={`article-result-${i}`}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => selectArticle(r)}
                    className="w-full text-left p-4 rounded-xl border flex items-center gap-3 transition-all hover:border-[#F3BA2F]/50 active:scale-[0.98]"
                    style={{ background: '#121212', borderColor: '#27272A' }}
                  >
                    <BookOpen size={18} className="text-gray-500 shrink-0" />
                    <span className="text-sm text-gray-200 line-clamp-2">{r.title}</span>
                  </motion.button>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {step === 'name' && (
          <motion.div key="name" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <h2 className="text-2xl font-bold mb-1" style={{ color: '#F3BA2F' }}>
              Almost Ready!
            </h2>
            <p className="text-gray-500 text-sm mb-2">
              Topic: <span className="text-gray-300">{articleContent?.title || selectedArticle?.title}</span>
            </p>
            <p className="text-gray-600 text-xs mb-6 line-clamp-3">
              {articleContent?.content?.substring(0, 200)}...
            </p>

            <label className="text-gray-400 text-sm mb-2 block">Your Name</label>
            <input
              data-testid="host-name-input"
              value={hostName}
              onChange={(e) => setHostName(e.target.value)}
              placeholder="Enter your name"
              disabled={generating}
              className="w-full h-12 px-4 rounded-xl text-white placeholder:text-gray-600 outline-none mb-6 disabled:opacity-50"
              style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
            />

            {generating ? (
              <div className="w-full flex flex-col items-center gap-3 py-4">
                <button
                  data-testid="generate-quiz-btn"
                  disabled
                  className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 opacity-80"
                  style={{ background: '#F3BA2F', color: '#000' }}
                >
                  <Loader2 size={20} className="animate-spin" />
                  {loadingMsg || 'Generating...'}
                </button>
                <div className="flex items-center gap-3">
                  <p className="text-gray-600 text-xs">{elapsed}s</p>
                  <button
                    data-testid="cancel-generate-btn"
                    onClick={cancelOperation}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
                  >
                    <X size={12} /> Cancel
                  </button>
                </div>
              </div>
            ) : (
              <button
                data-testid="generate-quiz-btn"
                onClick={generateAndCreate}
                className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all"
                style={{ background: '#F3BA2F', color: '#000' }}
              >
                <Sparkles size={20} />
                Generate Quiz & Start
              </button>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
