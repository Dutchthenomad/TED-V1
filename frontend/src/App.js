import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import { AlertCircle, TrendingUp, Clock, Target, Wifi, WifiOff } from 'lucide-react';

const TreasuryPatternDashboard = () => {
  // WebSocket connection
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Game state
  const [gameState, setGameState] = useState({
    gameId: 0,
    currentTick: 0,
    currentPrice: 1.0,
    isActive: false,
    isRugged: false
  });

  // Pattern states
  const [patterns, setPatterns] = useState({
    pattern1: {
      name: 'Post-Max-Payout Recovery',
      status: 'NORMAL',
      confidence: 0.85,
      last_trigger: null,
      next_game_prob: 0.211
    },
    pattern2: {
      name: 'Ultra-Short High-Payout',
      status: 'NORMAL',
      confidence: 0.78,
      ultra_short_prob: 0.081,
      current_game_prob: 0.15
    },
    pattern3: {
      name: 'Momentum Thresholds',
      status: 'NORMAL',
      confidence: 0.91,
      current_peak: 1.0,
      next_alert: 8
    }
  });

  // Rug prediction
  const [rugPrediction, setRugPrediction] = useState({
    predicted_tick: 200,
    confidence: 0.5,
    tolerance: 50,
    based_on_patterns: []
  });

  // Connection status
  const [connectionStats, setConnectionStats] = useState({
    totalUpdates: 0,
    lastError: null,
    uptime: 0
  });

  const getBackendBase = () => {
    const base = process.env.REACT_APP_BACKEND_URL || '';
    return base.replace(/^http/i, 'ws');
  };

  // WebSocket connection logic
  const connectWebSocket = () => {
    try {
      wsRef.current = new WebSocket(`${getBackendBase()}/api/ws`);
      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionStats(prev => ({ ...prev, lastError: null }));
      };
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.game_state) setGameState(data.game_state);
          if (data.patterns) setPatterns(data.patterns);
          if (data.prediction) setRugPrediction(data.prediction);
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
        reconnectTimeoutRef.current = setTimeout(() => { connectWebSocket(); }, 3000);
      };
    } catch (err) {
      setConnectionStats(prev => ({ ...prev, lastError: `Connection failed: ${err.message}` }));
    }
  };

  useEffect(() => {
    connectWebSocket();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      if (isConnected) {
        setConnectionStats(prev => ({ ...prev, uptime: prev.uptime + 1 }));
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [isConnected]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'TRIGGERED': return 'bg-red-500';
      case 'MONITORING': return 'bg-yellow-500';
      case 'APPROACHING': return 'bg-orange-500';
      case 'NORMAL': return 'bg-green-500';
      case 'EXCEEDED': return 'bg-purple-500';
      default: return 'bg-gray-500';
    }
  };

  const getPatternIcon = (patternKey) => {
    switch (patternKey) {
      case 'pattern1': return <TrendingUp className="w-5 h-5" />;
      case 'pattern2': return <Clock className="w-5 h-5" />;
      case 'pattern3': return <Target className="w-5 h-5" />;
      default: return <AlertCircle className="w-5 h-5" />;
    }
  };

  const formatUptime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}h ${minutes}m ${secs}s`;
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-4">Treasury Pattern Tracker MVP</h1>
        <div className="bg-gray-800 rounded-lg p-4 mb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                {isConnected ? <Wifi className="w-5 h-5 text-green-500" /> : <WifiOff className="w-5 h-5 text-red-500" />}
                <span className={`font-medium ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
                  {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
                </span>
              </div>
              {isConnected && (
                <>
                  <span className="text-sm text-gray-400">•</span>
                  <span className="text-sm text-gray-400">Uptime: {formatUptime(connectionStats.uptime)}</span>
                  <span className="text-sm text-gray-400">•</span>
                  <span className="text-sm text-gray-400">Updates: {connectionStats.totalUpdates}</span>
                </>
              )}
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-400">Game #{gameState.gameId} • Tick: {gameState.currentTick}</div>
              {lastUpdate && <div className="text-xs text-gray-500">Last update: {lastUpdate.toLocaleTimeString()}</div>}
            </div>
          </div>
          {connectionStats.lastError && (
            <div className="mt-2 text-sm text-red-400">Error: {connectionStats.lastError}</div>
          )}
        </div>
        <div className="flex items-center space-x-6 text-sm">
          <div className={`px-3 py-1 rounded-full ${gameState.isActive ? 'bg-green-600' : 'bg-gray-600'}`}>
            {gameState.isActive ? 'ACTIVE' : 'WAITING'}
          </div>
          <span>Price: {Number(gameState.currentPrice || 0).toFixed(3)}x</span>
          {gameState.isRugged && <span className="text-red-400 font-bold">RUGGED!</span>}
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-6 mb-8 border-l-4 border-blue-500">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Target className="w-6 h-6 mr-2" />
          Live Rug Prediction
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-blue-400">{rugPrediction.predicted_tick}</div>
            <div className="text-sm text-gray-400">Predicted Tick</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-400">±{rugPrediction.tolerance}</div>
            <div className="text-sm text-gray-400">Tolerance</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-400">{((rugPrediction.confidence || 0) * 100).toFixed(1)}%</div>
            <div className="text-sm text-gray-400">Confidence</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">{Math.max(0, (rugPrediction.predicted_tick || 0) - (gameState.currentTick || 0))}</div>
            <div className="text-sm text-gray-400">Ticks Remaining</div>
          </div>
        </div>
        {rugPrediction.based_on_patterns && rugPrediction.based_on_patterns.length > 0 && (
          <div className="mt-4 text-sm text-gray-400">Active patterns: {rugPrediction.based_on_patterns.join(', ')}</div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center">{getPatternIcon('pattern1')}<span className="ml-2">Pattern 1</span></h3>
            <div className={`w-3 h-3 rounded-full ${getStatusColor(patterns?.pattern1?.status)}`}></div>
          </div>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-400">Post-Max-Payout Recovery</div>
              <div className="text-xl font-bold">{patterns?.pattern1?.last_trigger !== null && patterns?.pattern1?.last_trigger !== undefined ? `${patterns.pattern1.last_trigger} games ago` : 'No recent trigger'}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Next Game Max Payout Prob</div>
              <div className="text-xl font-bold text-yellow-400">{((patterns?.pattern1?.next_game_prob || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Status</div>
              <div className={`text-lg font-bold ${patterns?.pattern1?.status === 'TRIGGERED' ? 'text-red-400' : patterns?.pattern1?.status === 'MONITORING' ? 'text-yellow-400' : 'text-green-400'}`}>{patterns?.pattern1?.status}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Confidence</div>
              <div className="text-lg font-bold">{((patterns?.pattern1?.confidence || 0) * 100).toFixed(0)}%</div>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center">{getPatternIcon('pattern2')}<span className="ml-2">Pattern 2</span></h3>
            <div className={`w-3 h-3 rounded-full ${getStatusColor(patterns?.pattern2?.status)}`}></div>
          </div>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-400">Ultra-Short High-Payout</div>
              <div className="text-xl font-bold">≤10 tick detection</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Base Ultra-Short Prob</div>
              <div className="text-xl font-bold text-orange-400">{((patterns?.pattern2?.ultra_short_prob || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Current Game Prob</div>
              <div className="text-lg font-bold text-blue-400">{((patterns?.pattern2?.current_game_prob || patterns?.pattern2?.current_game_probability || 0) * 100).toFixed(1)}%</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Status</div>
              <div className={`text-lg font-bold ${patterns?.pattern2?.status === 'TRIGGERED' ? 'text-red-400' : 'text-green-400'}`}>{patterns?.pattern2?.status}</div>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center">{getPatternIcon('pattern3')}<span className="ml-2">Pattern 3</span></h3>
            <div className={`w-3 h-3 rounded-full ${getStatusColor(patterns?.pattern3?.status)}`}></div>
          </div>
          <div className="space-y-3">
            <div>
              <div className="text-sm text-gray-400">Momentum Thresholds</div>
              <div className="text-xl font-bold">{Number(patterns?.pattern3?.current_peak || 1).toFixed(1)}x current</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Next Alert: {patterns?.pattern3?.next_alert}x</div>
              <div className="text-xl font-bold text-red-400">
                {patterns?.pattern3?.next_alert === 8 ? '24.4%' : patterns?.pattern3?.next_alert === 12 ? '23.0%' : patterns?.pattern3?.next_alert === 20 ? '50.0%' : 'N/A'}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Status</div>
              <div className={`text-lg font-bold ${patterns?.pattern3?.status === 'APPROACHING' ? 'text-orange-400' : patterns?.pattern3?.status?.startsWith('DROUGHT_') ? 'text-purple-400' : 'text-green-400'}`}>{patterns?.pattern3?.status}</div>
            </div>
            <div className="text-sm space-y-1">
              <div className="flex justify-between"><span>8x → 50x:</span><span className="text-yellow-400">24.4%</span></div>
              <div className="flex justify-between"><span>12x → 100x:</span><span className="text-orange-400">23.0%</span></div>
              <div className="flex justify-between"><span>20x → 50x:</span><span className="text-red-400">50.0%</span></div>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-8 bg-gray-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Live Prediction Tracking</h3>
        <div className="relative">
          <div className="h-8 bg-gray-700 rounded-full overflow-hidden relative">
            <div className="absolute top-0 h-full w-1 bg-white z-30 shadow-lg" style={{ left: `${Math.min(((gameState.currentTick || 0) / 600) * 100, 100)}%` }}>
              <div className="absolute -top-6 -left-8 text-xs text-white font-bold">NOW</div>
            </div>
            <div className="absolute top-0 h-full bg-blue-500 opacity-60 z-10" style={{ left: `${Math.min((((rugPrediction.predicted_tick || 0) - (rugPrediction.tolerance || 0)) / 600) * 100, 100)}%`, width: `${Math.min((((rugPrediction.tolerance || 0) * 2) / 600) * 100, 100)}%` }}></div>
            <div className="absolute top-0 h-full w-1 bg-yellow-400 z-20 shadow-lg" style={{ left: `${Math.min(((rugPrediction.predicted_tick || 0) / 600) * 100, 100)}%` }}>
              <div className="absolute -top-6 -left-12 text-xs text-yellow-400 font-bold">PREDICT</div>
            </div>
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-3">
            <span>0 ticks</span>
            <span>Current: {gameState.currentTick}</span>
            <span>Predicted: {rugPrediction.predicted_tick} ±{rugPrediction.tolerance}</span>
            <span>600+ ticks</span>
          </div>
        </div>
      </div>

      {!isConnected && (
        <div className="mt-8 bg-red-900 bg-opacity-50 border border-red-600 rounded-lg p-4">
          <h4 className="text-red-400 font-semibold mb-2">Connection Issues</h4>
          <p className="text-sm text-red-300">Unable to connect to backend. Make sure the backend is running and REACT_APP_BACKEND_URL is correctly set.</p>
        </div>
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