import React from 'react';

const SideBetPanel = ({ sideBet, performance }) => {
  if (!sideBet) return null;

  const isPositiveEV = sideBet.expected_value > 0;
  const shouldBet = sideBet.action === 'PLACE_SIDE_BET';

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700 h-full">
      <h3 className="text-sm font-semibold text-gray-300 mb-2">Side Bet Arbitrage</h3>

      {/* Main Recommendation */}
      <div className={`text-lg font-bold mb-2 ${shouldBet ? 'text-green-400' : 'text-yellow-400'}`}>
        {shouldBet ? '🎯 PLACE BET' : '⏳ WAIT'}
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-gray-500">Win Prob:</span>
          <span className="ml-1 text-white">{(sideBet.ultra_short_probability * 100).toFixed(1)}%</span>
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
        </div>
      )}

      {/* Reasoning */}
      <div className="mt-2 text-xs text-gray-400 italic">{sideBet.reasoning}</div>
    </div>
  );
};

export default SideBetPanel;