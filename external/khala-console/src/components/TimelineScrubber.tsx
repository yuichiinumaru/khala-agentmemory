import React from 'react';

export interface TimelineEvent {
  time: number;
  type: string; // 'job' | 'error' | 'user'
  id: string;
}

interface TimelineScrubberProps {
  startTime: number;
  endTime: number;
  currentTime: number;
  events: TimelineEvent[];
  onChange: (time: number) => void;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  startTime, endTime, currentTime, events, onChange
}) => {
  const range = endTime - startTime;

  const getPercentage = (time: number) => {
      if (range <= 0) return 0;
      return Math.max(0, Math.min(100, ((time - startTime) / range) * 100));
  };

  return (
    <div className="relative w-full h-12 bg-black/50 border-t border-white/10 mt-auto pointer-events-auto select-none">
       {/* Events Layer */}
       <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-2 pointer-events-none">
          {events.map(ev => (
              <div
                key={ev.id}
                className={`event-marker absolute w-2 h-2 rounded-full -ml-1 ${ev.type === 'error' ? 'bg-red-500' : 'bg-neon-blue'}`}
                style={{ left: `${getPercentage(ev.time)}%` }}
                title={`${ev.type} at ${ev.time}`}
              />
          ))}
       </div>

       {/* Slider Input */}
       <input
          type="range"
          min={startTime}
          max={endTime}
          value={currentTime}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-full opacity-0 z-20 absolute top-0 left-0 cursor-pointer"
          aria-label="Timeline"
       />

       {/* Custom Track Visuals (Playhead) */}
       <div className="absolute inset-0 pointer-events-none">
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-neon-purple transition-all duration-75"
            style={{ left: `${getPercentage(currentTime)}%` }}
          />
       </div>

       <div className="absolute top-0 left-2 text-[10px] font-mono text-white/30">
          {new Date(startTime).toLocaleTimeString()}
       </div>
       <div className="absolute top-0 right-2 text-[10px] font-mono text-white/30">
          {new Date(endTime).toLocaleTimeString()}
       </div>
    </div>
  );
};
