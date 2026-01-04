import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  RefreshCw, 
  ArrowLeft, 
  CheckCircle2,
  Loader2,
  Sparkles,
  Brain,
  MapPin,
  Navigation,
  AlertCircle,
  Crosshair
} from 'lucide-react';
import LockerCard from '../../components/LockerCard';
import LockerMap from '../../components/LockerMap';
import { lockerApi } from '../../services/lockerApi';
import type { LockerRecommendation } from '../../types/locker';

const LockerSelection: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('orderId');

  // Location states
  const [locationStep, setLocationStep] = useState<'asking' | 'loading' | 'granted' | 'manual' | 'denied'>('asking');
  const [customerLocation, setCustomerLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [manualAddress, setManualAddress] = useState('');
  const [locationError, setLocationError] = useState<string | null>(null);

  // Recommendation states
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<LockerRecommendation[]>([]);
  const [selectedLocker, setSelectedLocker] = useState<LockerRecommendation | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Mock courier route (in production, fetch from assigned courier's GPS)
  const [courierLocation] = useState({ lat: 6.9344, lng: 79.8428 }); // Fort area
  const [courierRoute, setCourierRoute] = useState<[number, number][]>([]);

  // Request GPS location
  const requestGPSLocation = () => {
    setLocationStep('loading');
    setLocationError(null);

    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by your browser');
      setLocationStep('manual');
      return;
    }

    // Success callback
    const onSuccess = (position: GeolocationPosition) => {
      const { latitude, longitude } = position.coords;
      setCustomerLocation({ lat: latitude, lng: longitude });
      setLocationStep('granted');
      
      // Generate courier route from courier to customer
      generateCourierRoute(courierLocation, { lat: latitude, lng: longitude });
    };

    // Error callback
    const onError = (error: GeolocationPositionError) => {
      console.error('GPS Error:', error);
      
      // If high accuracy failed, try with lower accuracy (faster)
      if (error.code === error.TIMEOUT) {
        console.log('Retrying with lower accuracy...');
        navigator.geolocation.getCurrentPosition(
          onSuccess,
          (retryError) => {
            console.error('GPS Retry Error:', retryError);
            handleLocationError(retryError);
          },
          {
            enableHighAccuracy: false,
            timeout: 30000,
            maximumAge: 60000 // Accept cached position up to 1 minute old
          }
        );
        return;
      }
      
      handleLocationError(error);
    };

    const handleLocationError = (error: GeolocationPositionError) => {
      switch (error.code) {
        case error.PERMISSION_DENIED:
          setLocationError('Location permission denied. Please enter your address manually.');
          break;
        case error.POSITION_UNAVAILABLE:
          setLocationError('Location information unavailable. Please enter your address manually.');
          break;
        case error.TIMEOUT:
          setLocationError('Location request timed out. Please enter your address manually or use a Colombo location below.');
          break;
        default:
          setLocationError('Unable to get your location. Please enter manually.');
      }
      setLocationStep('manual');
    };

    // First try with high accuracy
    navigator.geolocation.getCurrentPosition(
      onSuccess,
      onError,
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 30000 // Accept cached position up to 30 seconds old
      }
    );
  };

  // Use default Colombo location (fallback)
  const useDefaultLocation = (locationName: string) => {
    const colomboLocations: Record<string, { lat: number; lng: number }> = {
      'Colombo Fort': { lat: 6.9344, lng: 79.8428 },
      'Bambalapitiya': { lat: 6.8950, lng: 79.8567 },
      'Wellawatte': { lat: 6.8742, lng: 79.8612 },
      'Nugegoda': { lat: 6.8716, lng: 79.8916 },
      'Dehiwala': { lat: 6.8560, lng: 79.8650 },
      'Kollupitiya': { lat: 6.9100, lng: 79.8512 },
      'Liberty Plaza': { lat: 6.9157, lng: 79.8636 },
      'Havelock': { lat: 6.8800, lng: 79.8700 },
    };

    const location = colomboLocations[locationName];
    if (location) {
      setCustomerLocation(location);
      setLocationStep('granted');
      generateCourierRoute(courierLocation, location);
    }
  };

  // Geocode manual address to coordinates
  const geocodeAddress = async () => {
    if (!manualAddress.trim()) {
      setLocationError('Please enter an address');
      return;
    }

    setLocationStep('loading');
    setLocationError(null);

    try {
      // Using OpenStreetMap Nominatim for geocoding (free, no API key)
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(manualAddress + ', Colombo, Sri Lanka')}&limit=1`
      );
      const data = await response.json();

      if (data && data.length > 0) {
        const { lat, lon } = data[0];
        setCustomerLocation({ lat: parseFloat(lat), lng: parseFloat(lon) });
        setLocationStep('granted');
        generateCourierRoute(courierLocation, { lat: parseFloat(lat), lng: parseFloat(lon) });
      } else {
        setLocationError('Address not found. Please try a different address or use GPS.');
        setLocationStep('manual');
      }
    } catch (err) {
      console.error('Geocoding error:', err);
      setLocationError('Failed to find address. Please try again.');
      setLocationStep('manual');
    }
  };

  // Generate route waypoints from courier to customer
  const generateCourierRoute = (from: { lat: number; lng: number }, to: { lat: number; lng: number }) => {
    // Generate intermediate waypoints (in production, use routing API)
    const steps = 5;
    const route: [number, number][] = [];
    
    for (let i = 0; i <= steps; i++) {
      const lat = from.lat + (to.lat - from.lat) * (i / steps);
      const lng = from.lng + (to.lng - from.lng) * (i / steps);
      route.push([lat, lng]);
    }
    
    setCourierRoute(route);
  };

  // Fetch recommendations when location is available
  useEffect(() => {
    if (locationStep === 'granted' && customerLocation && courierRoute.length > 0) {
      fetchRecommendations();
    }
  }, [locationStep, customerLocation, courierRoute]);

  const fetchRecommendations = async () => {
    if (!customerLocation) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await lockerApi.getRecommendations({
        latitude: customerLocation.lat,
        longitude: customerLocation.lng,
        courier_route: courierRoute,
        package_size: 'medium'
      });

      if (response.success) {
        const transformedRecommendations: LockerRecommendation[] = response.recommendations.map((r: any) => ({
          id: r.id,
          name: r.name,
          latitude: r.latitude || 0,
          longitude: r.longitude || 0,
          score: r.score,
          distance: r.distance,
          address: r.address || '',
          availability: {
            small: r.availability?.small || 0,
            medium: r.availability?.medium || 0,
            large: r.availability?.large || 0
          },
          route_deviation: r.route_deviation || 'N/A',
          predicted_availability: r.predicted_availability || Math.round(r.score)
        }));
        
        setRecommendations(transformedRecommendations);
        
        if (transformedRecommendations.length > 0) {
          setSelectedLocker(transformedRecommendations[0]);
        }
      } else {
        setError('Failed to get recommendations');
      }
    } catch (err: any) {
      console.error('Error fetching recommendations:', err);
      setError(err.message || 'Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmLocker = async () => {
    if (!selectedLocker || !orderId) return;
    
    setConfirming(true);
    try {
      const result = await lockerApi.reserveSlot(selectedLocker.id, parseInt(orderId) || 1, 'medium');
      
      // Navigate to confirmation page with locker details
      navigate(`/client/checkout?orderId=${orderId}&lockerId=${selectedLocker.id}&code=${result.unlock_code}`);
    } catch (err) {
      console.error('Error reserving locker:', err);
      setError('Failed to reserve locker slot');
    } finally {
      setConfirming(false);
    }
  };

  // STEP 1: Ask for Location Permission
  if (locationStep === 'asking') {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm sticky top-0 z-10">
          <div className="flex items-center justify-between p-4">
            <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-full">
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div className="text-center">
              <h1 className="font-bold text-lg">Smart Locker Selection</h1>
              <p className="text-xs text-gray-500">AI-Powered Recommendations</p>
            </div>
            <div className="w-10" />
          </div>
        </header>

        <main className="p-4 flex items-center justify-center min-h-[80vh]">
          <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
            <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <MapPin className="w-10 h-10 text-blue-600" />
            </div>
            
            <h2 className="text-2xl font-bold text-gray-800 mb-3">
              Where are you located?
            </h2>
            
            <p className="text-gray-600 mb-6">
              We need your location to find the <strong>nearest smart lockers</strong> and optimize the delivery route for you.
            </p>

            <div className="space-y-3">
              <button
                onClick={requestGPSLocation}
                className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center gap-3"
              >
                <Crosshair className="w-5 h-5" />
                Use My Current Location
              </button>
              
              <button
                onClick={() => setLocationStep('manual')}
                className="w-full border-2 border-gray-300 text-gray-700 py-4 rounded-xl font-semibold hover:bg-gray-50 transition-colors flex items-center justify-center gap-3"
              >
                <Navigation className="w-5 h-5" />
                Enter Address Manually
              </button>
            </div>

            <p className="text-xs text-gray-400 mt-6">
              🔒 Your location is only used to find nearby lockers and is not stored.
            </p>
          </div>
        </main>
      </div>
    );
  }

  // STEP 2: Loading Location
  if (locationStep === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center">
          <Loader2 className="w-16 h-16 animate-spin text-blue-500 mx-auto mb-6" />
          <h2 className="text-xl font-bold text-gray-800 mb-2">Getting Your Location...</h2>
          <p className="text-gray-500">Please wait while we detect your position</p>
        </div>
      </div>
    );
  }

  // STEP 3: Manual Address Entry
  if (locationStep === 'manual') {
    return (
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm sticky top-0 z-10">
          <div className="flex items-center justify-between p-4">
            <button onClick={() => setLocationStep('asking')} className="p-2 hover:bg-gray-100 rounded-full">
              <ArrowLeft className="w-6 h-6" />
            </button>
            <div className="text-center">
              <h1 className="font-bold text-lg">Enter Your Location</h1>
            </div>
            <div className="w-10" />
          </div>
        </header>

        <main className="p-4">
          <div className="bg-white rounded-2xl shadow-lg p-6 max-w-md mx-auto">
            <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Navigation className="w-8 h-8 text-orange-600" />
            </div>
            
            <h2 className="text-xl font-bold text-gray-800 mb-2 text-center">
              Enter Your Delivery Address
            </h2>
            
            <p className="text-gray-500 text-sm text-center mb-6">
              Enter your address in Colombo to find nearby smart lockers
            </p>

            {locationError && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <p className="text-red-700 text-sm">{locationError}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Street Address or Landmark
                </label>
                <input
                  type="text"
                  value={manualAddress}
                  onChange={(e) => setManualAddress(e.target.value)}
                  placeholder="e.g., Liberty Plaza, Colombo 03"
                  className="w-full p-4 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-xs text-gray-500 font-medium mb-2">📍 Quick Select (No GPS needed):</p>
                <div className="flex flex-wrap gap-2">
                  {['Colombo Fort', 'Bambalapitiya', 'Wellawatte', 'Nugegoda', 'Dehiwala', 'Liberty Plaza', 'Havelock'].map((loc) => (
                    <button
                      key={loc}
                      onClick={() => useDefaultLocation(loc)}
                      className="text-xs bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-full hover:bg-blue-100 hover:border-blue-400 text-blue-700 font-medium"
                    >
                      📍 {loc}
                    </button>
                  ))}
                </div>
              </div>

              <div className="border-t pt-4">
                <p className="text-xs text-gray-500 mb-2">Or enter custom address:</p>
                <button
                  onClick={geocodeAddress}
                  disabled={!manualAddress.trim()}
                  className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                  Search Address
                </button>
              </div>

              <button
                onClick={requestGPSLocation}
                className="w-full text-blue-600 py-2 font-medium hover:underline"
              >
                ← Try GPS Location Again
              </button>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // STEP 4: Show Recommendations (Location Granted)
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="flex items-center justify-between p-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-full">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div className="text-center">
            <h1 className="font-bold text-lg">Smart Locker Selection</h1>
            <p className="text-xs text-gray-500">AI-Powered Recommendations</p>
          </div>
          <button 
            onClick={fetchRecommendations}
            className="p-2 hover:bg-gray-100 rounded-full"
            disabled={loading}
          >
            <RefreshCw className={`w-6 h-6 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </header>

      <main className="p-4 pb-32">
        {/* Location Info Banner */}
        {customerLocation && (
          <div className="bg-green-50 border border-green-200 rounded-xl p-3 mb-4 flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
              <MapPin className="w-5 h-5 text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-green-800 font-medium text-sm">Your Location Detected</p>
              <p className="text-green-600 text-xs">
                📍 {customerLocation.lat.toFixed(4)}, {customerLocation.lng.toFixed(4)}
              </p>
            </div>
            <button 
              onClick={() => setLocationStep('asking')}
              className="text-green-600 text-xs underline"
            >
              Change
            </button>
          </div>
        )}

        {/* Courier Info Banner */}
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-3 mb-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
            <Navigation className="w-5 h-5 text-orange-600" />
          </div>
          <div className="flex-1">
            <p className="text-orange-800 font-medium text-sm">🚚 Courier Location</p>
            <p className="text-orange-600 text-xs">
              📍 Fort Railway Station ({courierLocation.lat.toFixed(4)}, {courierLocation.lng.toFixed(4)})
            </p>
          </div>
        </div>

        {/* AI Badge */}
        <div className="bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl p-4 mb-4 text-white">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-white/20 rounded-lg">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <h2 className="font-bold flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                ST-GNN AI Recommendation
              </h2>
              <p className="text-sm opacity-90">
                Optimized for your location & courier route
              </p>
            </div>
          </div>
        </div>

        {/* Map Section */}
        {customerLocation && (
          <div className="mb-4">
            <LockerMap
              lockers={recommendations}
              customerLocation={customerLocation}
              courierLocation={{ lat: 6.9344, lng: 79.8428 }}
              courierRoute={courierRoute}
              selectedLocker={selectedLocker}
              onLockerSelect={setSelectedLocker}
            />
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-xl p-8 text-center">
            <Loader2 className="w-12 h-12 animate-spin text-blue-500 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-800">Analyzing Locations...</h3>
            <p className="text-sm text-gray-500 mt-2">
              Running ST-GNN model to find optimal lockers
            </p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-4">
            <p className="text-red-700 font-medium">{error}</p>
            <button onClick={fetchRecommendations} className="mt-2 text-red-600 underline text-sm">
              Try again
            </button>
          </div>
        )}

        {/* Recommendations List */}
        {!loading && recommendations.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-gray-800">
                Top {recommendations.length} Recommendations
              </h3>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                Sorted by AI Score
              </span>
            </div>
            
            {recommendations.map((locker, index) => (
              <LockerCard
                key={locker.id}
                locker={locker}
                rank={index + 1}
                isSelected={selectedLocker?.id === locker.id}
                onSelect={setSelectedLocker}
              />
            ))}
          </div>
        )}
      </main>

      {/* Bottom Action Bar */}
      {selectedLocker && !loading && (
        <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4 shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <div>
              <p className="text-sm text-gray-500">Selected Locker</p>
              <p className="font-bold text-gray-800">{selectedLocker.name}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500">AI Score</p>
              <p className="font-bold text-green-600">{selectedLocker.score.toFixed(1)}/100</p>
            </div>
          </div>
          <button
            onClick={handleConfirmLocker}
            disabled={confirming}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-semibold hover:bg-blue-700 transition-colors disabled:bg-blue-300 flex items-center justify-center gap-2"
          >
            {confirming ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Reserving...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Confirm Locker Selection
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};

export default LockerSelection;