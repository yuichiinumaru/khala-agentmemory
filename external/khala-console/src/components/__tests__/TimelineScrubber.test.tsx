import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { TimelineScrubber } from '../TimelineScrubber';
import React from 'react';

describe('TimelineScrubber', () => {
  const props = {
    startTime: 1000,
    endTime: 2000,
    currentTime: 1500,
    events: [
        { time: 1200, type: 'job', id: '1' },
        { time: 1800, type: 'error', id: '2' }
    ],
    onChange: vi.fn()
  };

  it('should render slider with correct range', () => {
    render(<TimelineScrubber {...props} />);
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('min', '1000');
    expect(slider).toHaveAttribute('max', '2000');
    expect(slider).toHaveValue('1500');
  });

  it('should call onChange when moved', () => {
    render(<TimelineScrubber {...props} />);
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '1600' } });
    expect(props.onChange).toHaveBeenCalledWith(1600);
  });

  it('should render event markers', () => {
     const { container } = render(<TimelineScrubber {...props} />);
     // Using class selector
     const markers = container.querySelectorAll('.event-marker');
     expect(markers.length).toBe(2);

     // 1200 is 200 from start (1000). Range is 1000. So 20%.
     // Style checking can be tricky with jsdom/inline styles but generally works
     expect(markers[0]).toHaveStyle({ left: '20%' });
  });
});
