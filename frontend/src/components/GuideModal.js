import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Search, Users, Zap, Clock, Trophy, ArrowRight, User, Share2 } from 'lucide-react';

const sections = [
  {
    id: 'host',
    title: 'Host a Quiz',
    icon: Zap,
    color: '#F3BA2F',
    steps: [
      { icon: Search, text: 'Search any crypto topic from Binance Academy' },
      { icon: ArrowRight, text: 'Select an article and generate AI-powered questions' },
      { icon: Share2, text: 'Share the game code with your friends' },
      { icon: Zap, text: 'Start the game and control the flow as host' },
    ],
  },
  {
    id: 'join',
    title: 'Join a Game',
    icon: Users,
    color: '#00F0FF',
    steps: [
      { icon: Users, text: 'Get the game code from your host' },
      { icon: User, text: 'Enter the code and pick a nickname' },
      { icon: Clock, text: 'Answer each question before the timer runs out' },
      { icon: Trophy, text: 'Compete for the top spot on the leaderboard' },
    ],
  },
  {
    id: 'solo',
    title: 'Solo Mode',
    icon: User,
    color: '#00FF29',
    steps: [
      { icon: Search, text: 'Search and pick any Binance Academy topic' },
      { icon: Zap, text: 'AI generates a custom quiz just for you' },
      { icon: Clock, text: 'Race against the clock on each question' },
      { icon: Trophy, text: 'Review your results and learn from explanations' },
    ],
  },
];

const scoringRules = [
  { label: 'Correct + Fast', value: 'Up to 1,000 pts', color: '#00FF29' },
  { label: 'Correct + Slow', value: '500 pts minimum', color: '#F3BA2F' },
  { label: 'Incorrect', value: '0 pts', color: '#FF2E63' },
  { label: 'No Answer', value: '0 pts', color: '#666' },
];

export default function GuideModal({ isOpen, onClose }) {
  const [activeSection, setActiveSection] = useState('host');

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
        style={{ background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)' }}
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 60, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 60, opacity: 0 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className="w-full max-w-md max-h-[85vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl relative"
          style={{ background: '#0A0A0A', border: '1px solid #1E1E1E' }}
          onClick={(e) => e.stopPropagation()}
          data-testid="guide-modal"
        >
          {/* Header */}
          <div className="sticky top-0 z-10 px-6 pt-6 pb-4" style={{ background: '#0A0A0A' }}>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-xl font-bold" style={{ color: '#F3BA2F' }}>
                How to Play
              </h2>
              <button
                data-testid="guide-close-btn"
                onClick={onClose}
                className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
                style={{ background: '#1E1E1E' }}
              >
                <X size={16} className="text-gray-400" />
              </button>
            </div>
            <p className="text-gray-500 text-sm">Everything you need to know</p>
          </div>

          <div className="px-6 pb-6">
            {/* Section Tabs */}
            <div className="flex gap-2 mb-6">
              {sections.map((s) => (
                <button
                  key={s.id}
                  data-testid={`guide-tab-${s.id}`}
                  onClick={() => setActiveSection(s.id)}
                  className="flex-1 py-2.5 rounded-xl text-xs font-semibold transition-all"
                  style={{
                    background: activeSection === s.id ? `${s.color}15` : '#121212',
                    border: `1px solid ${activeSection === s.id ? `${s.color}50` : '#1E1E1E'}`,
                    color: activeSection === s.id ? s.color : '#666',
                  }}
                >
                  {s.title}
                </button>
              ))}
            </div>

            {/* Active Section Steps */}
            {sections
              .filter((s) => s.id === activeSection)
              .map((section) => (
                <div key={section.id} className="mb-8">
                  <div className="space-y-3">
                    {section.steps.map((step, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.08 }}
                        className="flex items-start gap-3 p-3 rounded-xl"
                        style={{ background: '#121212' }}
                      >
                        <div
                          className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                          style={{ background: `${section.color}12` }}
                        >
                          <span
                            className="text-xs font-bold"
                            style={{ color: section.color }}
                          >
                            {i + 1}
                          </span>
                        </div>
                        <p className="text-sm text-gray-300 leading-relaxed">
                          {step.text}
                        </p>
                      </motion.div>
                    ))}
                  </div>
                </div>
              ))}

            {/* Scoring */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
                Scoring
              </h3>
              <div className="rounded-xl overflow-hidden" style={{ border: '1px solid #1E1E1E' }}>
                {scoringRules.map((rule, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between px-4 py-3"
                    style={{
                      background: '#121212',
                      borderBottom: i < scoringRules.length - 1 ? '1px solid #1E1E1E' : 'none',
                    }}
                  >
                    <span className="text-sm text-gray-400">{rule.label}</span>
                    <span className="text-sm font-mono font-semibold" style={{ color: rule.color }}>
                      {rule.value}
                    </span>
                  </div>
                ))}
              </div>
              <p className="text-gray-600 text-xs mt-2">
                Speed matters. The faster you answer correctly, the more points you earn.
              </p>
            </div>

            {/* Tips */}
            <div>
              <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
                Tips
              </h3>
              <div className="space-y-2">
                {[
                  'Read the full question before answering',
                  'Speed bonus rewards quick correct answers',
                  'Use Solo Mode to practice before competing',
                  'Host can control the pace between questions',
                ].map((tip, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-3 px-4 py-2.5 rounded-lg"
                    style={{ background: '#121212' }}
                  >
                    <div className="w-1 h-1 rounded-full shrink-0" style={{ background: '#F3BA2F' }} />
                    <span className="text-xs text-gray-400">{tip}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
