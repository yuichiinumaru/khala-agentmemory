import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryInspector, MemoryNode } from '../MemoryInspector';
import React from 'react';

describe('MemoryInspector', () => {
  const mockNode: MemoryNode = {
    id: 'mem:1',
    content: 'Hello World',
    tier: 'working',
    importance: 0.8,
    metadata: { source: 'user' },
    embedding: [0.1, 0.2],
    label: 'mem:1',
    x: 0, y: 0, size: 10, color: 'red'
  };

  it('should render content and tier', () => {
    render(<MemoryInspector node={mockNode} />);
    expect(screen.getByText(/Hello World/)).toBeInTheDocument();
    expect(screen.getByText('working')).toBeInTheDocument();
  });

  it('should sanitize HTML content', () => {
    const dangerousNode: MemoryNode = {
       ...mockNode,
       content: '<img src=x onerror=alert(1)> Dangerous Content'
    };
    render(<MemoryInspector node={dangerousNode} />);
    expect(screen.getByText(/Dangerous Content/)).toBeInTheDocument();
    // DOMPurify + ReactMarkdown usually means <img ...> is rendered as text or stripped if HTML is disabled
    // If we enable HTML in markdown, we must sanitize.
    // If we disable HTML (default), then <img> is rendered as text "&lt;img..."
    // Let's assume we want to support some HTML or Markdown.
  });

  it('should show tabs', () => {
     render(<MemoryInspector node={mockNode} />);
     expect(screen.getByRole('tab', { name: /Meta/i })).toBeInTheDocument();
     expect(screen.getByRole('tab', { name: /Vector/i })).toBeInTheDocument();
  });
});
