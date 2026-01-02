import { useState, useEffect } from 'react';
import { Phone, PhoneOff } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import AudioVisualizer from '../components/AudioVisualizer';
import VoiceStatus from '../components/VoiceStatus';
import { useDatabase } from '../context/MockDatabaseContext';

const CourierCall = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const orderId = searchParams.get('orderId');
    const { orders } = useDatabase();
    const order = orders.find(o => o.id === orderId);

    const [isCallActive, setIsCallActive] = useState(false);
    const [voiceStatus, setVoiceStatus] = useState<'listening' | 'human' | 'ai'>('listening');
    const [callDuration, setCallDuration] = useState(0);

    useEffect(() => {
        let interval: number;
        if (isCallActive) {
            interval = setInterval(() => setCallDuration(prev => prev + 1), 1000);

            // Mock AI detection logic
            const timeout = setTimeout(() => {
                // Randomly detect AI or Human
                const isAi = Math.random() > 0.8; // 20% chance of AI fraud
                setVoiceStatus(isAi ? 'ai' : 'human');
            }, 4000); // Analyze for 4 seconds

            return () => {
                clearInterval(interval);
                clearTimeout(timeout);
            };
        } else {
            setCallDuration(0);
            setVoiceStatus('listening');
        }
    }, [isCallActive]);

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (!order && orderId) return <div className="p-4 text-white">Order not found</div>;

    const recipientName = order ? order.recipientName : "John Doe";

    return (
        <div className="flex flex-col h-full bg-gray-900 text-white">
            <div className="flex-1 flex flex-col items-center justify-center p-6 relative overflow-hidden">
                {/* Background blobs */}
                <div className="absolute top-[-10%] left-[-10%] w-64 h-64 bg-blue-600/20 rounded-full blur-3xl"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-64 h-64 bg-purple-600/20 rounded-full blur-3xl"></div>

                <div className="z-10 w-full max-w-sm flex flex-col gap-8">
                    <div className="text-center">
                        <div className="w-24 h-24 bg-gray-700 rounded-full mx-auto mb-4 flex items-center justify-center text-3xl font-bold">
                            {recipientName.charAt(0)}
                        </div>
                        <h1 className="text-2xl font-bold">{recipientName}</h1>
                        <p className="text-gray-400">{isCallActive ? formatTime(callDuration) : "Calling..."}</p>
                        {order?.voiceEnrolled && (
                            <span className="inline-block mt-2 px-2 py-1 bg-green-900/50 text-green-400 text-xs rounded-full border border-green-800">
                                Voice Profile Matched
                            </span>
                        )}
                    </div>

                    {isCallActive ? (
                        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/10">
                            <VoiceStatus status={voiceStatus} />
                            <div className="mt-6">
                                <AudioVisualizer isActive={true} isAiDetected={voiceStatus === 'ai'} />
                            </div>
                        </div>
                    ) : (
                        <div className="text-center text-gray-400 text-sm">
                            Tap the green button to start the call verification.
                        </div>
                    )}
                </div>
            </div>

            <div className="p-8 pb-24 flex justify-around items-center bg-gray-900/50 backdrop-blur-sm">
                {isCallActive ? (
                    <button
                        onClick={() => {
                            setIsCallActive(false);
                            // Navigate back with voice verification status
                            const isVoiceVerified = voiceStatus === 'human';
                            if (orderId) {
                                navigate(`/courier/delivery/${orderId}?voiceVerified=${isVoiceVerified}`);
                            } else {
                                navigate(-1);
                            }
                        }}
                        className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center shadow-lg hover:bg-red-600 transition-transform active:scale-95"
                    >
                        <PhoneOff size={32} />
                    </button>
                ) : (
                    <button
                        onClick={() => setIsCallActive(true)}
                        className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center shadow-lg hover:bg-green-600 transition-transform active:scale-95 animate-bounce"
                    >
                        <Phone size={32} />
                    </button>
                )}
            </div>
        </div>
    );
};

export default CourierCall;
