import React from 'react';

interface EntropyGaugeProps {
  value: number;
  min?: number;
  max?: number;
  label?: string;
  className?: string;
}

export const EntropyGauge: React.FC<EntropyGaugeProps> = ({
  value, min = 0, max = 10, label = 'Entropy', className = ''
}) => {
  const normalized = Math.min(Math.max((value - min) / (max - min), 0), 1);

  // Color interpolation: Green (low entropy/order) -> Red (high entropy/chaos)
  // Actually, for Working Memory, high entropy might be good (learning).
  // But for Long Term, low entropy is good (consolidated).
  // Let's assume standard "Green is Good" -> "Red is Bad/High".
  const getColor = (t: number) => {
      if (t < 0.5) return '#0aff60'; // Green
      if (t < 0.8) return '#ffff00'; // Yellow
      return '#ff0a5c'; // Red
  };

  const color = getColor(normalized);

  // Semi-circle length approx 126 (PI * 40)
  const arcLength = 126;

  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="relative w-24 h-12 overflow-hidden">
        <svg viewBox="0 0 100 50" className="w-full h-full">
           {/* Background Arc */}
           <path d="M 10 50 A 40 40 0 0 1 90 50" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" strokeLinecap="round" />
           {/* Fill Arc */}
           <path
             d="M 10 50 A 40 40 0 0 1 90 50"
             fill="none"
             stroke={color}
             strokeWidth="8"
             strokeLinecap="round"
             strokeDasharray={`${normalized * arcLength} ${arcLength}`}
             className="transition-all duration-500 ease-out entropy-meter-fill"
           />
        </svg>
        <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-white font-mono font-bold text-lg leading-none mb-1">
           {value.toFixed(2)}
        </div>
      </div>
      <span className="text-[10px] text-white/40 uppercase font-bold tracking-wider">{label}</span>
    </div>
  );
};
