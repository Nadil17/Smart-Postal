import { Camera, Upload } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface FaceScannerProps {
    onScanComplete: (imageData: File | null, imageUrl?: string) => void;
    isScanning: boolean;
}

const FaceScanner = ({ onScanComplete, isScanning }: FaceScannerProps) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [hasPermission, setHasPermission] = useState(false);
    const [useUpload, setUseUpload] = useState(false);
    const [uploadPreview, setUploadPreview] = useState<string | null>(null);

    useEffect(() => {
        if (isScanning && !useUpload) {
            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    facingMode: 'user',
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                } 
            })
                .then(stream => {
                    if (videoRef.current) {
                        videoRef.current.srcObject = stream;
                        setHasPermission(true);
                    }
                })
                .catch(err => {
                    console.warn("Camera access denied, switching to upload mode:", err.name);
                    setHasPermission(false);
                    setUseUpload(true); // Auto-fallback to upload
                });
        } else {
            // Stop stream
            if (videoRef.current?.srcObject) {
                const stream = videoRef.current.srcObject as MediaStream;
                stream.getTracks().forEach(track => track.stop());
            }
        }
        
        return () => {
            // Cleanup on unmount
            if (videoRef.current?.srcObject) {
                const stream = videoRef.current.srcObject as MediaStream;
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, [isScanning, useUpload]);

    const capturePhoto = () => {
        if (videoRef.current && canvasRef.current) {
            const video = videoRef.current;
            const canvas = canvasRef.current;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.drawImage(video, 0, 0);
                canvas.toBlob((blob) => {
                    if (blob) {
                        const file = new File([blob], 'face_capture.jpg', { type: 'image/jpeg' });
                        onScanComplete(file);
                    }
                }, 'image/jpeg', 0.95);
            }
        }
    };

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Validate file type
            if (!file.type.startsWith('image/')) {
                alert('Please select an image file');
                return;
            }
            
            // Validate file size (max 10MB)
            if (file.size > 10 * 1024 * 1024) {
                alert('Image size must be less than 10MB');
                return;
            }
            
            const url = URL.createObjectURL(file);
            setUploadPreview(url);
            onScanComplete(file, url);
        }
    };

    return (
        <div className="relative w-full aspect-[3/4] bg-black rounded-2xl overflow-hidden shadow-lg">
            {isScanning ? (
                <>
                    {useUpload || uploadPreview ? (
                        <div className="w-full h-full flex flex-col items-center justify-center p-4">
                            {uploadPreview ? (
                                <img src={uploadPreview} alt="Uploaded" className="w-full h-full object-cover" />
                            ) : (
                                <div className="w-full h-full flex flex-col items-center justify-center">
                                    <Upload size={48} className="text-gray-400 mb-4" />
                                    <p className="text-white text-sm mb-4">Upload Photo</p>
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        className="bg-white text-blue-600 px-6 py-2 rounded-full font-bold shadow-lg"
                                    >
                                        Choose File
                                    </button>
                                    <button
                                        onClick={() => setUseUpload(false)}
                                        className="mt-3 text-white text-sm underline"
                                    >
                                        Use Camera Instead
                                    </button>
                                </div>
                            )}
                        </div>
                    ) : (
                        <>
                            <video
                                ref={videoRef}
                                autoPlay
                                playsInline
                                muted
                                className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 border-4 border-blue-500/50 rounded-2xl pointer-events-none">
                                <div className="absolute top-1/4 left-1/4 right-1/4 bottom-1/4 border-2 border-white/80 rounded-full animate-pulse shadow-[0_0_100px_rgba(0,0,0,0.5)_inset]"></div>
                            </div>
                        </>
                    )}
                    <div className="absolute bottom-4 left-0 right-0 flex justify-center gap-3 px-4">
                        {!useUpload && !uploadPreview && (
                            <>
                                <button
                                    onClick={capturePhoto}
                                    className="bg-white text-blue-600 px-6 py-2 rounded-full font-bold shadow-lg active:scale-95 transition-transform flex items-center gap-2"
                                >
                                    <Camera size={20} />
                                    Capture
                                </button>
                                <button
                                    onClick={() => setUseUpload(true)}
                                    className="bg-gray-800 text-white px-4 py-2 rounded-full font-bold shadow-lg active:scale-95 transition-transform flex items-center gap-2"
                                >
                                    <Upload size={18} />
                                </button>
                            </>
                        )}
                    </div>
                    <canvas ref={canvasRef} className="hidden" />
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/*"
                        onChange={handleFileUpload}
                        className="hidden"
                    />
                </>
            ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-gray-400">
                    <Camera size={48} className="mb-2" />
                    <p>{hasPermission === false && isScanning ? "Camera access denied" : "Camera inactive"}</p>
                </div>
            )}
        </div>
    );
};

export default FaceScanner;
