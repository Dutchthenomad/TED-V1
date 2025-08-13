import React from 'react';

const SideBetPanel = ({ sideBet, performance, capturedTick, capturedAt, status }) => {
  if (!sideBet) return null;

  const p = Number(sideBet?.p_win_40 ?? sideBet?.ultra_short_probability ?? 0);
  const isPositiveEV = Number(sideBet?.expected_value ?? -1) > 0;
  const shouldBet = sideBet?.action === 'PLACE_SIDE_BET';
  const eprActive = !!(sideBet?.epr_active ?? status?.ml?.epr?.active);
  const usedThreshold = Number(sideBet?.threshold_used ?? status?.ml?.sidebet_threshold ?? 0.20);

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 h-full">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-300">Side Bet Arbitrage</h3>
        {typeof capturedTick === 'number' && (
          <span className="text-[10px] text-gray-400">Captured at tick {capturedTick}</span>
        )}
      </div>

      {/* Main Recommendation */}
      <div className={`text-lg font-bold mb-2 ${shouldBet ? 'text-green-400' : 'text-yellow-400'}`}>
        {shouldBet ? '🎯 PLACE BET' : '⏳ WAIT'}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-500">Win Prob (40t):</span>
          <span className="ml-1 text-white">{(p * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-gray-500">EV:</span>
          <span className={`ml-1 ${isPositiveEV ? 'text-green-400' : 'text-red-400'}`}>
            {sideBet.expected_value > 0 ? '+' : ''}{sideBet.expected_value.toFixed(3)}
          </span>
        </div>
        <div>
          <span className="text-gray-500">Confidence:</span>
          <span className="ml-1 text-white">{(sideBet.confidence * 100).toFixed(0)}%</span>
        </div>
        <div>
          <span className="text-gray-500">Payout:</span>
          <span className="ml-1 text-blue-400">5:1</span>
        </div>
      </div>

      {/* Performance Stats (if available) */}
      {performance && (
        <div className="mt-2 pt-2 border-t border-gray-700 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-500">Win Rate:</span>
            <span className="text-white">
              {performance.bets_won}/{(performance.bets_won || 0) + (performance.bets_lost || 0)} ({(((performance.bets_won || 0) / Math.max(1, (performance.bets_won || 0) + (performance.bets_lost || 0))) * 100).toFixed(0)}%)
            </span>
          </div>
          {!!sideBet?.coverage_end_tick && typeof capturedTick === 'number' && (
            <div className="flex justify-between mt-1">
              <span className="text-gray-500">Coverage:</span>
              <span className="text-white">[{capturedTick} → {sideBet.coverage_end_tick}] (40 ticks)</span>
            </div>
          )}
          {!!sideBet?.next_eligible_tick && (
            <div className="flex justify-between mt-1">
              <span className="text-gray-500">Next eligible:</span>
              <span className="text-white">{sideBet.next_eligible_tick}</span>
            </div>
          )}
        </div>
      )}

      {/* EPR Status Badge */}
      {eprActive && (
        <div className="mt-2 p-2 bg-amber-900/20 border border-amber-700/50 rounded text-[11px] text-amber-400">
          <div className="flex items-center justify-between">
            <span className="font-semibold">Early Peak Regime: ON</span>
            <span className="text-amber-300">Threshold: {usedThreshold.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Reasoning */}
      {!!sideBet?.reasoning && <div className="mt-2 text-xs text-gray-400 italic">{sideBet.reasoning}</div>}
    </div>
  );
};

export default SideBetPanel;