import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe } from 'lucide-react';
import { LANGUAGES } from '@/i18n/translations';
import { useLanguage } from '@/context/LanguageContext';

export default function LanguageToggle() {
  const { langCode, setLanguage } = useLanguage();
  const [open, setOpen] = useState(false);
  const current = LANGUAGES.find(l => l.code === langCode) || LANGUAGES[0];

  return (
    <div className="fixed top-4 right-4 z-50">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold transition-all active:scale-95"
        style={{ background: '#121212', border: '1px solid #27272A', color: '#F3BA2F' }}
      >
        <Globe size={15} />
        <span>{current.flag}</span>
        <span className="hidden sm:inline text-xs text-gray-400">{current.label}</span>
      </button>

      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
            />

            {/* Dropdown */}
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: -8 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: -8 }}
              className="absolute right-0 top-12 z-50 rounded-2xl overflow-hidden shadow-2xl"
              style={{
                background: '#121212',
                border: '1px solid #27272A',
                width: '220px',
                maxHeight: '70vh',
                overflowY: 'auto',
              }}
            >
              <p className="text-gray-500 text-xs px-4 pt-3 pb-2 uppercase tracking-widest">
                Language
              </p>
              {LANGUAGES.map(lang => (
                <button
                  key={lang.code}
                  onClick={() => { setLanguage(lang.code); setOpen(false); }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-white/5"
                  style={{
                    background: langCode === lang.code ? '#F3BA2F15' : 'transparent',
                    color: langCode === lang.code ? '#F3BA2F' : '#9CA3AF',
                  }}
                >
                  <span className="text-lg">{lang.flag}</span>
                  <span className="text-sm">{lang.label}</span>
                  {langCode === lang.code && (
                    <span className="ml-auto text-xs" style={{ color: '#F3BA2F' }}>✓</span>
                  )}
                </button>
              ))}
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
