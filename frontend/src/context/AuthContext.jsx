import { createContext, useContext, useState, useEffect } from 'react';
import { onAuthChange, syncWithBackend } from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let version = 0;
    let active = true;
    const unsubscribe = onAuthChange(async (firebaseUser) => {
      const current = ++version;
      setLoading(true);
      if (firebaseUser) {
        try {
          const idToken = await firebaseUser.getIdToken();
          if (!active || current !== version) return;
          await syncWithBackend(idToken);
          if (active && current === version) setUser(firebaseUser);
        } catch (error) {
          console.error('Error syncing with backend:', error);
          if (active && current === version) setUser(null);
        }
      } else {
        setUser(null);
      }
      if (active && current === version) setLoading(false);
    });

    return () => { active = false; version++; unsubscribe(); };
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
