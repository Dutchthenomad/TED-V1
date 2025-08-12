import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { TrendingUp, Clock, Target, Wifi, WifiOff } from 'lucide-react';
import SideBetPanel from './SideBetPanel';

const CompactValue = ({ label, value, accent }) => (
  <div className="flex flex-col leading-tight min-w-0">
    <span className="text-[10px] text-gray-400 truncate">{label}</span>
    <span className={`text-sm font-semibold truncate ${accent || ''}`}>{value}</span>
  </div>
);

const ModuleBadge = ({ label, active }) => (
  <span
    className={`px-1.5 py-0.5 rounded text-[10px] border ${
      active ? 'bg-green-900/40 border-green-700 text-green-300' : 'bg-gray-800 border-gray-700 text-gray-400'
    }`}
  >
    {label}
  </span>
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
  const [sideBet, setSideBet] = useState(null);
  const [sideBetPerf, setSideBetPerf] = useState(null);
  const [version, setVersion] = useState(null);
  const [avgEndWindow, setAvgEndWindow] = useState(20); // Average End Price window (default 20)
  const [avgDiffWindow, setAvgDiffWindow] = useState(20); // Average Diff window (default 20)

  // Monitoring and REST-enhanced state
  const [wsSystemStatus, setWsSystemStatus] = useState(null);
  const [restStatus, setRestStatus] = useState(null);
  const [restMetrics, setRestMetrics] = useState(null);

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
          if (data.side_bet_recommendation !== undefined) setSideBet(data.side_bet_recommendation);
          if (data.side_bet_performance) setSideBetPerf(data.side_bet_performance);
          if (data.version) setVersion(data.version);
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

  const bandWidth = (rugPrediction?.tolerance || 0) * 2;
  const gateApplied = !!rugPrediction?.ml_enhancement?.ultra_short_gate_applied;
  const gateProb = rugPrediction?.ml_enhancement?.ultra_short_prob;
  const predictionMethod = mlStatus?.prediction_method || '—';
  const modules = mlStatus?.modules || {};

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
          <CompactValue label="Version" value={version || '—'} />
          {/* Top Bar ML method and module badges */}
          <div className="hidden sm:flex items-center gap-2 min-w-0">
            <span className="text-[10px] text-gray-400 whitespace-nowrap">Method:</span>
            <span className="text-[10px] text-blue-300 truncate max-w-[120px]">{predictionMethod}</span>
            <div className="flex items-center gap-1 flex-wrap">
              <ModuleBadge label="hazard" active={!!modules?.hazard} />
              <ModuleBadge label="gate" active={!!modules?.gate} />
              <ModuleBadge label="conformal" active={!!modules?.conformal} />
            </div>
          </div>
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
            <CompactValue label="Band Width" value={`${bandWidth}`} />
            <CompactValue label="Method" value={predictionMethod} />
          </div>
          <div className="mt-2 text-[10px] text-gray-400 truncate">
            Based on: {rugPrediction?.based_on_patterns?.join(', ') || '—'}
          </div>
          <div className="mt-1 text-[10px] text-gray-400 truncate">
            Ultra-Short Gate: {gateApplied ? <span className="text-green-400">ON{typeof gateProb === 'number' ? ` (${(gateProb * 100).toFixed(0)}%)` : ''}</span> : <span className="text-gray-400">OFF</span>}
          </div>
        </div>

        <div className="col-span-5 min-h-0 overflow-hidden flex flex-col gap-2">
          {/* Live Tracking card */}
          <div className="bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
            <div className="text-xs font-semibold mb-2">Live Tracking <span className="text-[10px] text-gray-400 ml-1">(Conformal band)</span></div>
            <div className="relative h-5 bg-gray-700 rounded overflow-hidden">
              <div className="absolute top-0 h-full w-0.5 bg-white" style={{ left: `${Math.min(((gameState.currentTick || 0) / 600) * 100, 100)}%` }} />
              <div className="absolute top-0 h-full bg-blue-500/60" style={{ left: `${Math.min((((rugPrediction.predicted_tick || 0) - (rugPrediction.tolerance || 0)) / 600) * 100, 100)}%`, width: `${Math.min((((rugPrediction.tolerance || 0) * 2) / 600) * 100, 100)}%` }} />
              <div className="absolute top-0 h-full w-0.5 bg-yellow-400" style={{ left: `${Math.min(((rugPrediction.predicted_tick || 0) / 600) * 100, 100)}%` }} />
            </div>
            <div className="flex justify-between text-[10px] text-gray-400 mt-1">
              <span>0</span><span>Tick {gameState.currentTick}</span><span>{rugPrediction.predicted_tick} ±{rugPrediction.tolerance}</span><span>600+</span>
            </div>
          </div>

          {/* Average End Price card */}
          <div className="bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs font-semibold">Average End Price</div>
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-gray-400">Window</span>
                <select
                  className="bg-gray-900 border border-gray-700 text-[10px] rounded px-1 py-0.5 focus:outline-none"
                  value={avgEndWindow}
                  onChange={(e) => setAvgEndWindow(Number(e.target.value))}
                >
                  {[5,10,20,25,50,100].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>
            <div className="text-sm font-semibold text-blue-300">
              {(() => {
                const recs = (predictionHistory || []).slice(-avgEndWindow);
                const usable = recs.filter(r => typeof r.end_price === 'number' && !isNaN(r.end_price));
                const count = usable.length;
                if (count === 0) return '—';
                const sum = usable.reduce((acc, r) => acc + Number(r.end_price), 0);
                return (sum / count).toFixed(6);
              })()}
            </div>
            <div className="text-[10px] text-gray-500 mt-1">Based on available records (up to selected window)</div>
          </div>

          {/* Average Diff card */}
          <div className="bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs font-semibold">Average Diff (Pred vs Actual)</div>
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-gray-400">Window</span>
                <select
                  className="bg-gray-900 border border-gray-700 text-[10px] rounded px-1 py-0.5 focus:outline-none"
                  value={avgDiffWindow}
                  onChange={(e) => setAvgDiffWindow(Number(e.target.value))}
                >
                  {[5,10,20,25,50,100].map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
            </div>
            <div className="text-sm font-semibold text-yellow-300">
              {(() => {
                const recs = (predictionHistory || []).slice(-avgDiffWindow);
                const usable = recs.filter(r => typeof r.diff === 'number' && !isNaN(r.diff));
                const count = usable.length;
                if (count === 0) return '—';
                const sum = usable.reduce((acc, r) => acc + Number(r.diff), 0);
                return Math.round(sum / count);
              })()}
            </div>
            <div className="text-[10px] text-gray-500 mt-1">Average absolute difference in ticks</div>
          </div>
        </div>

        <div className="col-span-4 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
          <div className="text-xs font-semibold mb-2">ML Insights</div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {rugPrediction ? (
              <>
                <CompactValue label="Confidence" value={`${((rugPrediction.confidence || 0) * 100).toFixed(0)}%`} />
                <CompactValue label="Accuracy" value={`${((mlStatus?.performance?.accuracy || 0) * 100).toFixed(0)}%`} />
                <CompactValue label="Patterns" value={(rugPrediction?.based_on_patterns || []).slice(0,2).join(', ') || '—'} />
                <CompactValue label="Drought x" value={rugPrediction?.game_features?.drought_multiplier || patterns?.pattern3?.drought_multiplier || 1.0} />
              </>
            ) : (
              <span className="text-[10px] text-gray-400">Awaiting ML data…</span>
            )}
          </div>
          <div className="mt-2 flex items-center gap-1 flex-wrap">
            <span className="text-[10px] text-gray-400 mr-1">Modules:</span>
            <ModuleBadge label="hazard" active={!!modules?.hazard} />
            <ModuleBadge label="gate" active={!!modules?.gate} />
            <ModuleBadge label="conformal" active={!!modules?.conformal} />
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
          <div className="text-xs font-semibold mb-2">Performance</div>
          <div className="grid grid-cols-2 gap-2 text-xs pr-1">
            <CompactValue label="Accuracy" value={`${((mlStatus?.performance?.accuracy || 0) * 100).toFixed(0)}%`} />
            <CompactValue label="Recent" value={`${((mlStatus?.performance?.recent_accuracy || 0) * 100).toFixed(0)}%`} />
            <CompactValue label="Total Preds" value={mlStatus?.performance?.total_predictions || 0} />
            <CompactValue label="Method" value={predictionMethod} />
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
        <div className="col-span-4 min-h-0 overflow-hidden">
          <SideBetPanel sideBet={sideBet} performance={sideBetPerf} />
        </div>
        <div className="col-span-8 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
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