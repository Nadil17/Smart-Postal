import { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, CheckCircle, Package } from 'lucide-react';
import FaceScanner from '../../components/FaceScanner';
import VerificationResult from '../../components/VerificationResult';
import { useDatabase } from '../../context/MockDatabaseContext';

const DeliveryDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { orders, updateOrder } = useDatabase();
    const order = orders.find(o => o.id === id);

    const [step, setStep] = useState<'info' | 'scan' | 'result'>('info');
    const [resultStatus, setResultStatus] = useState<'success' | 'failed' | 'locker'>('success');
    const [isVerified, setIsVerified] = useState(false);
    const [verificationMethod, setVerificationMethod] = useState<'face' | 'voice' | null>(null);

    // Check if returning from voice verification
    useEffect(() => {
        const voiceVerified = searchParams.get('voiceVerified');
        if (voiceVerified === 'true') {
            setIsVerified(true);
            setVerificationMethod('voice');
        }
    }, [searchParams]);

    if (!order) return <div>Order not found</div>;

    const handleScanComplete = () => {
        // Face scan successful - verification passed
        setResultStatus('success');
        setStep('result');
        setIsVerified(true);
        setVerificationMethod('face');
    };

    const handleCompleteDelivery = () => {
        updateOrder(order.id, { status: 'delivered' });
        navigate('/courier/dashboard');
    };

    const handleLockerRedirect = () => {
        updateOrder(order.id, { status: 'locker' });
        navigate('/courier/dashboard');
    };

    return (
        <div className="flex flex-col h-full bg-gray-50">
            <header className="bg-white p-4 shadow-sm flex items-center gap-3">
                <button onClick={() => navigate(-1)} className="text-gray-600">
                    <ArrowLeft size={24} />
                </button>
                <div>
                    <h1 className="text-lg font-bold text-gray-800">Delivery #{id}</h1>
                    <p className="text-xs text-gray-500">{order.recipientName}</p>
                </div>
            </header>

            <div className="flex-1 p-4 overflow-y-auto">
                {step === 'info' && (
                    <div className="flex flex-col gap-6">
                        <div className="bg-white p-4 rounded-2xl shadow-sm">
                            <h2 className="font-semibold mb-2">Delivery Instructions</h2>
                            <p className="text-sm text-gray-600 mb-4">
                                Recipient is not at home.
                                {order.neighborNicImage
                                    ? ` Authorized neighbor: ${order.neighborName || 'Yes'}`
                                    : " No authorized neighbor found."}
                            </p>

                            {order.neighborNicImage ? (
                                <div className="mb-4">
                                    <p className="text-xs font-medium text-gray-500 mb-2">Authorized NIC:</p>
                                    <img
                                        src={order.neighborNicImage}
                                        alt="Neighbor NIC"
                                        className="w-full h-32 object-cover rounded-lg border border-gray-200"
                                    />
                                </div>
                            ) : (
                                <div className="bg-orange-50 p-3 rounded-lg flex gap-2 text-orange-700 text-sm mb-4">
                                    <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                                    <p>No neighbor authorized. Proceed to Smart Locker or contact admin.</p>
                                </div>
                            )}

                            <div className="flex flex-col gap-3">
                                <button
                                    onClick={() => navigate(`/call?orderId=${order.id}`)}
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
                                    disabled={!order.neighborNicImage}
                                    className="w-full py-3 bg-blue-600 text-white rounded-xl font-bold shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    Verify Identity (Face)
                                </button>

                                {/* Show Complete button if verified via voice */}
                                {isVerified && verificationMethod === 'voice' && (
                                    <div className="mt-4 p-4 bg-green-50 rounded-xl border border-green-200">
                                        <div className="flex items-center gap-2 text-green-700 mb-3">
                                            <CheckCircle size={20} />
                                            <span className="font-medium">Voice Verified Successfully</span>
                                        </div>
                                        <button
                                            onClick={handleCompleteDelivery}
                                            className="w-full py-3 px-4 rounded-xl bg-green-600 text-white font-bold hover:bg-green-700 flex items-center justify-center gap-2"
                                        >
                                            ✓ Complete Delivery
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Deposit to Locker Section */}
                        <div className="bg-white p-4 rounded-2xl shadow-sm">
                            <h2 className="font-semibold mb-2">Alternative Option</h2>
                            <p className="text-sm text-gray-600 mb-4">
                                If recipient is unavailable or verification is not possible, deposit the package in a Smart Locker.
                            </p>
                            <button
                                onClick={handleLockerRedirect}
                                className="w-full py-3 bg-orange-600 text-white rounded-xl font-bold shadow-lg flex items-center justify-center gap-2 hover:bg-orange-700"
                            >
                                <Package size={20} />
                                Deposit in Smart Locker
                            </button>
                        </div>
                    </div>
                )}

                {step === 'scan' && (
                    <div className="flex flex-col gap-6">
                        <div className="bg-white p-4 rounded-2xl shadow-sm">
                            <h2 className="font-semibold mb-2">Verify Recipient</h2>
                            <p className="text-sm text-gray-600 mb-4">Scanning face to match against authorized NIC.</p>
                            <FaceScanner isScanning={true} onScanComplete={handleScanComplete} />
                        </div>
                        {order.neighborNicImage && (
                            <div className="bg-white p-3 rounded-xl shadow-sm flex items-center gap-3 opacity-70">
                                <img src={order.neighborNicImage} alt="NIC" className="w-12 h-8 object-cover rounded" />
                                <span className="text-sm text-gray-500">Matching against stored NIC...</span>
                            </div>
                        )}
                    </div>
                )}

                {step === 'result' && (
                    <div className="bg-white rounded-2xl shadow-sm">
                        <VerificationResult
                            status={resultStatus}
                            onReset={() => {
                                setStep('info');
                                setIsVerified(false);
                            }}
                        />
                        {resultStatus === 'success' && (
                            <div className="p-4 pt-0">
                                <button
                                    onClick={handleCompleteDelivery}
                                    className="w-full py-3 px-4 rounded-xl bg-green-600 text-white font-bold hover:bg-green-700 flex items-center justify-center gap-2"
                                >
                                    ✓ Complete Delivery
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default DeliveryDetail;
