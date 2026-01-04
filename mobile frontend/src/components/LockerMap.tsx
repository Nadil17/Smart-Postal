import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { LockerRecommendation } from '../types/locker';
import { Loader2 } from 'lucide-react';
import 'leaflet/dist/leaflet.css';

// Fix for default marker icons in React-Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom marker icons
const createCustomIcon = (color: string, label: string) => {
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        background: ${color};
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      ">${label}</div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
};

const customerIcon = L.divIcon({
  className: 'customer-marker',
  html: `
    <div style="
      background: #EF4444;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 3px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
      animation: pulse 2s infinite;
    ">
      <div style="width: 8px; height: 8px; background: white; border-radius: 50%;"></div>
    </div>
    <style>
      @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
      }
    </style>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
});

const courierIcon = L.divIcon({
  className: 'courier-marker',
  html: `
    <div style="
      background: #F97316;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 3px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
      font-size: 14px;
    ">🚚</div>
  `,
  iconSize: [28, 28],
  iconAnchor: [14, 14],
});

// Component to fit bounds when lockers change
const FitBounds: React.FC<{ lockers: LockerRecommendation[]; customerLocation: { lat: number; lng: number } }> = ({ lockers, customerLocation }) => {
  const map = useMap();
  
  useEffect(() => {
    if (lockers.length > 0) {
      const bounds = L.latLngBounds([
        [customerLocation.lat, customerLocation.lng],
        ...lockers.map(l => [l.latitude, l.longitude] as [number, number])
      ]);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [lockers, customerLocation, map]);
  
  return null;
};

interface LockerMapProps {
  lockers: LockerRecommendation[];
  customerLocation?: { lat: number; lng: number };
  courierLocation?: { lat: number; lng: number };
  courierRoute?: [number, number][];
  selectedLocker: LockerRecommendation | null;
  onLockerSelect: (locker: LockerRecommendation) => void;
}

const LockerMap: React.FC<LockerMapProps> = ({
  lockers,
  customerLocation = { lat: 6.9100, lng: 79.8600 },
  courierLocation = { lat: 6.9344, lng: 79.8428 },
  courierRoute,
  selectedLocker,
  onLockerSelect
}) => {
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    setMapLoaded(true);
  }, []);

  const getMarkerColor = (rank: number, isSelected: boolean) => {
    if (isSelected) return '#2563EB'; // blue-600
    switch (rank) {
      case 0: return '#F59E0B'; // yellow-500 (Best)
      case 1: return '#9CA3AF'; // gray-400 (2nd)
      case 2: return '#F97316'; // orange-500 (3rd)
      default: return '#6B7280';
    }
  };

  if (!mapLoaded) {
    return (
      <div className="relative w-full h-80 bg-gray-100 rounded-xl overflow-hidden flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600">Loading Colombo Map...</span>
      </div>
    );
  }

  return (
    <div className="relative w-full h-80 rounded-xl overflow-hidden shadow-lg">
      <MapContainer
        center={[customerLocation.lat, customerLocation.lng]}
        zoom={13}
        className="w-full h-full z-0"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <FitBounds lockers={lockers} customerLocation={customerLocation} />
        
        {/* Customer Location Marker */}
        <Marker position={[customerLocation.lat, customerLocation.lng]} icon={customerIcon}>
          <Popup>
            <div className="text-center">
              <strong className="text-red-600">📍 Your Location</strong>
              <p className="text-xs text-gray-500">Delivery destination</p>
            </div>
          </Popup>
        </Marker>
        
        {/* Courier Location Marker */}
        <Marker position={[courierLocation.lat, courierLocation.lng]} icon={courierIcon}>
          <Popup>
            <div className="text-center">
              <strong className="text-orange-600">🚚 Courier Location</strong>
              <p className="text-xs text-gray-500">Fort Railway Station</p>
              <p className="text-xs text-blue-500 mt-1">Delivery person current position</p>
            </div>
          </Popup>
        </Marker>
        
        {/* Locker Markers */}
        {lockers.map((locker, index) => {
          const isSelected = selectedLocker?.id === locker.id;
          const icon = createCustomIcon(
            getMarkerColor(index, isSelected),
            `${index + 1}`
          );
          
          return (
            <Marker
              key={locker.id}
              position={[locker.latitude, locker.longitude]}
              icon={icon}
              eventHandlers={{
                click: () => onLockerSelect(locker),
              }}
            >
              <Popup>
                <div className="min-w-[200px]">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-1 rounded text-xs font-bold text-white ${
                      index === 0 ? 'bg-yellow-500' : index === 1 ? 'bg-gray-400' : 'bg-orange-500'
                    }`}>
                      #{index + 1} {index === 0 ? '🥇' : index === 1 ? '🥈' : '🥉'}
                    </span>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                      Score: {locker.score}
                    </span>
                  </div>
                  <strong className="text-blue-700 block">{locker.name}</strong>
                  <p className="text-xs text-gray-600 mt-1">{locker.address || 'Colombo, Sri Lanka'}</p>
                  <div className="mt-2 pt-2 border-t border-gray-200 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-gray-500">Distance:</span>
                      <span className="font-semibold ml-1">{locker.distance}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Deviation:</span>
                      <span className="font-semibold ml-1">{locker.route_deviation}</span>
                    </div>
                  </div>
                  <div className="mt-2 flex gap-1">
                    <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                      S: {locker.availability.small}
                    </span>
                    <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-xs">
                      M: {locker.availability.medium}
                    </span>
                    <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">
                      L: {locker.availability.large}
                    </span>
                  </div>
                  <button
                    onClick={() => onLockerSelect(locker)}
                    className="w-full mt-3 bg-blue-600 text-white py-2 rounded text-sm font-semibold hover:bg-blue-700"
                  >
                    Select This Locker
                  </button>
                </div>
              </Popup>
            </Marker>
          );
        })}
        
        {/* Courier Route Line */}
        {courierRoute && courierRoute.length > 1 && (
          <Polyline
            positions={courierRoute}
            color="#3B82F6"
            weight={4}
            dashArray="10, 10"
            opacity={0.7}
          />
        )}
      </MapContainer>
      
      {/* Legend Overlay */}
      <div className="absolute bottom-3 left-3 bg-white/95 backdrop-blur-sm rounded-lg p-3 text-xs shadow-lg z-[1000]">
        <div className="font-semibold text-gray-700 mb-2">Map Legend</div>
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-4 h-4 bg-red-500 rounded-full border-2 border-white shadow" />
          <span>Your Location</span>
        </div>
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-4 h-4 bg-yellow-500 rounded border-2 border-white shadow" />
          <span>🥇 Best Match</span>
        </div>
        <div className="flex items-center gap-2 mb-1.5">
          <div className="w-4 h-4 bg-gray-400 rounded border-2 border-white shadow" />
          <span>🥈 2nd Best</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-orange-500 rounded border-2 border-white shadow" />
          <span>🥉 3rd Best</span>
        </div>
      </div>
    </div>
  );
};

export default LockerMap;