import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';
import { Surreal } from 'surrealdb.js';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface SurrealContextType {
  client: Surreal;
  status: ConnectionStatus;
  error: Error | null;
}

const SurrealContext = createContext<SurrealContextType | null>(null);

interface SurrealProviderProps {
  children: React.ReactNode;
  url: string;
  ns?: string;
  db?: string;
  user?: string;
  pass?: string;
  token?: string;
}

export const SurrealProvider: React.FC<SurrealProviderProps> = ({
  children, url, ns, db, user, pass, token
}) => {
  // Memoize client to prevent recreation on every render
  const client = useMemo(() => new Surreal(), []);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;

    const connect = async () => {
      setStatus('connecting');
      try {
        await client.connect(url);

        if (token) {
           await client.authenticate(token);
        } else if (user && pass) {
           await client.signin({ username: user, password: pass });
        }

        if (ns && db) {
          await client.use({ ns, db });
        }

        if (mounted) {
          setStatus('connected');
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setStatus('error');
          setError(err instanceof Error ? err : new Error(String(err)));
          console.error("SurrealDB Connection Error:", err);
        }
      }
    };

    connect();

    return () => {
      mounted = false;
      client.close();
      setStatus('disconnected');
    };
  }, [client, url, ns, db, user, pass, token]);

  return (
    <SurrealContext.Provider value={{ client, status, error }}>
      {children}
    </SurrealContext.Provider>
  );
};

export const useSurreal = () => {
  const context = useContext(SurrealContext);
  if (!context) {
    throw new Error('useSurreal must be used within a SurrealProvider');
  }
  return context;
};
