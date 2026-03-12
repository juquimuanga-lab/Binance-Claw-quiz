import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, ArrowLeft, Loader2, BookOpen, Sparkles } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;
const tgUser = window.Telegram?.WebApp?.initDataUnsafe?.user;

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
  const [step, setStep] = useState('search'); // search, article, name

  const searchAcademy = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API}/api/academy/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data.results || []);
      if (!data.results?.length) toast.info('No results found. Try different keywords.');
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const selectArticle = async (article) => {
    setSelectedArticle(article);
    setFetchingContent(true);
    try {
      const res = await fetch(`${API}/api/academy/article`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: article.url }),
      });
      const data = await res.json();
      setArticleContent(data);
      setStep('name');
    } catch {
      toast.error('Failed to fetch article');
    } finally {
      setFetchingContent(false);
    }
  };

  const generateAndCreate = async () => {
    if (!hostName.trim()) {
      toast.error('Enter your name');
      return;
    }
    setGenerating(true);
    try {
      const quizRes = await fetch(`${API}/api/quiz/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          article_url: selectedArticle.url,
          article_title: articleContent?.title || selectedArticle.title,
          article_content: articleContent?.content || '',
          num_questions: 10,
        }),
      });
      if (!quizRes.ok) throw new Error('Quiz generation failed');
      const quiz = await quizRes.json();

      const sessionRes = await fetch(`${API}/api/session/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ host_name: hostName, quiz_id: quiz.quiz_id }),
      });
      if (!sessionRes.ok) throw new Error('Session creation failed');
      const session = await sessionRes.json();

      navigate(`/game/${session.code}?role=host`);
    } catch (err) {
      toast.error(err.message || 'Something went wrong');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="min-h-screen px-5 py-8 relative z-10 max-w-lg mx-auto">
      <button
        data-testid="back-btn"
        onClick={() => (step === 'name' ? setStep('search') : navigate('/'))}
        className="flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition-colors"
      >
        <ArrowLeft size={18} /> Back
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
                className="flex-1 h-12 px-4 rounded-xl text-white placeholder:text-gray-600 outline-none transition-all"
                style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
              />
              <button
                data-testid="search-btn"
                onClick={searchAcademy}
                disabled={searching}
                className="h-12 px-5 rounded-xl font-semibold flex items-center gap-2 active:scale-95 transition-all"
                style={{ background: '#F3BA2F', color: '#000' }}
              >
                {searching ? <Loader2 size={18} className="animate-spin" /> : <Search size={18} />}
              </button>
            </div>

            {fetchingContent && (
              <div className="flex items-center justify-center py-20 gap-3">
                <Loader2 size={24} className="animate-spin" style={{ color: '#F3BA2F' }} />
                <span className="text-gray-400">Fetching article...</span>
              </div>
            )}

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
              className="w-full h-12 px-4 rounded-xl text-white placeholder:text-gray-600 outline-none mb-6"
              style={{ background: '#0A0A0A', border: '1px solid #27272A' }}
            />

            <button
              data-testid="generate-quiz-btn"
              onClick={generateAndCreate}
              disabled={generating}
              className="w-full h-14 rounded-xl font-bold text-lg flex items-center justify-center gap-3 active:scale-95 transition-all disabled:opacity-50"
              style={{ background: '#F3BA2F', color: '#000' }}
            >
              {generating ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Generating Quiz...
                </>
              ) : (
                <>
                  <Sparkles size={20} />
                  Generate Quiz & Start
                </>
              )}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
