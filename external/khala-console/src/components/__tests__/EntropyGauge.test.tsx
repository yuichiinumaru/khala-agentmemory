import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { EntropyGauge } from '../EntropyGauge';
import React from 'react';

describe('EntropyGauge', () => {
  it('should render value and label', () => {
    render(<EntropyGauge value={3.5} label="Entropy" />);
    expect(screen.getByText('3.50')).toBeInTheDocument(); // Expect formatting
    expect(screen.getByText('Entropy')).toBeInTheDocument();
  });
});
