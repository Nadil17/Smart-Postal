import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ShoppingBag, MapPin, CreditCard, ShieldCheck, Truck, X, Mic, CheckCircle } from 'lucide-react';
import { useDatabase } from '../../context/MockDatabaseContext';
import clsx from 'clsx';
import { enrollVoiceSample, loginUser, registerUser, type ApiError, type VoiceEnrollmentResponse } from '../../lib/api';
import { convertBlobToWav } from '../../lib/audio/wav';

const Checkout = () => {
    const navigate = useNavigate();
    const { updateOrder } = useDatabase();
    const [showVoiceModal, setShowVoiceModal] = useState(false);
    const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
    const [email, setEmail] = useState('');
    const [fullName, setFullName] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [authToken, setAuthToken] = useState<string | null>(null);
    const [authBusy, setAuthBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [enrollStatus, setEnrollStatus] = useState<VoiceEnrollmentResponse | null>(null);
    const [uploadBusy, setUploadBusy] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [recordingProgress, setRecordingProgress] = useState(0);
    const [enrollMode, setEnrollMode] = useState<'live' | 'upload'>('live');
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [uploadLabel, setUploadLabel] = useState<string | null>(null);

    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    const chunksRef = useRef<BlobPart[]>([]);
    const recordTimerRef = useRef<number | null>(null);
    const [orderPlaced, setOrderPlaced] = useState(false);

    const samplesRequired = enrollStatus?.samples_required ?? 3;
    const samplesRecorded = enrollStatus?.samples_recorded ?? 0;

    const stepItems = useMemo(() => {
        const n = Math.max(1, Math.min(samplesRequired, 6));
        return Array.from({ length: n }, (_, i) => i + 1);
    }, [samplesRequired]);

    useEffect(() => {
        // Require credential validation each time before enrollment.
        if (!showVoiceModal) return;
        setAuthToken(null);
        setError(null);
        setEnrollStatus(null);
        setEnrollMode('live');
        setSelectedFiles([]);
        setUploadLabel(null);
    }, [showVoiceModal]);

    useEffect(() => {
        return () => {
            if (recordTimerRef.current) {
                window.clearInterval(recordTimerRef.current);
                recordTimerRef.current = null;
            }
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop();
            }
            if (mediaStreamRef.current) {
                mediaStreamRef.current.getTracks().forEach(t => t.stop());
                mediaStreamRef.current = null;
            }
        };
    }, []);

    const resetModalState = () => {
        setError(null);
        setAuthBusy(false);
        setUploadBusy(false);
        setIsRecording(false);
        setRecordingProgress(0);
        setEnrollStatus(null);
        setEnrollMode('live');
        setSelectedFiles([]);
        setUploadLabel(null);
        setAuthToken(null);

        if (recordTimerRef.current) {
            window.clearInterval(recordTimerRef.current);
            recordTimerRef.current = null;
        }
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop();
        }
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(t => t.stop());
            mediaStreamRef.current = null;
        }
    };

    const closeVoiceModal = () => {
        setShowVoiceModal(false);
        resetModalState();
    };

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setAuthBusy(true);
        try {
            const res = await loginUser({ email, password });
            setAuthToken(res.access_token);
        } catch (err) {
            const apiErr = err as ApiError;
            setError(apiErr.message || 'Login failed');
        } finally {
            setAuthBusy(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        const cleanedPhone = phone.replace(/\s|-/g, '');
        if (!cleanedPhone || cleanedPhone.length < 10) {
            setError('Phone must be at least 10 digits');
            return;
        }
        if (!/^\d+$/.test(cleanedPhone)) {
            setError('Phone must contain only digits');
            return;
        }
        if (password.length < 8 || !/[A-Z]/.test(password) || !/\d/.test(password)) {
            setError('Password must be 8+ chars, include 1 uppercase letter and 1 digit');
            return;
        }

        setAuthBusy(true);
        try {
            await registerUser({ email, phone: cleanedPhone, full_name: fullName, password, role: 'customer' });
            const res = await loginUser({ email, password });
            setAuthToken(res.access_token);
        } catch (err) {
            const apiErr = err as ApiError;
            setError(apiErr.message || 'Registration failed');
        } finally {
            setAuthBusy(false);
        }
    };

    const getSupportedMimeType = () => {
        const candidates = [
            'audio/webm;codecs=opus',
            'audio/webm',
            'audio/ogg;codecs=opus',
            'audio/ogg',
        ];
        for (const type of candidates) {
            if (window.MediaRecorder && MediaRecorder.isTypeSupported(type)) return type;
        }
        return '';
    };

    const completeEnrollment = () => {
        updateOrder('ORD-001', { voiceEnrolled: true });
        setShowVoiceModal(false);
        setOrderPlaced(true);
        resetModalState();
    };

    const uploadAudioBlobAsEnrollmentSample = async (blob: Blob, filenamePrefix: string) => {
        if (!authToken) throw new Error('Missing auth token');
        const wavBlob = await convertBlobToWav(blob, 16000);
        const wavFile = new File([wavBlob], `${filenamePrefix}_${Date.now()}.wav`, { type: 'audio/wav' });
        const res = await enrollVoiceSample(authToken, wavFile);
        setEnrollStatus(res);
        if (res.enrollment_complete) {
            completeEnrollment();
        }
        return res;
    };

    const handleManualFiles = (files: FileList | null) => {
        setError(null);
        if (!files || files.length === 0) {
            setSelectedFiles([]);
            return;
        }
        setSelectedFiles(Array.from(files));
    };

    const uploadSelectedSamples = async () => {
        if (!authToken) {
            setError('Please log in first');
            return;
        }
        if (!selectedFiles.length) {
            setError('Please choose one or more audio files');
            return;
        }

        setError(null);
        setUploadBusy(true);
        setUploadLabel(null);

        try {
            for (let i = 0; i < selectedFiles.length; i++) {
                const file = selectedFiles[i];
                setUploadLabel(`Uploading ${i + 1} of ${selectedFiles.length}…`);
                const res = await uploadAudioBlobAsEnrollmentSample(file, 'voice_upload');
                if (res.enrollment_complete) return;
            }
            setUploadLabel('Upload complete. Add more samples if needed.');
        } catch (err) {
            const apiErr = err as ApiError;
            setError(apiErr.message || 'Upload failed');
        } finally {
            setUploadBusy(false);
        }
    };

    const recordAndEnrollOnce = async () => {
        if (!authToken) {
            setError('Please log in first');
            return;
        }
        setError(null);
        setUploadBusy(false);
        setIsRecording(true);
        setRecordingProgress(0);

        try {
            if (!mediaStreamRef.current) {
                mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true });
            }

            chunksRef.current = [];
            const mimeType = getSupportedMimeType();
            const recorder = new MediaRecorder(mediaStreamRef.current, mimeType ? { mimeType } : undefined);
            mediaRecorderRef.current = recorder;

            recorder.ondataavailable = (ev) => {
                if (ev.data && ev.data.size > 0) chunksRef.current.push(ev.data);
            };

            const stopPromise = new Promise<Blob>((resolve, reject) => {
                recorder.onstop = () => {
                    try {
                        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || 'audio/webm' });
                        resolve(blob);
                    } catch (e) {
                        reject(e);
                    }
                };
                recorder.onerror = () => reject(new Error('Recording failed'));
            });

            recorder.start();

            // 3-second capture to match the prototype UX
            const durationMs = 3000;
            const startedAt = Date.now();
            recordTimerRef.current = window.setInterval(() => {
                const elapsed = Date.now() - startedAt;
                const pct = Math.min(100, Math.round((elapsed / durationMs) * 100));
                setRecordingProgress(pct);
                if (pct >= 100 && recordTimerRef.current) {
                    window.clearInterval(recordTimerRef.current);
                    recordTimerRef.current = null;
                }
            }, 100);

            window.setTimeout(() => {
                if (recorder.state !== 'inactive') recorder.stop();
            }, durationMs);

            const rawBlob = await stopPromise;
            setIsRecording(false);
            setUploadBusy(true);
            await uploadAudioBlobAsEnrollmentSample(rawBlob, 'voice');
        } catch (err) {
            const apiErr = err as ApiError;
            // Backend sometimes returns a structured JSON detail object
            if (apiErr?.detail && typeof apiErr.detail === 'object') {
                const detail = apiErr.detail as any;
                if (detail?.detail?.message) {
                    setError(String(detail.detail.message));
                } else if (detail?.detail?.error) {
                    setError(String(detail.detail.error));
                } else if (detail?.detail) {
                    setError(typeof detail.detail === 'string' ? detail.detail : JSON.stringify(detail.detail));
                } else {
                    setError(apiErr.message || 'Voice enrollment failed');
                }
            } else {
                setError(apiErr.message || 'Voice enrollment failed');
            }
        } finally {
            setUploadBusy(false);
            setIsRecording(false);
        }
    };

    if (orderPlaced) {
        return (
            <div className="flex flex-col h-full bg-gray-50">
                <header className="bg-white p-4 shadow-sm flex items-center gap-3 border-b">
                    <button onClick={() => navigate(-1)} className="text-gray-600">
                        <ArrowLeft size={24} />
                    </button>
                    <h1 className="text-lg font-bold text-gray-800">Order Confirmation</h1>
                </header>

                <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
                    <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center text-green-600 mb-6 animate-bounce">
                        <CheckCircle size={48} />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-800 mb-2">Order Placed Successfully!</h2>
                    <p className="text-gray-600 mb-2">Order #ORD-001</p>
                    <p className="text-sm text-gray-500 mb-8 max-w-md">
                        Your voice has been securely enrolled. The courier will verify your identity via voice call before delivery.
                    </p>
                    <button
                        onClick={() => navigate('/client/dashboard')}
                        className="px-8 py-3 bg-blue-600 text-white rounded-lg font-bold shadow-lg hover:bg-blue-700 transition-colors"
                    >
                        View My Orders
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-gray-50">
            <header className="bg-white p-4 shadow-sm flex items-center gap-3 border-b">
                <button onClick={() => navigate(-1)} className="text-gray-600">
                    <ArrowLeft size={24} />
                </button>
                <h1 className="text-lg font-bold text-gray-800">Checkout</h1>
            </header>

            <div className="flex-1 overflow-y-auto p-4 pb-24">
                {/* Shipping Address */}
                <div className="bg-white rounded-lg shadow-sm mb-4 p-4 border">
                    <div className="flex items-center justify-between mb-3">
                        <h2 className="font-bold text-gray-800 flex items-center gap-2">
                            <MapPin size={18} className="text-blue-600" />
                            Shipping Address
                        </h2>
                        <button className="text-blue-600 text-sm font-medium">Change</button>
                    </div>
                    <div className="text-sm text-gray-700">
                        <p className="font-medium">John Doe</p>
                        <p>123, Galle Road</p>
                        <p>Colombo 03, Sri Lanka</p>
                        <p className="mt-1">+94 77 123 4567</p>
                    </div>
                </div>

                {/* Items */}
                <div className="bg-white rounded-lg shadow-sm mb-4 p-4 border">
                    <h2 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                        <ShoppingBag size={18} className="text-blue-600" />
                        Items (1)
                    </h2>
                    <div className="flex gap-3">
                        <div className="w-20 h-20 bg-gray-100 rounded-lg flex items-center justify-center">
                            <ShoppingBag size={32} className="text-gray-400" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-medium text-gray-800">Wireless Headphones</h3>
                            <p className="text-sm text-gray-500">Premium Noise Cancelling</p>
                            <p className="text-sm text-gray-600 mt-1">Qty: 1</p>
                        </div>
                        <div className="text-right">
                            <p className="font-bold text-gray-800">$120.00</p>
                        </div>
                    </div>
                </div>

                {/* Delivery */}
                <div className="bg-white rounded-lg shadow-sm mb-4 p-4 border">
                    <h2 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                        <Truck size={18} className="text-blue-600" />
                        Delivery Options
                    </h2>
                    <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div>
                            <p className="font-medium text-gray-800">Standard Delivery</p>
                            <p className="text-sm text-gray-600">Arrives in 2-3 business days</p>
                        </div>
                        <p className="font-bold text-gray-800">$5.00</p>
                    </div>
                </div>

                {/* Payment */}
                <div className="bg-white rounded-lg shadow-sm mb-4 p-4 border">
                    <h2 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
                        <CreditCard size={18} className="text-blue-600" />
                        Payment Method
                    </h2>
                    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border">
                        <CreditCard size={24} className="text-gray-600" />
                        <div>
                            <p className="font-medium text-gray-800">Visa ending in 4242</p>
                            <p className="text-sm text-gray-600">Expires 12/25</p>
                        </div>
                    </div>
                </div>

                {/* Voice Security */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm mb-4 p-4 border border-blue-200">
                    <h2 className="font-bold text-gray-800 mb-2 flex items-center gap-2">
                        <ShieldCheck size={18} className="text-blue-600" />
                        Voice Security Enrollment
                    </h2>
                    <p className="text-sm text-gray-700 mb-3">
                        Protect your delivery with voice verification. The courier will verify your identity before handing over the package.
                    </p>
                    <div className="flex items-center gap-2 text-xs text-blue-700 bg-blue-100 p-2 rounded">
                        <ShieldCheck size={14} />
                        <span>Required for secure delivery</span>
                    </div>
                </div>
            </div>

            {/* Bottom Summary */}
            <div className="fixed bottom-0 left-0 right-0 bg-white border-t shadow-lg p-4">
                <div className="space-y-2 mb-3">
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Subtotal</span>
                        <span className="font-medium">$120.00</span>
                    </div>
                    <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Shipping</span>
                        <span className="font-medium">$5.00</span>
                    </div>
                    <div className="flex justify-between text-lg font-bold border-t pt-2">
                        <span>Total</span>
                        <span className="text-blue-600">$125.00</span>
                    </div>
                </div>
                <button
                    onClick={() => setShowVoiceModal(true)}
                    className="w-full py-3 bg-blue-600 text-white rounded-lg font-bold shadow-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
                >
                    <ShieldCheck size={20} />
                    Complete Order with Voice Security
                </button>
            </div>

            {/* Voice Enrollment Modal */}
            {showVoiceModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 relative">
                        <button
                            onClick={closeVoiceModal}
                            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
                        >
                            <X size={24} />
                        </button>

                        <div className="text-center mb-6">
                            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Mic size={32} className="text-blue-600" />
                            </div>
                            <h2 className="text-2xl font-bold text-gray-800 mb-2">Voice Enrollment</h2>
                            <p className="text-sm text-gray-600">
                                Say your name 3 times to complete enrollment
                            </p>
                        </div>

                        {/* Auth / Enrollment */}
                        {!authToken ? (
                            <div className="mb-2">
                                <div className="flex gap-2 mb-4">
                                    <button
                                        type="button"
                                        onClick={() => { setAuthMode('login'); setError(null); }}
                                        className={clsx(
                                            'flex-1 py-2 rounded-lg font-bold border',
                                            authMode === 'login' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200'
                                        )}
                                    >
                                        Log in
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => { setAuthMode('register'); setError(null); }}
                                        className={clsx(
                                            'flex-1 py-2 rounded-lg font-bold border',
                                            authMode === 'register' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200'
                                        )}
                                    >
                                        Register
                                    </button>
                                </div>

                                <form onSubmit={authMode === 'login' ? handleLogin : handleRegister} className="space-y-3">
                                    {authMode === 'register' && (
                                        <>
                                            <input
                                                value={fullName}
                                                onChange={(e) => setFullName(e.target.value)}
                                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                placeholder="Full name"
                                                required
                                            />
                                            <input
                                                value={phone}
                                                onChange={(e) => setPhone(e.target.value)}
                                                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                placeholder="Phone (digits only)"
                                                required
                                            />
                                            <p className="text-xs text-gray-500">
                                                Password must be 8+ chars, include 1 uppercase letter and 1 digit.
                                            </p>
                                        </>
                                    )}

                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="Email"
                                        required
                                    />
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                        placeholder="Password"
                                        required
                                    />

                                    {error && (
                                        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                            {error}
                                        </div>
                                    )}

                                    <button
                                        type="submit"
                                        disabled={authBusy}
                                        className={clsx(
                                            'w-full py-3 rounded-lg font-bold shadow-lg transition-colors',
                                            authBusy ? 'bg-gray-300 text-gray-600' : 'bg-blue-600 text-white hover:bg-blue-700'
                                        )}
                                    >
                                        {authMode === 'login' ? (authBusy ? 'Signing in…' : 'Sign in') : (authBusy ? 'Creating account…' : 'Create account')}
                                    </button>
                                </form>
                            </div>
                        ) : (
                            <>
                                <div className="flex gap-2 mb-4">
                                    <button
                                        type="button"
                                        onClick={() => { setEnrollMode('live'); setError(null); setUploadLabel(null); }}
                                        className={clsx(
                                            'flex-1 py-2 rounded-lg font-bold border',
                                            enrollMode === 'live' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200'
                                        )}
                                    >
                                        Live enrollment
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => { setEnrollMode('upload'); setError(null); setUploadLabel(null); }}
                                        className={clsx(
                                            'flex-1 py-2 rounded-lg font-bold border',
                                            enrollMode === 'upload' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-200'
                                        )}
                                    >
                                        Manual samples
                                    </button>
                                </div>

                                {/* Progress Indicators */}
                                <div className="flex justify-center gap-3 mb-6">
                                    {stepItems.map(step => (
                                <div
                                    key={step}
                                    className={clsx(
                                        "w-12 h-12 rounded-full flex items-center justify-center font-bold transition-all",
                                        step <= samplesRecorded
                                            ? "bg-green-500 text-white"
                                            : step === (samplesRecorded + 1)
                                                ? "bg-blue-600 text-white ring-4 ring-blue-200"
                                                : "bg-gray-200 text-gray-500"
                                    )}
                                >
                                    {step <= samplesRecorded ? <CheckCircle size={20} /> : step}
                                </div>
                                    ))}
                                </div>

                                {/* Instructions */}
                                <div className="bg-blue-50 rounded-lg p-4 mb-6 border border-blue-200">
                                    <p className="text-center font-medium text-gray-800 mb-2">
                                        Recording {Math.min(samplesRecorded + 1, samplesRequired)} of {samplesRequired}
                                    </p>
                                    {enrollMode === 'live' ? (
                                        <p className="text-center text-lg font-bold text-blue-600 italic">
                                            "My name is [Your Name]"
                                        </p>
                                    ) : (
                                        <p className="text-center text-sm text-gray-700">
                                            Upload existing voice recordings (audio files). We’ll convert them to WAV and enroll.
                                        </p>
                                    )}
                                    {enrollStatus?.message && (
                                        <p className="text-center text-xs text-gray-600 mt-2">{enrollStatus.message}</p>
                                    )}
                                </div>

                                {/* Live Record Button */}
                                <div className="flex flex-col items-center">
                                    {enrollMode === 'live' ? (
                                        <button
                                            onClick={recordAndEnrollOnce}
                                            disabled={isRecording || uploadBusy || (samplesRecorded >= samplesRequired)}
                                            className={clsx(
                                                "w-20 h-20 rounded-full flex items-center justify-center transition-all shadow-lg mb-4",
                                                (samplesRecorded >= samplesRequired)
                                                    ? "bg-green-500 text-white"
                                                    : isRecording
                                                        ? "bg-red-500 text-white animate-pulse"
                                                        : uploadBusy
                                                            ? "bg-gray-300 text-gray-600"
                                                            : "bg-blue-600 text-white hover:bg-blue-700 active:scale-95"
                                            )}
                                        >
                                            {(samplesRecorded >= samplesRequired) ? (
                                                <CheckCircle size={40} />
                                            ) : (
                                                <Mic size={40} />
                                            )}
                                        </button>
                                    ) : (
                                        <div className="w-full">
                                            <input
                                                type="file"
                                                accept="audio/*"
                                                multiple
                                                onChange={(e) => handleManualFiles(e.target.files)}
                                                className="block w-full text-sm text-gray-700 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-blue-600 file:text-white file:font-bold hover:file:bg-blue-700"
                                                disabled={uploadBusy}
                                            />
                                            <div className="mt-3 flex items-center justify-between">
                                                <p className="text-xs text-gray-600">
                                                    {selectedFiles.length ? `${selectedFiles.length} file(s) selected` : 'No files selected'}
                                                </p>
                                                <button
                                                    type="button"
                                                    onClick={uploadSelectedSamples}
                                                    disabled={uploadBusy || !selectedFiles.length || (samplesRecorded >= samplesRequired)}
                                                    className={clsx(
                                                        'px-4 py-2 rounded-lg font-bold',
                                                        uploadBusy || !selectedFiles.length || (samplesRecorded >= samplesRequired)
                                                            ? 'bg-gray-300 text-gray-600'
                                                            : 'bg-blue-600 text-white hover:bg-blue-700'
                                                    )}
                                                >
                                                    Upload
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {isRecording && (
                                        <div className="w-full">
                                            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-blue-600 transition-all duration-100"
                                                    style={{ width: `${recordingProgress}%` }}
                                                />
                                            </div>
                                            <p className="text-center text-sm text-gray-600 mt-2">
                                                Recording... {Math.round(recordingProgress)}%
                                            </p>
                                        </div>
                                    )}

                                    {!isRecording && !uploadBusy && (samplesRecorded < samplesRequired) && (
                                        <p className="text-sm text-gray-600">
                                            {enrollMode === 'live' ? 'Tap to record and upload' : 'Upload samples to enroll'}
                                        </p>
                                    )}

                                    {uploadBusy && (
                                        <p className="text-sm text-gray-600">{uploadLabel ?? 'Uploading sample…'}</p>
                                    )}

                                    {!uploadBusy && uploadLabel && (
                                        <p className="text-sm text-gray-600">{uploadLabel}</p>
                                    )}

                                    {error && (
                                        <div className="mt-3 w-full p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                                            {error}
                                        </div>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Checkout;
