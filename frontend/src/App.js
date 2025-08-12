import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { TrendingUp, Clock, Target, Wifi, WifiOff } from 'lucide-react';

const CompactValue = ({ label, value, accent }) => (
  <div className="flex flex-col leading-tight min-w-0">
    <span className="text-[10px] text-gray-400 truncate">{label}</span>
    <span className={`text-sm font-semibold truncate ${accent || ''}`}>{value}</span>
  </div>
);

const TreasuryPatternDashboard = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const [gameState, setGameState] = useState({ gameId: 0, currentTick: 0, currentPrice: 1.0, isActive: false, isRugged: false, peak_price: 1.0 });
  const [patterns, setPatterns] = useState({});
  const [rugPrediction, setRugPrediction] = useState({ predicted_tick: 200, confidence: 0.5, tolerance: 50, based_on_patterns: [] });
  const [mlStatus, setMlStatus] = useState(null);
  const [predictionHistory, setPredictionHistory] = useState([]);
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
      wsRef.current.onopen = () => { setIsConnected(true); setConnectionStats(prev => ({ ...prev, lastError: null })); };
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.game_state) setGameState(prev => ({ ...prev, ...data.game_state }));
          if (data.patterns) setPatterns(data.patterns);
          if (data.prediction) setRugPrediction(data.prediction);
          if (data.ml_status) setMlStatus(data.ml_status);
          if (data.prediction_history) setPredictionHistory(data.prediction_history);
          setLastPayload(data);
          setLastUpdate(new Date());
          setConnectionStats(prev => ({ ...prev, totalUpdates: prev.totalUpdates + 1 }));
        } catch (err) {
          setConnectionStats(prev => ({ ...prev, lastError: `Parse error: ${err.message}` }));
        }
      };
      wsRef.current.onerror = () => { setConnectionStats(prev => ({ ...prev, lastError: 'Connection error' })); };
      wsRef.current.onclose = () => { setIsConnected(false); reconnectTimeoutRef.current = setTimeout(() => { connectWebSocket(); }, 1500); };
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
    <tr className="text-[11px]">
      <td className="px-2 py-1 text-gray-300 whitespace-nowrap">{label}</td>
      <td className={`px-2 py-1 font-semibold whitespace-nowrap ${getStatusColor(p?.status)}`}>{p?.status || '—'}</td>
      <td className="px-2 py-1 whitespace-nowrap">{((p?.confidence || 0) * 100).toFixed(0)}%</td>
      <td className="px-2 py-1 whitespace-nowrap">{p?.current_peak ? Number(p.current_peak).toFixed(1) + 'x' : p?.ultra_short_prob ? ((p.ultra_short_prob * 100).toFixed(1) + '%') : p?.next_game_prob ? ((p.next_game_prob * 100).toFixed(1) + '%') : '—'}</td>
      <td className="px-2 py-1 whitespace-nowrap">{p?.next_alert || p?.recovery_window || p?.last_trigger || '—'}</td>
    </tr>
  );

  const DiffBadge = ({ diff }) => {
    const color = diff <= 25 ? 'text-green-400' : diff <= 75 ? 'text-yellow-400' : 'text-red-400';
    return <span className={`font-semibold ${color}`}>{diff}</span>;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-2 overflow-x-hidden">
      {/* Top Bar */}
      <div className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded px-3 py-2 min-h-0">
        <div className="flex items-center gap-3 min-w-0">
          {isConnected ? <Wifi className="w-4 h-4 text-green-500" /> : <WifiOff className="w-4 h-4 text-red-500" />}
          <span className={`text-xs ${isConnected ? 'text-green-400' : 'text-red-400'} whitespace-nowrap`}>{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
          <span className="text-xs text-gray-400 whitespace-nowrap">• Uptime {connectionStats.uptime}s</span>
          <span className="text-xs text-gray-400 whitespace-nowrap">• Updates {connectionStats.totalUpdates}</span>
          {lastUpdate && <span className="text-xs text-gray-500 whitespace-nowrap">• Last {lastUpdate.toLocaleTimeString()}</span>}
        </div>
        <div className="flex items-center gap-4 min-w-0">
          <CompactValue label="Game" value={`#${gameState.gameId}`} />
          <CompactValue label="Tick" value={gameState.currentTick} />
          <CompactValue label="Price" value={`${Number(gameState.currentPrice || 0).toFixed(3)}x`} />
        </div>
      </div>

      {/* Grid rows (use min-h-0 and overflow rules to prevent overlapping) */}
      <div className="grid grid-cols-12 gap-2 mt-2 auto-rows-fr">
        {/* Row 1 */}
        <div className="col-span-3 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
          <div className="text-xs font-semibold mb-2 flex items-center"><Target className="w-4 h-4 mr-1" /> Prediction</div>
          <div className="grid grid-cols-2 gap-2">
            <CompactValue label="Predicted Tick" value={rugPrediction.predicted_tick} accent="text-blue-400" />
            <CompactValue label="Tolerance" value={`±${rugPrediction.tolerance}`} accent="text-green-400" />
            <CompactValue label="Confidence" value={`${((rugPrediction.confidence || 0) * 100).toFixed(1)}%`} accent="text-yellow-400" />
            <CompactValue label="Remaining" value={Math.max(0, (rugPrediction.predicted_tick || 0) - (gameState.currentTick || 0))} accent="text-purple-400" />
          </div>
          <div className="mt-2 text-[10px] text-gray-400 truncate">Based on: {rugPrediction?.based_on_patterns?.join(', ')}</div>
        </div>

        <div className="col-span-5 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
          <div className="text-xs font-semibold mb-2">Live Tracking</div>
          <div className="relative h-5 bg-gray-700 rounded overflow-hidden">
            <div className="absolute top-0 h-full w-0.5 bg-white" style={{ left: `${Math.min(((gameState.currentTick || 0) / 600) * 100, 100)}%` }} />
            <div className="absolute top-0 h-full bg-blue-500/60" style={{ left: `${Math.min((((rugPrediction.predicted_tick || 0) - (rugPrediction.tolerance || 0)) / 600) * 100, 100)}%`, width: `${Math.min((((rugPrediction.tolerance || 0) * 2) / 600) * 100, 100)}%` }} />
            <div className="absolute top-0 h-full w-0.5 bg-yellow-400" style={{ left: `${Math.min(((rugPrediction.predicted_tick || 0) / 600) * 100, 100)}%` }} />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400 mt-1">
            <span>0</span><span>Tick {gameState.currentTick}</span><span>{rugPrediction.predicted_tick} ±{rugPrediction.tolerance}</span><span>600+</span>
          </div>
        </div>

        <div className="col-span-4 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
          <div className="text-xs font-semibold mb-2">ML Insights</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {rugPrediction?.ml_enhancement ? (
              <>
                <CompactValue label="ML Pred" value={Math.round(rugPrediction.ml_enhancement.ml_prediction)} />
                <CompactValue label="Base Pred" value={rugPrediction.ml_enhancement.base_prediction} />
                <CompactValue label="ML Weight" value={(rugPrediction.ml_enhancement.ml_weight * 100).toFixed(0) + '%'} />
                <CompactValue label="Adj (P/D/T)" value={`${Math.round(rugPrediction.ml_enhancement.pattern_adjustments || 0)}/${Math.round(rugPrediction.ml_enhancement.duration_adjustment || 0)}/${Math.round(rugPrediction.ml_enhancement.treasury_adjustment || 0)}`} />
                <CompactValue label="Accuracy" value={`${((mlStatus?.learning_engine?.overall_accuracy || 0) * 100).toFixed(0)}%`} />
                <CompactValue label="LR" value={(mlStatus?.learning_engine?.current_learning_rate || 0).toFixed(3)} />
              </>
            ) : (
              <span className="text-[10px] text-gray-400">Awaiting ML data…</span>
            )}
          </div>
        </div>

        {/* Row 2 */}
        <div className="col-span-5 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden flex flex-col">
          <div className="text-xs font-semibold mb-2 flex items-center"><TrendingUp className="w-4 h-4 mr-1" /> Patterns</div>
          <div className="min-h-0 overflow-auto">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-gray-800">
                <tr className="text-[10px] text-gray-400">
                  <th className="px-2 py-1">Pattern</th><th className="px-2 py-1">Status</th><th className="px-2 py-1">Conf</th><th className="px-2 py-1">Metric</th><th className="px-2 py-1">Next</th>
                </tr>
              </thead>
              <tbody>
                <PatternRow label="Post-Max" p={patterns?.pattern1} />
                <PatternRow label="Ultra-Short" p={patterns?.pattern2} />
                <PatternRow label="Momentum" p={patterns?.pattern3} />
              </tbody>
            </table>
          </div>
        </div>

        <div className="col-span-3 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden flex flex-col">
          <div className="text-xs font-semibold mb-2">Weights & System</div>
          <div className="min-h-0 overflow-auto grid grid-cols-2 gap-2 text-xs pr-1">
            {mlStatus?.learning_engine?.feature_weights && Object.entries(mlStatus.learning_engine.feature_weights).map(([k, v]) => (
              <div key={k} className="flex justify-between gap-2"><span className="truncate">{k}</span><span className="text-gray-300 whitespace-nowrap">{Number(v).toFixed(2)}</span></div>
            ))}
          </div>
          <div className="mt-2 text-[10px] text-gray-400 truncate">Errors: {mlStatus?.system_health?.errors || 0} • Last: {mlStatus?.system_health?.last_error || '—'}</div>
        </div>

        <div className="col-span-4 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden flex flex-col">
          <div className="text-xs font-semibold mb-2">Prediction History</div>
          <div className="min-h-0 overflow-auto">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-gray-800">
                <tr className="text-[10px] text-gray-400">
                  <th className="px-2 py-1">Game</th>
                  <th className="px-2 py-1">Pred</th>
                  <th className="px-2 py-1">Actual</th>
                  <th className="px-2 py-1">Diff</th>
                  <th className="px-2 py-1">Peak</th>
                  <th className="px-2 py-1">End</th>
                </tr>
              </thead>
              <tbody className="text-[11px]">
                {predictionHistory && predictionHistory.slice().reverse().slice(0, 14).map((r) => (
                  <tr key={`${r.game_id}-${r.timestamp}`}>
                    <td className="px-2 py-1 text-gray-300 truncate max-w-[80px]" title={r.game_id}>{String(r.game_id).slice(-8)}</td>
                    <td className="px-2 py-1 whitespace-nowrap">{r.predicted_tick}</td>
                    <td className="px-2 py-1 whitespace-nowrap">{r.actual_tick}</td>
                    <td className="px-2 py-1 whitespace-nowrap"><DiffBadge diff={Math.abs((r.predicted_tick || 0) - (r.actual_tick || 0))} /></td>
                    <td className="px-2 py-1 whitespace-nowrap">{Number(r.peak_price || 0).toFixed(2)}x</td>
                    <td className="px-2 py-1 whitespace-nowrap">{Number(r.end_price || 0).toFixed(6)}</td>
                  </tr>
                ))}
                {(!predictionHistory || predictionHistory.length === 0) && (
                  <tr><td colSpan={6} className="px-2 py-1 text-[10px] text-gray-500">No history yet…</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Row 3 */}
        <div className="col-span-12 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
          <div className="text-xs font-semibold mb-2 flex items-center"><Clock className="w-4 h-4 mr-1" /> Live Payload</div>
          <div className="max-h-32 overflow-auto">
            <pre className="text-[10px] whitespace-pre-wrap break-words break-all text-gray-300">{lastPayload ? JSON.stringify(lastPayload, null, 2) : 'Waiting for data…'}</pre>
          </div>
        </div>
      </div>

      {connectionStats.lastError && (
        <div className="mt-2 text-[10px] text-red-400 truncate">Error: {connectionStats.lastError}</div>
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