import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { TrendingUp, Clock, Target, Wifi, WifiOff } from 'lucide-react';
import SideBetPanel from './SideBetPanel';
import { useSystemMonitoring } from './hooks/useSystemMonitoring';

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
const StatLine = ({ label, value, accent }) => (
  <div className="flex items-center justify-between text-[11px]">
    <span className="text-gray-400 mr-2 truncate">{label}</span>
    <span className={`font-semibold ${accent || ''}`}>{value}</span>
  </div>
);


const TreasuryPatternDashboard = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const isConnectingRef = useRef(false);
  const mountedRef = useRef(true);
  const pingIntervalRef = useRef(null);

  const [gameState, setGameState] = useState({ gameId: null, currentTick: 0, currentPrice: 0, rugged: false, peak_price: 1.0 });
  const [patterns, setPatterns] = useState({});
  const [rugPrediction, setRugPrediction] = useState({ predicted_tick: 200, confidence: 0.5, tolerance: 50, based_on_patterns: [], ml_enhancement: {} });
  const [mlStatus, setMlStatus] = useState(null);
  const [predictionHistory, setPredictionHistory] = useState([]);
  const [connectionStats, setConnectionStats] = useState({ totalUpdates: 0, lastError: null, uptime: 0 });
  const [lastPayload, setLastPayload] = useState(null);
  const [sideBet, setSideBet] = useState(null);
  const [sideBetPerf, setSideBetPerf] = useState(null);
  const [version, setVersion] = useState(null);
  const [avgEndWindow, setAvgEndWindow] = useState(20); // Average End Price window (default 20)
  // Sticky side bet per game
  const [stickySideBet, setStickySideBet] = useState(null);
  const [stickyGameId, setStickyGameId] = useState(null);

  const [avgDiffWindow, setAvgDiffWindow] = useState(20); // Average Diff window (default 20)
  const [historyShowN, setHistoryShowN] = useState(20); // how many rows to display in the table - default to first option
  const [directionalMetrics, setDirectionalMetrics] = useState(null); // New directional metrics

  // Monitoring and REST-enhanced state
  const [wsSystemStatus, setWsSystemStatus] = useState(null);
  const monitoring = useSystemMonitoring({ wsSystemStatus, connectionStats });
  const restStatus = monitoring.rest;
  const restMetrics = monitoring.metrics;

  const getBackendBaseHttp = () => {
    return process.env.REACT_APP_BACKEND_URL || '';
  };
  const getBackendBaseWs = () => {
    // Use REACT_APP_WS_URL if available, otherwise derive from BACKEND_URL
    if (process.env.REACT_APP_WS_URL) {
      return process.env.REACT_APP_WS_URL.replace(/\/+$/, '');
    }
    const base = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
    return base.replace(/^http/i, 'ws');
  };

  // --- REST helpers ---
  const backend = process.env.REACT_APP_BACKEND_URL || '';
  const fetchPredictionHistory = async () => {
    if (!backend) return;
    try {
      const res = await fetch(`${backend}/api/prediction-history`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data?.history)) {
          setPredictionHistory(data.history); // expected up to 200 from backend
        }
        // Extract directional metrics from the response
        if (data?.metrics) {
          setDirectionalMetrics(data.metrics);
        }
      }
    } catch (_) {}
  };

  const fetchMetrics = async () => {
    if (!backend) return;
    try {
      const res = await fetch(`${backend}/api/metrics`);
      if (res.ok) {
        const data = await res.json();
        if (data?.directional_metrics?.last_50) {
          setDirectionalMetrics(data.directional_metrics.last_50);
        }
      }
    } catch (_) {}
  };

  const fetchSideBet = async () => {
    if (!backend) return;
    try {
      const res = await fetch(`${backend}/api/side-bet`);
      if (res.ok) {
        const data = await res.json();
        const rec = data?.recommendation;
        if (rec) {
          setSideBet(rec);
          // Sticky capture: store the first PLACE_SIDE_BET per game
          if (!stickySideBet && rec.action === 'PLACE_SIDE_BET' && gameState?.currentTick != null) {
            setStickySideBet({
              data: rec,
              tick: gameState.currentTick,
              timestamp: new Date().toISOString(),
            });
          }
        }
        if (data?.performance) setSideBetPerf(data.performance);
      }
    } catch (_) {}
  };

  const connectWebSocket = () => {
    // Don't create a new connection if one already exists and is connecting/open
    if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
      return;
    }
    
    // Prevent concurrent connection attempts
    if (isConnectingRef.current) {
      return;
    }
    
    // Don't connect if component is unmounted
    if (!mountedRef.current) {
      return;
    }
    
    isConnectingRef.current = true;
    
    try {
      const wsUrl = `${getBackendBaseWs()}/api/ws`;
      console.log('Connecting to WebSocket:', wsUrl);
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        isConnectingRef.current = false;
        if (mountedRef.current) {
          setIsConnected(true);
          setConnectionStats(prev => ({ ...prev, lastError: null }));
          
          // Start ping interval to keep connection alive
          if (pingIntervalRef.current) {
            clearInterval(pingIntervalRef.current);
          }
          pingIntervalRef.current = setInterval(() => {
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send('ping');
              console.log('Sent ping');
            }
          }, 25000); // Send ping every 25 seconds
        }
      };
      
      wsRef.current.onmessage = (event) => {
        if (!mountedRef.current) return;
        
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message received:', data.type || 'data', 'tick:', data.game_state?.currentTick);
          
          // Force state updates with new object references to ensure re-render
          if (data.game_state) {
            setGameState(prevState => {
              const newState = { ...data.game_state };
              console.log('Game state update - Tick:', newState.currentTick, 'Price:', newState.currentPrice);
              return newState;
            });
          }
          if (data.patterns) setPatterns(() => ({ ...data.patterns }));
          if (data.prediction) setRugPrediction(() => ({ ...data.prediction }));
          if (data.ml_status) setMlStatus(() => ({ ...data.ml_status }));
          // Sticky side bet logic: capture first non-null per game
          if (data.game_state?.gameId !== undefined) {
            const gid = data.game_state.gameId;
            if (stickyGameId !== gid) {
              setStickyGameId(gid);
              setStickySideBet(null);
            }
          }
          if (data.side_bet_recommendation) {
            if (!stickySideBet && data.game_state) {
              setStickySideBet({
                data: data.side_bet_recommendation,
                tick: data.game_state.currentTick,
                timestamp: new Date().toISOString(),
              });
            }
          }

          if (data.prediction_history) setPredictionHistory(data.prediction_history);
          if (data.side_bet_recommendation !== undefined) setSideBet(data.side_bet_recommendation);
          if (data.side_bet_performance) setSideBetPerf(data.side_bet_performance);
          if (data.version) setVersion(data.version);
          if (data.system_status) setWsSystemStatus(data.system_status);
          // Force new Date object and state updates
          setLastPayload(() => data);
          setLastUpdate(() => new Date());
          setConnectionStats(prev => {
            const newStats = { ...prev, totalUpdates: prev.totalUpdates + 1 };
            console.log('Total WebSocket updates received:', newStats.totalUpdates);
            return newStats;
          });
        } catch (err) {
          setConnectionStats(prev => ({ ...prev, lastError: `Parse error: ${err.message}` }));
        }
      };
      wsRef.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        isConnectingRef.current = false;
        if (mountedRef.current) {
          setConnectionStats(prev => ({ ...prev, lastError: 'Connection error' }));
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        isConnectingRef.current = false;
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        if (mountedRef.current) {
          setIsConnected(false);
          
          // Only attempt reconnect if not a normal closure and component is still mounted
          if (event.code !== 1000 && event.code !== 1001) {
            if (reconnectTimeoutRef.current) {
              clearTimeout(reconnectTimeoutRef.current);
            }
            reconnectTimeoutRef.current = setTimeout(() => {
              if (mountedRef.current) {
                connectWebSocket();
              }
            }, 2000);
          }
        }
      };
    } catch (err) {
      console.error('Failed to create WebSocket:', err);
      isConnectingRef.current = false;
      if (mountedRef.current) {
        setConnectionStats(prev => ({ ...prev, lastError: `Connection failed: ${err.message}` }));
      }
    }
  };

  useEffect(() => {
    mountedRef.current = true;
    
    // Delay initial connection to avoid React StrictMode double-mount issues
    const connectionTimer = setTimeout(() => {
      if (mountedRef.current) {
        connectWebSocket();
      }
    }, 100);
    
    return () => {
      mountedRef.current = false;
      clearTimeout(connectionTimer);
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      
      if (wsRef.current) {
        if (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING) {
          wsRef.current.close(1000, 'Component unmounting');
        }
        wsRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => { if (isConnected) setConnectionStats(prev => ({ ...prev, uptime: prev.uptime + 1 })); }, 1000);
    return () => clearInterval(interval);
  }, [isConnected]);

  // Kick off REST polling for history and side-bet
  useEffect(() => {
    let histTimer = null, sidebetTimer = null, metricsTimer = null;
    fetchPredictionHistory();
    fetchSideBet();
    fetchMetrics();
    histTimer = setInterval(fetchPredictionHistory, 45000); // 45s cadence
    sidebetTimer = setInterval(fetchSideBet, 2000);         // 2s cadence to not miss windows
    metricsTimer = setInterval(fetchMetrics, 30000);         // 30s cadence for metrics
    const onFocus = () => { fetchPredictionHistory(); fetchSideBet(); fetchMetrics(); };
    window.addEventListener('focus', onFocus);
    return () => {
      if (histTimer) clearInterval(histTimer);
      if (sidebetTimer) clearInterval(sidebetTimer);
      if (metricsTimer) clearInterval(metricsTimer);
      window.removeEventListener('focus', onFocus);
    };
  }, [backend, stickySideBet, gameState?.currentTick]);

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

          {/* Directional Metrics card */}
          <div className="bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
            <div className="text-xs font-semibold mb-2">Directional Metrics (50 games)</div>
            {directionalMetrics ? (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-400">Median E40:</span>
                  <span className={`font-semibold ${
                    Math.abs(directionalMetrics.median_E40 || 0) <= 0.25 ? 'text-green-400' : 
                    Math.abs(directionalMetrics.median_E40 || 0) <= 0.5 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {directionalMetrics.median_E40 > 0 ? '+' : ''}{directionalMetrics.median_E40?.toFixed(2)}w
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-400">Within 2w:</span>
                  <span className={`font-semibold ${
                    (directionalMetrics.within_2_windows || 0) >= 0.5 ? 'text-green-400' : 'text-yellow-400'
                  }`}>
                    {((directionalMetrics.within_2_windows || 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-400">Coverage:</span>
                  <span className={`font-semibold ${
                    Math.abs((directionalMetrics.coverage_rate || 0) - 0.85) <= 0.02 ? 'text-green-400' : 'text-yellow-400'
                  }`}>
                    {((directionalMetrics.coverage_rate || 0) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-400">Early Skew:</span>
                  <span className={`font-semibold ${
                    Math.abs(directionalMetrics.early_skew || 0) <= 0.1 ? 'text-green-400' : 'text-orange-400'
                  }`}>
                    {directionalMetrics.early_skew > 0 ? '+' : ''}{(directionalMetrics.early_skew || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            ) : (
              <div className="text-[10px] text-gray-400">Loading metrics...</div>
            )}
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
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="text-xs font-semibold">Prediction History</div>
              {predictionHistory && predictionHistory.length > 0 && (
                <div className="text-[10px] text-gray-400">
                  (showing {Math.min(historyShowN, predictionHistory.length)} of {predictionHistory.length})
                </div>
              )}
            </div>
            <div className="flex items-center gap-1">
              <span className="text-[10px] text-gray-400">Show</span>
              <select
                className="bg-gray-900 border border-gray-700 text-[10px] rounded px-1 py-0.5 focus:outline-none"
                value={historyShowN}
                onChange={(e) => setHistoryShowN(Number(e.target.value))}
              >
                {[20,50,100,200].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          </div>
          <div className="prediction-history-container min-h-0 overflow-auto prediction-history-scroll smooth-scroll">
            <table className="w-full text-left">
              <thead className="sticky top-0 bg-gray-800 z-10 border-b border-gray-700">
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
                {predictionHistory && predictionHistory.slice().reverse().slice(0, historyShowN).map((r, idx) => (
                  <tr 
                    key={`${r.game_id}-${r.timestamp}`}
                    className={`hover:bg-gray-700/30 transition-colors ${idx % 2 === 0 ? 'bg-gray-900/20' : ''}`}
                  >
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
          {/* SideBetPanel: sticky per game with captured tick label */}
          <SideBetPanel sideBet={stickySideBet?.data} performance={sideBetPerf} capturedTick={stickySideBet?.tick} capturedAt={stickySideBet?.timestamp} />
        </div>
        <div className="col-span-8 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
        {/* Side Bet Monitor */}
        <div className="col-span-4 bg-gray-800 border border-gray-700 rounded p-2 min-h-0 overflow-hidden">
          <div className="text-xs font-semibold mb-2">Side Bet Monitor</div>
          <div className="grid grid-cols-2 gap-2 pr-1 text-[11px]">
            <div className="flex items-center justify-between"><span className="text-gray-400">Eligible after 40-tick coverage + 4-tick cooldown</span><span className="font-semibold">{(gameState?.currentTick || 0) <= 5 ? 'Yes' : 'No'}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-400">Last Rec (this game)</span><span className="font-semibold">{stickySideBet ? (stickySideBet.tick + 't') : '—'}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-400">Total Recs</span><span className="font-semibold">{sideBetPerf?.total_recommendations || 0}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-400">Win/Loss</span><span className="font-semibold">{(sideBetPerf?.bets_won || 0)}/{(sideBetPerf?.bets_lost || 0)}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-400">Positive EV</span><span className="font-semibold">{sideBetPerf?.positive_ev_bets || 0}</span></div>
            <div className="flex items-center justify-between"><span className="text-gray-400">Total EV</span><span className="font-semibold">{typeof sideBetPerf?.total_ev === 'number' ? Number(sideBetPerf.total_ev).toFixed(3) : '0.000'}</span></div>
          </div>
        </div>

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