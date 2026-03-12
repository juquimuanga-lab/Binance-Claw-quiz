import React, { useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useSearchParams } from "react-router-dom";
import { Toaster } from "sonner";
import HomePage from "@/pages/HomePage";
import HostPage from "@/pages/HostPage";
import JoinPage from "@/pages/JoinPage";
import GamePage from "@/pages/GamePage";
import SoloPage from "@/pages/SoloPage";

function TelegramRedirect({ children }) {
  const [searchParams] = useSearchParams();
  const joinCode = searchParams.get('join');

  useEffect(() => {
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.ready();
      window.Telegram.WebApp.expand();
    }
  }, []);

  if (joinCode) {
    return <Navigate to={`/join?code=${joinCode}`} replace />;
  }

  const startParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
  if (startParam) {
    return <Navigate to={`/join?code=${startParam}`} replace />;
  }

  return children;
}

function App() {
  return (
    <div className="App">
      <div className="bg-noise" />
      <Toaster
        data-testid="global-toaster"
        richColors
        position="top-center"
        theme="dark"
        toastOptions={{
          style: { background: '#1E1E1E', border: '1px solid #27272A', color: '#F2F3F5' }
        }}
      />
      <BrowserRouter>
        <TelegramRedirect>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/host" element={<HostPage />} />
            <Route path="/join" element={<JoinPage />} />
            <Route path="/game/:code" element={<GamePage />} />
            <Route path="/solo" element={<SoloPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </TelegramRedirect>
      </BrowserRouter>
    </div>
  );
}

export default App;
