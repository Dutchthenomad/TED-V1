import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { AlertCircle, TrendingUp, Clock, Target, Wifi, WifiOff } from 'lucide-react';

const CompactValue = ({ label, value, accent }) => (
  <div className="flex flex-col">
    <span className="text-[10px] text-gray-400">{label}</span>
    <span className={`text-sm font-semibold ${accent || ''}`}>{value}</span>
  </div>
);

const TreasuryPatternDashboard = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const [gameState, setGameState] = useState({
    gameId: 0,
    currentTick: 0,
    currentPrice: 1.0,
    isActive: false,
    isRugged: false,
    peak_price: 1.0,
  });

  const [patterns, setPatterns] = useState({});
  const [rugPrediction, setRugPrediction] = useState({ predicted_tick: 200, confidence: 0.5, tolerance: 50, based_on_patterns: [] });
  const [mlStatus, setMlStatus] = useState(null);

  const [connectionStats, setConnectionStats] = useState({ totalUpdates: 0, lastError: null, uptime: 0 });
  const [lastPayload, setLastPayload] = useState(null);

  const getBackendBase = () => {
    const base = process.env.REACT_APP_BACKEND_URL || '';
    return base.replace(/^http/i, 'ws');
  };

  const connectWebSocket = () => {
    try {
      const wsUrl = `${getBackendBase()}/api/ws`;
      wsRef.current = new WebSocket(wsUrl);
      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionStats(prev => ({ ...prev, lastError: null }));
      };
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.game_state) setGameState(prev => ({ ...prev, ...data.game_state }));
          if (data.patterns) setPatterns(data.patterns);
          if (data.prediction) setRugPrediction(data.prediction);
          if (data.ml_status) setMlStatus(data.ml_status);
          setLastPayload(data);
          setLastUpdate(new Date());
          setConnectionStats(prev => ({ ...prev, totalUpdates: prev.totalUpdates + 1 }));
        } catch (err) {
          setConnectionStats(prev => ({ ...prev, lastError: `Parse error: ${err.message}` }));
        }
      };
      wsRef.current.onerror = () => {
        setConnectionStats(prev => ({ ...prev, lastError: 'Connection error' }));
      };
      wsRef.current.onclose = () => {
        setIsConnected(false);
        reconnectTimeoutRef.current = setTimeout(() => { connectWebSocket(); }, 1500);
      };
    } catch (err) {
      setConnectionStats(prev => ({ ...prev, lastError: `Connection failed: ${err.message}` }));
    }
  };

  useEffect(() => {
    connectWebSocket();
    return () => { if (wsRef.current) wsRef.current.close(); if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current); };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => { if (isConnected) setConnectionStats(prev => ({ ...prev, uptime: prev.uptime + 1 })); }, 1000);
    return () => clearInterval(interval);
  }, [isConnected]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'TRIGGERED': return 'text-red-400';
      case 'MONITORING': return 'text-yellow-400';
      case 'APPROACHING': return 'text-orange-400';
      case 'NORMAL': return 'text-green-400';
      default: return 'text-gray-400';
    }
  };

  const PatternRow = ({ label, p }) => (
    <tr className="text-xs">
      <td className="px-2 py-1 text-gray-300">{label}</td>
      <td className={`px-2 py-1 font-semibold ${getStatusColor(p?.status)}`}>{p?.status || '—'}</td>
      <td className="px-2 py-1">{((p?.confidence || 0) * 100).toFixed(0)}%</td>
      <td className="px-2 py-1">{(p?.current_peak || p?.ultra_short_prob || p?.next_game_prob || 0).toFixed ? (p?.current_peak || 0).toFixed(1) : `${((p?.ultra_short_prob || p?.next_game_prob || 0) * 100).toFixed(1)}%`}</td>
      <td className="px-2 py-1">{p?.next_alert || p?.recovery_window || p?.last_trigger || '—'}</td>
    </tr>
  );

  return (
    <div className="min-h-screen bg-gray-900 text-white p-3">
      {/* Top Bar */}
      <div className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded px-3 py-2">
        <div className="flex items-center gap-3">
          {isConnected ? <Wifi className="w-4 h-4 text-green-500" /> : <WifiOff className="w-4 h-4 text-red-500" />}
          <span className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          <span className="text-xs text-gray-400">• Uptime {connectionStats.uptime}s</span>
          <span className="text-xs text-gray-400">• Updates {connectionStats.totalUpdates}</span>
          {lastUpdate && <span className="text-xs text-gray-500">• Last {lastUpdate.toLocaleTimeString()}</span>}
        </div>
        <div className="flex items-center gap-4">
          <CompactValue label="Game" value={`#${gameState.gameId}`} />
          <CompactValue label="Tick" value={gameState.currentTick} />
          <CompactValue label="Price" value={`${Number(gameState.currentPrice || 0).toFixed(3)}x`} />
        </div>
      </div>

      {/* Grid Debug Panels */}
      <div className="grid grid-cols-12 gap-2 mt-2">
        {/* Prediction Summary */}
        <div className="col-span-3 bg-gray-800 border border-gray-700 rounded p-2">
          <div className="text-xs font-semibold mb-2 flex items-center"><Target className="w-4 h-4 mr-1" /> Prediction</div>
          <div className="grid grid-cols-2 gap-2">
            <CompactValue label="Predicted Tick" value={rugPrediction.predicted_tick} accent="text-blue-400" />
            <CompactValue label="Tolerance" value={`±${rugPrediction.tolerance}`} accent="text-green-400" />
            <CompactValue label="Confidence" value={`${((rugPrediction.confidence || 0) * 100).toFixed(1)}%`} accent="text-yellow-400" />
            <CompactValue label="Remaining" value={Math.max(0, (rugPrediction.predicted_tick || 0) - (gameState.currentTick || 0))} accent="text-purple-400" />
          </div>
          <div className="mt-2 text-[10px] text-gray-400 truncate">Based on: {rugPrediction?.based_on_patterns?.join(', ')}</div>
        </div>

        {/* Live Bar */}
        <div className="col-span-5 bg-gray-800 border border-gray-700 rounded p-2">
          <div className="text-xs font-semibold mb-2">Live Tracking</div>
          <div className="relative h-6 bg-gray-700 rounded">
            <div className="absolute top-0 h-full w-0.5 bg-white" style={{ left: `${Math.min(((gameState.currentTick || 0) / 600) * 100, 100)}%` }} />
            <div className="absolute top-0 h-full bg-blue-500/60" style={{ left: `${Math.min((((rugPrediction.predicted_tick || 0) - (rugPrediction.tolerance || 0)) / 600) * 100, 100)}%`, width: `${Math.min((((rugPrediction.tolerance || 0) * 2) / 600) * 100, 100)}%` }} />
            <div className="absolute top-0 h-full w-0.5 bg-yellow-400" style={{ left: `${Math.min(((rugPrediction.predicted_tick || 0) / 600) * 100, 100)}%` }} />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>0</span><span>Tick {gameState.currentTick}</span><span>{rugPrediction.predicted_tick} ±{rugPrediction.tolerance}</span><span>600+</span>
          </div>
        </div>

        {/* ML Insights */}
        <div className="col-span-4 bg-gray-800 border border-gray-700 rounded p-2">
          <div className="text-xs font-semibold mb-2">ML Insights</div>
          {rugPrediction?.ml_enhancement ? (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <CompactValue label="ML Pred" value={Math.round(rugPrediction.ml_enhancement.ml_prediction)} />
              <CompactValue label="Base Pred" value={rugPrediction.ml_enhancement.base_prediction} />
              <CompactValue label="ML Weight" value={(rugPrediction.ml_enhancement.ml_weight * 100).toFixed(0) + '%'} />
              <CompactValue label="Feat Score" value={Math.round(rugPrediction.ml_enhancement.feature_score)} />
              <CompactValue label="Adjust" value={Math.round(rugPrediction.ml_enhancement.ml_adjustment)} />
              <CompactValue label="Accuracy" value={`${((mlStatus?.online_learner?.overall_accuracy || 0) * 100).toFixed(0)}%`} />
            </div>
          ) : (
            <div className="text-[10px] text-gray-400">Awaiting ML data…</div>
          )}
          {rugPrediction?.ml_enhancement?.key_features && (
            <div className="mt-2 text-[10px] text-gray-400">
              <div className="font-semibold mb-1">Key Features</div>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(rugPrediction.ml_enhancement.key_features).map(([k, v]) => (
                  <div key={k} className="flex justify-between"><span>{k}</span><span className="text-gray-300">{typeof v === 'number' ? v.toFixed(2) : v}</span></div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Patterns Table */}
        <div className="col-span-7 bg-gray-800 border border-gray-700 rounded p-2">
          <div className="text-xs font-semibold mb-2 flex items-center"><TrendingUp className="w-4 h-4 mr-1" /> Patterns</div>
          <table className="w-full text-left border-separate border-spacing-y-1">
            <thead>
              <tr className="text-[10px] text-gray-400">
                <th className="px-2">Pattern</th><th className="px-2">Status</th><th className="px-2">Conf</th><th className="px-2">Metric</th><th className="px-2">Next</th>
              </tr>
            </thead>
            <tbody>
              <PatternRow label="Post-Max" p={patterns?.pattern1} />
              <PatternRow label="Ultra-Short" p={patterns?.pattern2} />
              <PatternRow label="Momentum" p={patterns?.pattern3} />
            </tbody>
          </table>
        </div>

        {/* Weights / System */}
        <div className="col-span-5 bg-gray-800 border border-gray-700 rounded p-2">
          <div className="text-xs font-semibold mb-2">Weights & System</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {mlStatus?.online_learner?.pattern_weights && Object.entries(mlStatus.online_learner.pattern_weights).map(([k, v]) => (
              <div key={k} className="flex justify-between"><span>{k}</span><span className="text-gray-300">{(v).toFixed(2)}</span></div>
            ))}
          </div>
          <div className="mt-2 text-[10px] text-gray-400">Errors: {mlStatus?.system_health?.errors || 0} • Last: {mlStatus?.system_health?.last_error || '—'}</div>
        </div>

        {/* Raw Payload */}
        <div className="col-span-12 bg-gray-800 border border-gray-700 rounded p-2 max-h-48 overflow-auto">
          <div className="text-xs font-semibold mb-2 flex items-center"><Clock className="w-4 h-4 mr-1" /> Live Payload</div>
          <pre className="text-[10px] whitespace-pre-wrap text-gray-300">{lastPayload ? JSON.stringify(lastPayload, null, 2) : 'Waiting for data…'}</pre>
        </div>
      </div>

      {connectionStats.lastError && (
        <div className="mt-2 text-[10px] text-red-400">Error: {connectionStats.lastError}</div>
      )}
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <TreasuryPatternDashboard />
    </div>
  );
}

export default App;