import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, User, Camera, CheckCircle, XCircle, ImageIcon, Shield } from 'lucide-react';
import FaceScanner from '../../components/FaceScanner';
import { ordersApi } from '../../services/api';
import type { FrontendOrder } from '../../services/api';

const DeliveryDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    
    // State for order from backend
    const [order, setOrder] = useState<FrontendOrder | null>(null);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);

    const [step, setStep] = useState<'info' | 'scan' | 'result'>('info');
    const [resultStatus, setResultStatus] = useState<'success' | 'failed' | 'locker'>('success');
    const [verifying, setVerifying] = useState(false);
    const [verificationDetails, setVerificationDetails] = useState<string>('');
    
    // Customer's reference image
    const [referenceImage, setReferenceImage] = useState<string | null>(null);
    const [loadingReference, setLoadingReference] = useState(false);
    const [referenceError, setReferenceError] = useState<string | null>(null);
    
    // Captured live image for comparison display
    const [capturedImage, setCapturedImage] = useState<string | null>(null);

    // Fetch order from backend
    useEffect(() => {
        const fetchOrder = async () => {
            if (!id) return;
            
            try {
                setLoading(true);
                setFetchError(null);
                const orderId = parseInt(id);
                if (isNaN(orderId)) {
                    throw new Error('Invalid order ID');
                }
                const fetchedOrder = await ordersApi.getOrder(orderId);
                setOrder(fetchedOrder);
            } catch (err) {
                console.error('Error fetching order:', err);
                setFetchError(err instanceof Error ? err.message : 'Failed to load order');
            } finally {
                setLoading(false);
            }
        };

        fetchOrder();
    }, [id]);

    // Fetch customer's reference image when order loads
    useEffect(() => {
        const fetchReferenceImage = async () => {
            if (!order?.customerId) return;
            
            try {
                setLoadingReference(true);
                setReferenceError(null);
                const token = localStorage.getItem('token');
                
                if (!token) {
                    // No token - redirect to login
                    navigate('/login');
                    return;
                }
                
                const response = await fetch(`http://127.0.0.1:8000/api/face/reference/${order.customerId}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.image_data) {
                        setReferenceImage(data.image_data);
                    }
                } else if (response.status === 401) {
                    // Token expired - clear and redirect to login
                    localStorage.removeItem('token');
                    localStorage.removeItem('user');
                    navigate('/login');
                    return;
                } else if (response.status === 404) {
                    setReferenceError('Customer has not enrolled their face yet');
                } else {
                    setReferenceError('Failed to load reference image');
                }
            } catch (err) {
                console.error('Error fetching reference image:', err);
                setReferenceError('Connection error');
            } finally {
                setLoadingReference(false);
            }
        };

        if (order && step === 'scan') {
            fetchReferenceImage();
        }
    }, [order, step]);

    // Update order status in backend
    const updateOrderStatus = async (status: string) => {
        if (!order) return;
        try {
            const updatedOrder = await ordersApi.updateOrderStatus(order.orderId, status);
            setOrder(updatedOrder);
        } catch (err) {
            console.error('Error updating order:', err);
        }
    };

    // Loading state
    if (loading) {
        return (
            <div className="flex flex-col h-full bg-gray-50 items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                <span className="mt-2 text-gray-600">Loading order...</span>
            </div>
        );
    }

    // Error state
    if (fetchError || !order) {
        return (
            <div className="flex flex-col h-full bg-gray-50">
                <header className="bg-white p-4 shadow-sm flex items-center gap-3">
                    <button onClick={() => navigate(-1)} className="text-gray-600">
                        <ArrowLeft size={24} />
                    </button>
                    <h1 className="text-lg font-bold text-gray-800">Order Not Found</h1>
                </header>
                <div className="flex-1 p-4 flex flex-col items-center justify-center">
                    <AlertTriangle size={48} className="text-orange-500 mb-4" />
                    <p className="text-gray-700 font-medium">{fetchError || 'Order not found'}</p>
                    <button
                        onClick={() => navigate('/courier')}
                        className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg"
                    >
                        Back to Dashboard
                    </button>
                </div>
            </div>
        );
    }

    const handleScanComplete = async (imageFile: File | null, imageUrl?: string) => {
        if (!imageFile) {
            setVerificationDetails('❌ No image captured');
            return;
        }

        // Store captured image for display
        if (imageUrl) {
            setCapturedImage(imageUrl);
        }

        setVerifying(true);
        setVerificationDetails('Processing with 3-model AI system...');

        try {
            const token = localStorage.getItem('token');
            
            if (!token) {
                setVerificationDetails('❌ Not logged in');
                setResultStatus('failed');
                setStep('result');
                setVerifying(false);
                return;
            }

            // Use actual customer_id from the order (from backend)
            const customerId = order.customerId;

            const formData = new FormData();
            formData.append('file', imageFile);
            formData.append('user_id', customerId.toString());
            
            // Use the numeric order ID for API
            formData.append('order_id', order.orderId.toString());

            setVerificationDetails(`Verifying Customer #${customerId} with ArcFace + Facenet512 + VGG-Face...`);

            const response = await fetch('http://127.0.0.1:8000/api/face/verify', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            const data = await response.json();

            if (response.status === 401) {
                // Token expired - clear and redirect to login
                localStorage.removeItem('token');
                localStorage.removeItem('user');
                setVerificationDetails('Session expired. Please log in again.');
                navigate('/login');
                return;
            }

            if (response.ok && data.success) {
                const similarity = (data.similarity_score * 100).toFixed(1);
                const threshold = (data.threshold * 100).toFixed(1);
                
                if (data.verified) {
                    setVerificationDetails(`✅ MATCH: ${similarity}% similarity (threshold: ${threshold}%)`);
                    setResultStatus('success');
                    // Update order status in backend
                    await updateOrderStatus('delivered');
                } else {
                    setVerificationDetails(`❌ NO MATCH: ${similarity}% similarity (threshold: ${threshold}%)\n${data.message}`);
                    setResultStatus('failed');
                }
            } else if (response.status === 404) {
                setVerificationDetails(`❌ Customer #${customerId} has not enrolled their face yet.\nPlease ask customer to enroll first.`);
                setResultStatus('failed');
            } else {
                const errorMsg = data.detail?.error || data.detail || data.message || 'Verification failed';
                setVerificationDetails(`❌ ${errorMsg}`);
                setResultStatus('failed');
            }

            setStep('result');
        } catch (error) {
            console.error('Verification error:', error);
            setVerificationDetails('❌ Connection error. Is backend running?\nCheck: http://127.0.0.1:8000');
            setResultStatus('failed');
            setStep('result');
        } finally {
            setVerifying(false);
        }
    };

    const handleLockerRedirect = async () => {
        setResultStatus('locker');
        await updateOrderStatus('failed');
    };

    return (
        <div className="flex flex-col h-full bg-gray-50">
            <header className="bg-white p-4 shadow-sm flex items-center gap-3">
                <button onClick={() => navigate(-1)} className="text-gray-600">
                    <ArrowLeft size={24} />
                </button>
                <div>
                    <h1 className="text-lg font-bold text-gray-800">Delivery #{order.orderNumber}</h1>
                    <p className="text-xs text-gray-500">Customer #{order.customerId} • {order.city}</p>
                </div>
            </header>

            <div className="flex-1 p-4 overflow-y-auto">
                {step === 'info' && (
                    <div className="flex flex-col gap-6">
                        <div className="bg-white p-4 rounded-2xl shadow-sm">
                            <h2 className="font-semibold mb-2">Delivery Information</h2>
                            <div className="text-sm text-gray-600 mb-4">
                                <p><strong>Address:</strong> {order.address}</p>
                                <p><strong>City:</strong> {order.city}</p>
                                <p><strong>Status:</strong> {order.status.toUpperCase()}</p>
                                <p><strong>Amount:</strong> Rs. {order.totalAmount.toFixed(2)}</p>
                            </div>

                            <h3 className="font-semibold mb-2">Verification</h3>
                            <p className="text-sm text-gray-600 mb-4">
                                {order.verificationRequired
                                    ? "⚠️ Face verification required for this delivery"
                                    : "✅ No verification required"}
                            </p>

                            <div className="flex flex-col gap-3">
                                <button
                                    onClick={() => navigate(`/call?orderId=${order.orderId}`)}
                                    className="w-full py-3 bg-green-600 text-white rounded-xl font-bold shadow-lg flex items-center justify-center gap-2"
                                >
                                    <span className="text-xl">📞</span> Call & Verify Voice
                                </button>
                                {order.voiceEnrolled ? (
                                    <p className="text-xs text-center text-green-600 font-medium">Voice Profile Available</p>
                                ) : (
                                    <p className="text-xs text-center text-orange-500 font-medium">No Voice Profile Enrolled</p>
                                )}

                                <button
                                    onClick={() => setStep('scan')}
                                    disabled={!order.verificationRequired}
                                    className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Verify Identity (Face)
                                </button>
                                {!order.verificationRequired && (
                                    <p className="text-xs text-center text-green-600 font-medium">No face verification required</p>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {step === 'scan' && (
                    <div className="flex flex-col gap-4">
                        {/* Customer's Reference Image Section */}
                        <div className="bg-white p-4 rounded-2xl shadow-sm">
                            <h2 className="font-semibold mb-3 flex items-center gap-2">
                                <User size={20} className="text-blue-600" />
                                Customer's Reference Photo
                            </h2>
                            
                            {loadingReference ? (
                                <div className="h-40 flex items-center justify-center bg-gray-100 rounded-xl">
                                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                                </div>
                            ) : referenceImage ? (
                                <div className="relative">
                                    <img 
                                        src={referenceImage} 
                                        alt="Customer Reference" 
                                        className="w-full h-40 object-contain bg-gray-900 rounded-xl"
                                    />
                                    <div className="absolute top-2 left-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-full flex items-center gap-1">
                                        <ImageIcon size={12} />
                                        Reference
                                    </div>
                                </div>
                            ) : (
                                <div className="h-40 flex flex-col items-center justify-center bg-orange-50 rounded-xl border-2 border-dashed border-orange-200">
                                    <AlertTriangle size={32} className="text-orange-500 mb-2" />
                                    <p className="text-sm text-orange-700 font-medium">
                                        {referenceError || 'No reference image'}
                                    </p>
                                    <p className="text-xs text-orange-600 mt-1">
                                        Customer needs to enroll first
                                    </p>
                                </div>
                            )}
                        </div>
                        
                        {/* Live Capture Section */}
                        <div className="bg-white p-4 rounded-2xl shadow-sm">
                            <h2 className="font-semibold mb-2 flex items-center gap-2">
                                <Camera size={20} className="text-green-600" />
                                Capture Live Photo
                            </h2>
                            <p className="text-sm text-gray-600 mb-3">
                                Take a LIVE photo of the person receiving the delivery
                            </p>
                            
                            <div className="p-3 bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl mb-4 border border-blue-100">
                                <div className="flex items-center gap-2 text-blue-700 mb-1">
                                    <Shield size={16} />
                                    <span className="text-sm font-medium">3-Model AI Verification</span>
                                </div>
                                <p className="text-xs text-blue-600">
                                    ArcFace + Facenet512 + VGG-Face • 75% threshold
                                </p>
                            </div>
                            
                            <FaceScanner isScanning={true} onScanComplete={handleScanComplete} />
                            
                            {verifying && (
                                <div className="mt-4 flex items-center justify-center gap-2 text-blue-600 py-2 bg-blue-50 rounded-xl">
                                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                                    <span className="text-sm">{verificationDetails}</span>
                                </div>
                            )}
                        </div>
                        
                        <button
                            onClick={() => setStep('info')}
                            className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium"
                        >
                            ← Back to Order Info
                        </button>
                    </div>
                )}

                {step === 'result' && (
                    <div className="flex flex-col gap-4">
                        {/* Side by side comparison - Always show */}
                        <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
                            <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 border-b border-blue-100">
                                <h3 className="font-bold text-center text-gray-800 text-lg">
                                    🔍 Verification Comparison
                                </h3>
                            </div>
                            
                            <div className="p-4">
                                <div className="grid grid-cols-2 gap-4">
                                    {/* Reference Image */}
                                    <div className="flex flex-col">
                                        <div className="bg-blue-100 text-blue-700 text-xs font-semibold px-3 py-1.5 rounded-t-xl text-center">
                                            📋 Customer's Enrolled Photo
                                        </div>
                                        <div className="bg-gray-900 rounded-b-xl overflow-hidden border-2 border-blue-200">
                                            {referenceImage ? (
                                                <img 
                                                    src={referenceImage} 
                                                    alt="Reference" 
                                                    className="w-full h-44 object-contain"
                                                />
                                            ) : (
                                                <div className="w-full h-44 flex flex-col items-center justify-center bg-gray-100">
                                                    <User className="text-gray-400 mb-2" size={40} />
                                                    <p className="text-xs text-gray-500">No image</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                    
                                    {/* Captured Image */}
                                    <div className="flex flex-col">
                                        <div className="bg-green-100 text-green-700 text-xs font-semibold px-3 py-1.5 rounded-t-xl text-center">
                                            📸 Live Captured Photo
                                        </div>
                                        <div className="bg-gray-900 rounded-b-xl overflow-hidden border-2 border-green-200">
                                            {capturedImage ? (
                                                <img 
                                                    src={capturedImage} 
                                                    alt="Captured" 
                                                    className="w-full h-44 object-contain"
                                                />
                                            ) : (
                                                <div className="w-full h-44 flex flex-col items-center justify-center bg-gray-100">
                                                    <Camera className="text-gray-400 mb-2" size={40} />
                                                    <p className="text-xs text-gray-500">No image</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                                
                                {/* Large Match/No Match indicator */}
                                <div className={`mt-4 p-4 rounded-xl flex items-center justify-center gap-3 ${
                                    resultStatus === 'success' 
                                        ? 'bg-green-100 border-2 border-green-300' 
                                        : 'bg-red-100 border-2 border-red-300'
                                }`}>
                                    {resultStatus === 'success' ? (
                                        <>
                                            <CheckCircle size={28} className="text-green-600" />
                                            <div>
                                                <p className="font-bold text-green-700 text-lg">IDENTITY VERIFIED</p>
                                                <p className="text-xs text-green-600">Face matches enrolled photo</p>
                                            </div>
                                        </>
                                    ) : (
                                        <>
                                            <XCircle size={28} className="text-red-600" />
                                            <div>
                                                <p className="font-bold text-red-700 text-lg">NO MATCH FOUND</p>
                                                <p className="text-xs text-red-600">Face does not match enrolled photo</p>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        </div>
                        
                        {/* Verification Details */}
                        {verificationDetails && (
                            <div className="bg-white rounded-2xl shadow-sm p-4">
                                <h4 className="font-semibold text-gray-700 mb-2 flex items-center gap-2">
                                    <Shield size={18} className="text-blue-600" />
                                    AI Analysis Details
                                </h4>
                                <div className="p-3 bg-gray-50 rounded-xl text-sm font-mono text-gray-700 whitespace-pre-line border border-gray-200">
                                    {verificationDetails}
                                </div>
                            </div>
                        )}

                        {/* Action Buttons */}
                        <div className="bg-white rounded-2xl shadow-sm p-4">
                            {resultStatus === 'success' ? (
                                <div className="space-y-3">
                                    <button
                                        onClick={() => navigate('/courier')}
                                        className="w-full py-4 bg-green-600 text-white rounded-xl font-bold text-lg shadow-lg hover:bg-green-700"
                                    >
                                        ✅ Complete Delivery
                                    </button>
                                    <button
                                        onClick={() => { 
                                            setStep('info'); 
                                            setVerificationDetails(''); 
                                            setCapturedImage(null);
                                        }}
                                        className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium"
                                    >
                                        Back to Order
                                    </button>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    <button
                                        onClick={() => { 
                                            setStep('scan'); 
                                            setVerificationDetails(''); 
                                            setCapturedImage(null);
                                        }}
                                        className="w-full py-4 bg-blue-600 text-white rounded-xl font-bold shadow-lg hover:bg-blue-700"
                                    >
                                        🔄 Try Again
                                    </button>
                                    <button
                                        onClick={handleLockerRedirect}
                                        className="w-full py-4 bg-orange-600 text-white rounded-xl font-bold shadow-lg hover:bg-orange-700"
                                    >
                                        📦 Deposit in Smart Locker
                                    </button>
                                    <button
                                        onClick={() => { 
                                            setStep('info'); 
                                            setVerificationDetails(''); 
                                            setCapturedImage(null);
                                        }}
                                        className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium"
                                    >
                                        Back to Order
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}


            </div>
        </div>
    );
};

export default DeliveryDetail;
