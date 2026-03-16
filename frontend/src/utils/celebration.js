import confetti from 'canvas-confetti';

const GOLD = '#F3BA2F';
const CYAN = '#00F0FF';
const GREEN = '#00FF29';
const RED = '#FF2E63';

export function fireCelebration() {
  const duration = 3000;
  const end = Date.now() + duration;

  const colors = [GOLD, CYAN, GREEN, '#FFFFFF'];

  // Initial big burst
  confetti({
    particleCount: 100,
    spread: 80,
    origin: { y: 0.6 },
    colors,
    startVelocity: 45,
    gravity: 0.8,
    ticks: 300,
  });

  // Side cannons
  setTimeout(() => {
    confetti({
      particleCount: 50,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.65 },
      colors,
      startVelocity: 40,
    });
    confetti({
      particleCount: 50,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.65 },
      colors,
      startVelocity: 40,
    });
  }, 300);

  // Sustained sparkles
  const interval = setInterval(() => {
    if (Date.now() > end) {
      clearInterval(interval);
      return;
    }
    confetti({
      particleCount: 8,
      spread: 100,
      origin: { x: Math.random(), y: Math.random() * 0.4 },
      colors: [GOLD, '#FFFFFF'],
      startVelocity: 15,
      gravity: 0.6,
      scalar: 0.8,
      ticks: 150,
    });
  }, 200);

  // Final flourish
  setTimeout(() => {
    confetti({
      particleCount: 80,
      spread: 120,
      origin: { y: 0.5 },
      colors,
      startVelocity: 30,
      gravity: 1,
      shapes: ['circle', 'square'],
    });
  }, 1500);
}

export function fireClap() {
  // Quick celebratory burst for correct answers
  confetti({
    particleCount: 30,
    spread: 60,
    origin: { y: 0.7 },
    colors: [GOLD, GREEN],
    startVelocity: 25,
    gravity: 1.2,
    ticks: 120,
    scalar: 0.7,
  });
}
