import { useEffect, useMemo, useState } from 'react';

export function useSystemMonitoring({ wsSystemStatus, connectionStats }) {
  const [restStatus, setRestStatus] = useState(null);
  const [restMetrics, setRestMetrics] = useState(null);

  useEffect(() => {
    const backend = process.env.REACT_APP_BACKEND_URL || '';
    if (!backend) return;

    let statusTimer = null;
    let metricsTimer = null;

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${backend}/api/status`);
        if (res.ok) setRestStatus(await res.json());
      } catch (e) {
        // silent fallback
      }
    };

    const fetchMetrics = async () => {
      try {
        const res = await fetch(`${backend}/api/metrics`);
        if (res.ok) setRestMetrics(await res.json());
      } catch (e) {
        // silent fallback
      }
    };

    fetchStatus();
    fetchMetrics();

    const onFocus = () => { fetchStatus(); fetchMetrics(); };
    window.addEventListener('focus', onFocus);
    statusTimer = setInterval(fetchStatus, 30000);
    metricsTimer = setInterval(fetchMetrics, 60000);

    return () => {
      if (statusTimer) clearInterval(statusTimer);
      if (metricsTimer) clearInterval(metricsTimer);
      window.removeEventListener('focus', onFocus);
    };
  }, []);

  const combined = useMemo(() => ({
    ws: wsSystemStatus || {},
    rest: restStatus || {},
    metrics: restMetrics || {}
  }), [wsSystemStatus, restStatus, restMetrics]);

  return combined;
}
