import { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { DivIcon } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  Package, 
  MapPin, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw,
  Box,
  Smartphone,
  Wifi,
  Battery,
  ThermometerSun,
  Search,
  Filter,
  Download,
  ChevronDown,
  ChevronUp,
  Activity
} from 'lucide-react';

// Types
interface LockerSlot {
  id: string;
  size: 'small' | 'medium' | 'large';
  status: 'available' | 'reserved' | 'occupied' | 'maintenance';
  orderId?: number;
  reservedAt?: string;
  expiresAt?: string;
}

interface LockerStation {
  id: string;
  name: string;
  address: string;
  latitude: number;
  longitude: number;
  operating_hours: string;
  is_active: boolean;
  total_slots: number;
  small_available: number;
  medium_available: number;
  large_available: number;
  // Simulated IoT data
  temperature?: number;
  humidity?: number;
  lastPing?: string;
  batteryLevel?: number;
  wifiStrength?: number;
  slots?: LockerSlot[];
}

// Custom marker icons
const createStationIcon = (availablePercent: number) => {
  const color = availablePercent > 50 ? '#22c55e' : availablePercent > 20 ? '#f59e0b' : '#ef4444';
  return new DivIcon({
    className: 'custom-station-marker',
    html: `
      <div style="
        background: ${color};
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: 3px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 12px;
      ">
        ${Math.round(availablePercent)}%
      </div>
    `,
    iconSize: [40, 40],
    iconAnchor: [20, 20],
    popupAnchor: [0, -20]
  });
};

export default function LockerNetworkMonitor() {
  const [stations, setStations] = useState<LockerStation[]>([]);
  const [selectedStation, setSelectedStation] = useState<LockerStation | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [viewMode, setViewMode] = useState<'map' | 'grid'>('map');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedStation, setExpandedStation] = useState<string | null>(null);

  // Colombo center coordinates
  const colomboCenter: [number, number] = [6.9271, 79.8612];

  // Fetch locker stations data
  const fetchStations = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/lockers/');
      if (response.ok) {
        const data = await response.json();
        // Add simulated IoT data
        const enrichedData = data.map((station: LockerStation) => ({
          ...station,
          temperature: 24 + Math.random() * 6,
          humidity: 55 + Math.random() * 20,
          lastPing: new Date(Date.now() - Math.random() * 300000).toISOString(),
          batteryLevel: 70 + Math.random() * 30,
          wifiStrength: 60 + Math.random() * 40,
          slots: generateSlots(station)
        }));
        setStations(enrichedData);
      }
    } catch (error) {
      console.error('Failed to fetch stations:', error);
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  };

  // Generate mock slots for a station
  const generateSlots = (station: LockerStation): LockerSlot[] => {
    const slots: LockerSlot[] = [];
    const sizes: Array<'small' | 'medium' | 'large'> = ['small', 'medium', 'large'];
    const statuses: Array<'available' | 'reserved' | 'occupied' | 'maintenance'> = 
      ['available', 'available', 'available', 'reserved', 'occupied', 'maintenance'];
    
    // Generate 50-75 slots per station
    const totalSlots = 50 + Math.floor(Math.random() * 25);
    
    for (let i = 1; i <= totalSlots; i++) {
      const size = sizes[i % 3];
      const sizePrefix = size[0].toUpperCase();
      const status = statuses[Math.floor(Math.random() * statuses.length)];
      
      slots.push({
        id: `${station.id}-${sizePrefix}-${String(i).padStart(3, '0')}`,
        size,
        status,
        ...(status === 'reserved' || status === 'occupied' ? {
          orderId: 1000 + Math.floor(Math.random() * 9000),
          reservedAt: new Date(Date.now() - Math.random() * 86400000).toISOString(),
          expiresAt: new Date(Date.now() + Math.random() * 86400000).toISOString()
        } : {})
      });
    }
    
    return slots;
  };

  useEffect(() => {
    fetchStations();
    
    // Auto-refresh every 30 seconds
    let interval: ReturnType<typeof setInterval> | undefined;
    if (autoRefresh) {
      interval = setInterval(fetchStations, 30000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  // Calculate network statistics
  const networkStats = {
    totalStations: stations.length,
    activeStations: stations.filter(s => s.is_active).length,
    totalSlots: stations.reduce((sum, s) => sum + (s.slots?.length || s.total_slots), 0),
    availableSlots: stations.reduce((sum, s) => 
      sum + s.small_available + s.medium_available + s.large_available, 0
    ),
    occupiedSlots: stations.reduce((sum, s) => {
      const available = s.small_available + s.medium_available + s.large_available;
      return sum + ((s.slots?.length || s.total_slots) - available);
    }, 0),
    maintenanceCount: stations.reduce((sum, s) => 
      sum + (s.slots?.filter(slot => slot.status === 'maintenance').length || 0), 0
    )
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'available': return 'bg-green-500';
      case 'reserved': return 'bg-yellow-500';
      case 'occupied': return 'bg-blue-500';
      case 'maintenance': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const filteredStations = stations.filter(station => {
    const matchesSearch = station.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      station.address.toLowerCase().includes(searchTerm.toLowerCase());
    
    if (filterStatus === 'all') return matchesSearch;
    if (filterStatus === 'active') return matchesSearch && station.is_active;
    if (filterStatus === 'inactive') return matchesSearch && !station.is_active;
    if (filterStatus === 'low') {
      const totalAvailable = station.small_available + station.medium_available + station.large_available;
      const percent = (totalAvailable / station.total_slots) * 100;
      return matchesSearch && percent < 30;
    }
    return matchesSearch;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Loading Network Status...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-2xl font-bold">Locker Network Monitor</h1>
              <p className="text-gray-400 text-sm">
                Real-time monitoring of all Smart Locker stations in Colombo
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-400">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </div>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-1 rounded text-sm ${
                autoRefresh ? 'bg-green-600' : 'bg-gray-600'
              }`}
            >
              Auto-refresh: {autoRefresh ? 'ON' : 'OFF'}
            </button>
            <button
              onClick={fetchStations}
              className="p-2 bg-blue-600 rounded hover:bg-blue-700"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-6 gap-4 p-4 bg-gray-800/50">
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <MapPin className="w-4 h-4" />
            Total Stations
          </div>
          <div className="text-2xl font-bold">{networkStats.totalStations}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center gap-2 text-green-400 text-sm mb-1">
            <CheckCircle2 className="w-4 h-4" />
            Active
          </div>
          <div className="text-2xl font-bold text-green-400">{networkStats.activeStations}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Box className="w-4 h-4" />
            Total Slots
          </div>
          <div className="text-2xl font-bold">{networkStats.totalSlots}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center gap-2 text-green-400 text-sm mb-1">
            <Package className="w-4 h-4" />
            Available
          </div>
          <div className="text-2xl font-bold text-green-400">{networkStats.availableSlots}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center gap-2 text-blue-400 text-sm mb-1">
            <Clock className="w-4 h-4" />
            Occupied
          </div>
          <div className="text-2xl font-bold text-blue-400">{networkStats.occupiedSlots}</div>
        </div>
        <div className="bg-gray-800 p-4 rounded-lg">
          <div className="flex items-center gap-2 text-red-400 text-sm mb-1">
            <AlertTriangle className="w-4 h-4" />
            Maintenance
          </div>
          <div className="text-2xl font-bold text-red-400">{networkStats.maintenanceCount}</div>
        </div>
      </div>

      {/* Controls */}
      <div className="p-4 flex items-center gap-4 bg-gray-800/30">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search stations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-400" />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2"
          >
            <option value="all">All Stations</option>
            <option value="active">Active Only</option>
            <option value="inactive">Inactive</option>
            <option value="low">Low Availability (&lt;30%)</option>
          </select>
        </div>
        <div className="flex bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('map')}
            className={`px-4 py-1 rounded ${viewMode === 'map' ? 'bg-blue-600' : ''}`}
          >
            Map View
          </button>
          <button
            onClick={() => setViewMode('grid')}
            className={`px-4 py-1 rounded ${viewMode === 'grid' ? 'bg-blue-600' : ''}`}
          >
            Grid View
          </button>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-gray-800 rounded hover:bg-gray-700">
          <Download className="w-5 h-5" />
          Export Report
        </button>
      </div>

      {/* Main Content */}
      <div className="flex gap-4 p-4 h-[calc(100vh-280px)]">
        {/* Map / Grid View */}
        <div className="flex-1 bg-gray-800 rounded-lg overflow-hidden">
          {viewMode === 'map' ? (
            <MapContainer
              center={colomboCenter}
              zoom={13}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
              />
              {filteredStations.map((station) => {
                const totalAvailable = station.small_available + station.medium_available + station.large_available;
                const availablePercent = (totalAvailable / station.total_slots) * 100;
                
                return (
                  <Marker
                    key={station.id}
                    position={[station.latitude, station.longitude]}
                    icon={createStationIcon(availablePercent)}
                    eventHandlers={{
                      click: () => setSelectedStation(station)
                    }}
                  >
                    <Popup>
                      <div className="p-2 min-w-[200px]">
                        <h3 className="font-bold text-lg">{station.name}</h3>
                        <p className="text-gray-600 text-sm">{station.address}</p>
                        <div className="mt-2 space-y-1">
                          <div className="flex justify-between">
                            <span>Small:</span>
                            <span className="font-medium">{station.small_available} available</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Medium:</span>
                            <span className="font-medium">{station.medium_available} available</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Large:</span>
                            <span className="font-medium">{station.large_available} available</span>
                          </div>
                        </div>
                        <button
                          onClick={() => setSelectedStation(station)}
                          className="mt-2 w-full py-1 bg-blue-500 text-white rounded text-sm"
                        >
                          View Details
                        </button>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          ) : (
            <div className="p-4 overflow-auto h-full">
              <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredStations.map((station) => {
                  const totalAvailable = station.small_available + station.medium_available + station.large_available;
                  const availablePercent = (totalAvailable / station.total_slots) * 100;
                  
                  return (
                    <div
                      key={station.id}
                      className={`bg-gray-700 rounded-lg p-4 cursor-pointer hover:bg-gray-600 transition ${
                        selectedStation?.id === station.id ? 'ring-2 ring-blue-500' : ''
                      }`}
                      onClick={() => setSelectedStation(station)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-bold">{station.name}</h3>
                          <p className="text-gray-400 text-sm">{station.address}</p>
                        </div>
                        <div className={`px-2 py-1 rounded text-xs ${
                          station.is_active ? 'bg-green-600' : 'bg-red-600'
                        }`}>
                          {station.is_active ? 'Active' : 'Offline'}
                        </div>
                      </div>
                      
                      {/* Availability Bar */}
                      <div className="mt-3">
                        <div className="flex justify-between text-sm mb-1">
                          <span>Availability</span>
                          <span>{Math.round(availablePercent)}%</span>
                        </div>
                        <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              availablePercent > 50 ? 'bg-green-500' : 
                              availablePercent > 20 ? 'bg-yellow-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${availablePercent}%` }}
                          />
                        </div>
                      </div>
                      
                      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                        <div className="bg-gray-800 rounded p-2">
                          <div className="text-green-400 font-bold">{station.small_available}</div>
                          <div className="text-gray-400">Small</div>
                        </div>
                        <div className="bg-gray-800 rounded p-2">
                          <div className="text-yellow-400 font-bold">{station.medium_available}</div>
                          <div className="text-gray-400">Medium</div>
                        </div>
                        <div className="bg-gray-800 rounded p-2">
                          <div className="text-blue-400 font-bold">{station.large_available}</div>
                          <div className="text-gray-400">Large</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Station Details Panel */}
        <div className="w-96 bg-gray-800 rounded-lg overflow-auto">
          {selectedStation ? (
            <div className="p-4">
              <h2 className="text-xl font-bold mb-1">{selectedStation.name}</h2>
              <p className="text-gray-400 text-sm mb-4">{selectedStation.address}</p>
              
              {/* IoT Status */}
              <div className="bg-gray-700 rounded-lg p-4 mb-4">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Smartphone className="w-5 h-5 text-blue-400" />
                  IoT Status
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <div className="flex items-center gap-2">
                    <ThermometerSun className="w-4 h-4 text-orange-400" />
                    <span className="text-sm">{selectedStation.temperature?.toFixed(1)}°C</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Wifi className="w-4 h-4 text-green-400" />
                    <span className="text-sm">{selectedStation.wifiStrength?.toFixed(0)}%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Battery className="w-4 h-4 text-yellow-400" />
                    <span className="text-sm">{selectedStation.batteryLevel?.toFixed(0)}%</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-gray-400" />
                    <span className="text-sm">
                      {selectedStation.lastPing ? 
                        `${Math.round((Date.now() - new Date(selectedStation.lastPing).getTime()) / 1000)}s ago` : 
                        'N/A'
                      }
                    </span>
                  </div>
                </div>
              </div>

              {/* Slot Grid */}
              <div className="bg-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Slot Grid ({selectedStation.slots?.length || 0} slots)</h3>
                  <button
                    onClick={() => setExpandedStation(
                      expandedStation === selectedStation.id ? null : selectedStation.id
                    )}
                    className="p-1 hover:bg-gray-600 rounded"
                  >
                    {expandedStation === selectedStation.id ? 
                      <ChevronUp className="w-5 h-5" /> : 
                      <ChevronDown className="w-5 h-5" />
                    }
                  </button>
                </div>
                
                {/* Legend */}
                <div className="flex gap-3 mb-3 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-green-500 rounded" />
                    <span>Available</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-yellow-500 rounded" />
                    <span>Reserved</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-blue-500 rounded" />
                    <span>Occupied</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-red-500 rounded" />
                    <span>Maintenance</span>
                  </div>
                </div>

                {/* Slot Visualization */}
                <div className={`grid grid-cols-10 gap-1 ${
                  expandedStation === selectedStation.id ? '' : 'max-h-40 overflow-hidden'
                }`}>
                  {selectedStation.slots?.map((slot) => (
                    <div
                      key={slot.id}
                      className={`aspect-square rounded cursor-pointer transition-transform hover:scale-110 ${getStatusColor(slot.status)}`}
                      title={`${slot.id}\nSize: ${slot.size}\nStatus: ${slot.status}${slot.orderId ? `\nOrder: #${slot.orderId}` : ''}`}
                    />
                  ))}
                </div>

                {/* Slot Stats */}
                <div className="mt-4 pt-4 border-t border-gray-600">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Available:</span>
                      <span className="text-green-400">
                        {selectedStation.slots?.filter(s => s.status === 'available').length || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Reserved:</span>
                      <span className="text-yellow-400">
                        {selectedStation.slots?.filter(s => s.status === 'reserved').length || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Occupied:</span>
                      <span className="text-blue-400">
                        {selectedStation.slots?.filter(s => s.status === 'occupied').length || 0}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Maintenance:</span>
                      <span className="text-red-400">
                        {selectedStation.slots?.filter(s => s.status === 'maintenance').length || 0}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button className="py-2 bg-blue-600 rounded hover:bg-blue-700 text-sm">
                  View All Reservations
                </button>
                <button className="py-2 bg-gray-700 rounded hover:bg-gray-600 text-sm">
                  Station Settings
                </button>
                <button className="py-2 bg-yellow-600 rounded hover:bg-yellow-700 text-sm">
                  Run Diagnostics
                </button>
                <button className="py-2 bg-red-600 rounded hover:bg-red-700 text-sm">
                  Emergency Unlock All
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <MapPin className="w-16 h-16 mb-4 opacity-50" />
              <p>Select a station to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
