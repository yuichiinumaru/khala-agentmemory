import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { SurrealProvider, useSurreal } from '../useSurreal';
import React from 'react';
import { Surreal } from 'surrealdb.js';

// Mock SurrealDB
vi.mock('surrealdb.js', () => {
  const SurrealMock = vi.fn();
  SurrealMock.prototype.connect = vi.fn().mockResolvedValue(true);
  SurrealMock.prototype.use = vi.fn().mockResolvedValue(true);
  SurrealMock.prototype.signin = vi.fn().mockResolvedValue('token');
  SurrealMock.prototype.authenticate = vi.fn().mockResolvedValue(true);
  SurrealMock.prototype.close = vi.fn().mockResolvedValue(true);
  SurrealMock.prototype.query = vi.fn().mockResolvedValue([]);
  return { Surreal: SurrealMock };
});

describe('useSurreal Hook', () => {
  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <SurrealProvider url="ws://localhost:8000" ns="khala" db="memory">
      {children}
    </SurrealProvider>
  );

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should connect on mount', async () => {
    const { result } = renderHook(() => useSurreal(), { wrapper });

    expect(result.current.client).toBeInstanceOf(Surreal);

    // Wait for async effect
    await waitFor(() => {
        expect(result.current.status).toBe('connected');
    });
  });
});
