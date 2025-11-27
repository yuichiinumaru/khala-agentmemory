import React, { useEffect, useState, useRef } from 'react';
import { Cpu } from 'lucide-react';

export const FpsMeter: React.FC = () => {
  const [fps, setFps] = useState(0);
  const frameCount = useRef(0);
  const lastTime = useRef(performance.now());

  useEffect(() => {
    let animationFrameId: number;

    const loop = (time: number) => {
      frameCount.current++;
      if (time - lastTime.current >= 1000) {
        setFps(frameCount.current);
        frameCount.current = 0;
        lastTime.current = time;
      }
      animationFrameId = requestAnimationFrame(loop);
    };

    animationFrameId = requestAnimationFrame(loop);

    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  // Color coding based on performance
  const getColor = () => {
    if (fps >= 50) return 'text-neon-green';
    if (fps >= 30) return 'text-neon-blue';
    return 'text-neon-purple'; // Danger/Warning aesthetic
  };

  return (
    <div className="flex items-center gap-2 bg-black/40 backdrop-blur-md px-3 py-1 rounded border border-white/5">
      <Cpu size={14} className={getColor()} />
      <span className={`font-mono text-xs font-bold ${getColor()}`}>
        {fps} FPS
      </span>
    </div>
  );
};