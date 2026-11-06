import { useEffect, useState } from 'react';
import { consultar } from '../services/comunicacionService';

export function useComunicacionResource(path) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setStatus(null);
    setResult(null);
    consultar(path).then(data => { if (active) setResult(data); })
      .catch(err => { if (active) { setError(err.message); setStatus(err.status); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [path, revision]);
  return { result, error, status, loading, reload: () => setRevision(n => n + 1) };
}
