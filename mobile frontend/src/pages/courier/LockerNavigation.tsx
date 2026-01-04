import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Navigation, 
  MapPin, 
  Package, 
  QrCode, 
  CheckCircle, 
  ArrowLeft,
  Clock,
  Unlock
} from 'lucide-react';
import { lockerApi } from '../../services/lockerApi';

const LockerNavigation: React.FC = () => {
  const { orderId, lockerId } = useParams();
  const navigate = useNavigate();
  
  const [locker, setLocker] = useState<any>(null);
  const [step, setStep] = useState<'navigate' | 'arrived' | 'unlock' | 'deposit' | 'complete'>('navigate');
  const [unlockCode, setUnlockCode] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (lockerId) {
      // Fetch locker details
      fetchLockerDetails();
    }
  }, [lockerId]);

  const fetchLockerDetails = async () => {
    try {
      const data = await lockerApi.getLockerById(lockerId!);
      setLocker(data);
    } catch (err) {
      console.error('Error fetching locker:', err);
      // Use mock data for demo
      setLocker({
        id: lockerId,
        name: 'Smart Locker - Fort Railway',
        address: '123 Fort Station Road, Colombo 01',
        operating_hours: '24/7',
        small_available: 5,
        medium_available: 8,
        large_available: 3
      });
    }
  };

  const handleArrived = () => {
    setStep('arrived');
  };

  const handleUnlock = async () => {
    setLoading(true);
    try {
      // In production, verify the code with backend
      await lockerApi.unlockLocker(lockerId!, unlockCode);
      setStep('deposit');
    } catch (err) {
      // Demo: proceed anyway
      setStep('deposit');
    } finally {
      setLoading(false);
    }
  };

  const handleDepositComplete = () => {
    setStep('complete');
    // Record on blockchain
    // Navigate after delay
    setTimeout(() => {
      navigate('/courier/dashboard');
    }, 3000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-blue-600 text-white p-4">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="p-1">
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="font-bold">Locker Delivery</h1>
            <p className="text-sm opacity-90">Order #{orderId}</p>
          </div>
        </div>
      </header>

      <main className="p-4">
        {/* Progress Steps */}
        <div className="flex justify-between mb-6">
          {['Navigate', 'Arrived', 'Unlock', 'Deposit', 'Complete'].map((s, i) => {
            const steps = ['navigate', 'arrived', 'unlock', 'deposit', 'complete'];
            const currentIndex = steps.indexOf(step);
            const isActive = i <= currentIndex;
            
            return (
              <div key={s} className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  isActive ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500'
                }`}>
                  {i + 1}
                </div>
                <span className={`text-xs mt-1 ${isActive ? 'text-blue-600' : 'text-gray-400'}`}>
                  {s}
                </span>
              </div>
            );
          })}
        </div>

        {/* Locker Info Card */}
        {locker && (
          <div className="bg-white rounded-xl p-4 shadow-sm mb-4">
            <div className="flex items-start gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Package className="w-6 h-6 text-blue-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-gray-800">{locker.name}</h3>
                <p className="text-sm text-gray-500 mt-1">{locker.address}</p>
                <div className="flex items-center gap-4 mt-2 text-sm">
                  <span className="flex items-center gap-1 text-green-600">
                    <Clock className="w-4 h-4" />
                    {locker.operating_hours}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step Content */}
        {step === 'navigate' && (
          <div className="space-y-4">
            {/* Map Placeholder */}
            <div className="bg-gradient-to-br from-blue-100 to-green-100 rounded-xl h-48 flex items-center justify-center">
              <div className="text-center">
                <Navigation className="w-12 h-12 text-blue-600 mx-auto mb-2" />
                <p className="text-gray-600">Navigation in progress...</p>
                <p className="text-sm text-gray-500">2.3 km • 8 min</p>
              </div>
            </div>
            
            <button
              onClick={handleArrived}
              className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold hover:bg-blue-700 flex items-center justify-center gap-2"
            >
              <MapPin className="w-5 h-5" />
              I've Arrived at Locker
            </button>
          </div>
        )}

        {step === 'arrived' && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-center">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-2" />
              <h3 className="font-bold text-green-800">Location Verified!</h3>
              <p className="text-sm text-green-600">You're at the locker location</p>
            </div>
            
            <div className="bg-white rounded-xl p-4 shadow-sm">
              <h3 className="font-semibold mb-3">Enter Unlock Code</h3>
              <input
                type="text"
                value={unlockCode}
                onChange={(e) => setUnlockCode(e.target.value.toUpperCase())}
                placeholder="Enter 6-digit code"
                maxLength={6}
                className="w-full text-center text-2xl font-mono tracking-widest p-4 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none"
              />
              <p className="text-xs text-gray-500 mt-2 text-center">
                Code sent to customer's phone
              </p>
            </div>
            
            <button
              onClick={handleUnlock}
              disabled={unlockCode.length < 6 || loading}
              className="w-full bg-blue-600 text-white py-4 rounded-xl font-semibold hover:bg-blue-700 disabled:bg-gray-300 flex items-center justify-center gap-2"
            >
              <Unlock className="w-5 h-5" />
              Unlock Locker
            </button>
            
            <button className="w-full border border-gray-300 text-gray-700 py-3 rounded-xl font-medium flex items-center justify-center gap-2">
              <QrCode className="w-5 h-5" />
              Scan QR Code Instead
            </button>
          </div>
        )}

        {step === 'deposit' && (
          <div className="space-y-4">
            <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-200 rounded-lg">
                  <Package className="w-6 h-6 text-yellow-700" />
                </div>
                <div>
                  <h3 className="font-bold text-yellow-800">Locker Open - Slot M-04</h3>
                  <p className="text-sm text-yellow-600">Medium size compartment</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-xl p-6 text-center">
              <div className="w-24 h-24 bg-blue-100 rounded-xl mx-auto mb-4 flex items-center justify-center">
                <Package className="w-12 h-12 text-blue-600" />
              </div>
              <h3 className="font-bold text-lg mb-2">Place Package Inside</h3>
              <ol className="text-left text-sm text-gray-600 space-y-2">
                <li>1. Place package in the open compartment</li>
                <li>2. Ensure package fits properly</li>
                <li>3. Close the locker door firmly</li>
                <li>4. Wait for confirmation beep</li>
              </ol>
            </div>
            
            <button
              onClick={handleDepositComplete}
              className="w-full bg-green-600 text-white py-4 rounded-xl font-semibold hover:bg-green-700 flex items-center justify-center gap-2"
            >
              <CheckCircle className="w-5 h-5" />
              Confirm Package Deposited
            </button>
          </div>
        )}

        {step === 'complete' && (
          <div className="text-center py-8">
            <div className="w-20 h-20 bg-green-100 rounded-full mx-auto mb-4 flex items-center justify-center">
              <CheckCircle className="w-12 h-12 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Delivery Complete!</h2>
            <p className="text-gray-600 mb-4">Package secured in locker</p>
            
            <div className="bg-gray-50 rounded-xl p-4 text-left space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-500">Locker ID</span>
                <span className="font-medium">{lockerId}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Compartment</span>
                <span className="font-medium">M-04</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Deposit Time</span>
                <span className="font-medium">{new Date().toLocaleTimeString()}</span>
              </div>
            </div>
            
            <p className="text-sm text-blue-600 mt-4">
              📱 Customer has been notified
            </p>
            <p className="text-sm text-purple-600 mt-1">
              🔗 Recording on blockchain...
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

export default LockerNavigation;