import React from 'react';
import { MapPin, Navigation, Star, Zap } from 'lucide-react';
import type { LockerRecommendation } from '../types/locker';

interface LockerCardProps {
  locker: LockerRecommendation;
  rank: number;
  isSelected: boolean;
  onSelect: (locker: LockerRecommendation) => void;
}

const LockerCard: React.FC<LockerCardProps> = ({ locker, rank, isSelected, onSelect }) => {
  const getRankBadge = () => {
    switch (rank) {
      case 1:
        return <span className="bg-yellow-400 text-yellow-900 px-2 py-1 rounded-full text-xs font-bold">🥇 Best Match</span>;
      case 2:
        return <span className="bg-gray-300 text-gray-800 px-2 py-1 rounded-full text-xs font-bold">🥈 2nd Best</span>;
      case 3:
        return <span className="bg-orange-300 text-orange-800 px-2 py-1 rounded-full text-xs font-bold">🥉 3rd Best</span>;
      default:
        return null;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-green-600 bg-green-100';
    if (score >= 50) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  return (
    <div
      onClick={() => onSelect(locker)}
      className={`
        p-4 rounded-xl border-2 transition-all duration-300 cursor-pointer
        ${isSelected 
          ? 'border-blue-500 bg-blue-50 shadow-lg transform scale-[1.02]' 
          : 'border-gray-200 bg-white hover:border-blue-300 hover:shadow-md'
        }
      `}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1 pr-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-blue-600 text-white px-2 py-0.5 rounded text-xs font-mono font-bold">
              ID: {locker.id}
            </span>
          </div>
          <h3 className="font-bold text-gray-800 text-lg">{locker.name}</h3>
          {locker.address && (
            <p className="text-xs text-gray-500 mt-0.5">{locker.address}</p>
          )}
          <div className="flex items-center text-gray-500 text-sm mt-1">
            <MapPin className="w-4 h-4 mr-1 text-blue-500" />
            <span>{locker.distance} away</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-2">
          {getRankBadge()}
          <div className={`px-3 py-1 rounded-full font-bold ${getScoreColor(locker.score)}`}>
            <Zap className="w-4 h-4 inline mr-1" />
            {locker.score.toFixed(1)}
          </div>
        </div>
      </div>

      {/* AI Score Breakdown */}
      <div className="bg-gray-50 rounded-lg p-3 mb-3">
        <div className="text-xs text-gray-500 mb-2 font-semibold">AI ANALYSIS</div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-lg font-bold text-blue-600">{locker.availability.small}</div>
            <div className="text-xs text-gray-500">Small</div>
          </div>
          <div>
            <div className="text-lg font-bold text-green-600">{locker.availability.medium}</div>
            <div className="text-xs text-gray-500">Medium</div>
          </div>
          <div>
            <div className="text-lg font-bold text-purple-600">{locker.availability.large}</div>
            <div className="text-xs text-gray-500">Large</div>
          </div>
        </div>
      </div>

      {/* Route Info */}
      <div className="flex justify-between items-center text-sm">
        <div className="flex items-center text-gray-600">
          <Navigation className="w-4 h-4 mr-1 text-blue-500" />
          <span>Route deviation: {locker.route_deviation}</span>
        </div>
        <div className="flex items-center text-green-600">
          <Star className="w-4 h-4 mr-1" />
          <span>{locker.predicted_availability}% available</span>
        </div>
      </div>

      {/* Select Button */}
      {isSelected && (
        <button className="w-full mt-4 bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 transition-colors">
          ✓ Selected - Confirm This Locker
        </button>
      )}
    </div>
  );
};

export default LockerCard;