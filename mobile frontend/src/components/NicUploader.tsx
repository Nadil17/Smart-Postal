import { Upload, Camera, Check, RotateCcw } from 'lucide-react';
import { useRef, useState, useCallback } from 'react';

interface NicUploaderProps {
    onImageSelected: (imageUrl: string, file?: File) => void;
    title?: string;
    subtitle?: string;
    showCamera?: boolean;
    confirmBeforeUpload?: boolean;
    onConfirm?: () => void;
}

const NicUploader = ({ 
    onImageSelected, 
    title = "Upload Your Photo",
    subtitle = "Take a clear photo of your face",
    showCamera = true,
    confirmBeforeUpload = false,
    onConfirm
}: NicUploaderProps) => {
    const fileInputRef = useRef<HTMLInputElement>(null);
    const cameraInputRef = useRef<HTMLInputElement>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isConfirmed, setIsConfirmed] = useState(false);

    const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const url = URL.createObjectURL(file);
            setPreview(url);
            setSelectedFile(file);
            setIsConfirmed(false);
            
            // If not requiring confirmation, call immediately
            if (!confirmBeforeUpload) {
                onImageSelected(url, file);
            }
        }
    }, [confirmBeforeUpload, onImageSelected]);

    const handleConfirm = useCallback(() => {
        if (preview && selectedFile) {
            setIsConfirmed(true);
            onImageSelected(preview, selectedFile);
            onConfirm?.();
        }
    }, [preview, selectedFile, onImageSelected, onConfirm]);

    const handleReset = useCallback(() => {
        if (preview) {
            URL.revokeObjectURL(preview);
        }
        setPreview(null);
        setSelectedFile(null);
        setIsConfirmed(false);
        // Reset file inputs
        if (fileInputRef.current) fileInputRef.current.value = '';
        if (cameraInputRef.current) cameraInputRef.current.value = '';
    }, [preview]);

    return (
        <div className="w-full">
            {/* Preview with image selected */}
            {preview ? (
                <div className="relative">
                    {/* Image Preview */}
                    <div className="border-2 border-blue-300 rounded-xl overflow-hidden bg-gray-900">
                        <img 
                            src={preview} 
                            alt="Preview" 
                            className="w-full h-56 object-contain"
                        />
                    </div>
                    
                    {/* Status Badge */}
                    <div className={`absolute top-2 left-2 px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 ${
                        isConfirmed 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-yellow-100 text-yellow-700'
                    }`}>
                        {isConfirmed ? (
                            <>
                                <Check size={14} />
                                Ready to Upload
                            </>
                        ) : (
                            <>
                                <Camera size={14} />
                                Review Your Photo
                            </>
                        )}
                    </div>

                    {/* Action Buttons */}
                    {confirmBeforeUpload && !isConfirmed && (
                        <div className="mt-4 flex gap-3">
                            <button
                                onClick={handleReset}
                                className="flex-1 py-3 px-4 bg-gray-100 text-gray-700 rounded-xl font-medium flex items-center justify-center gap-2 hover:bg-gray-200 transition-colors"
                            >
                                <RotateCcw size={18} />
                                Retake
                            </button>
                            <button
                                onClick={handleConfirm}
                                className="flex-1 py-3 px-4 bg-green-600 text-white rounded-xl font-medium flex items-center justify-center gap-2 hover:bg-green-700 transition-colors"
                            >
                                <Check size={18} />
                                Confirm Photo
                            </button>
                        </div>
                    )}

                    {/* Reset button for already confirmed or non-confirm mode */}
                    {(!confirmBeforeUpload || isConfirmed) && (
                        <button
                            onClick={handleReset}
                            className="mt-3 w-full py-2 px-4 bg-gray-100 text-gray-600 rounded-xl text-sm flex items-center justify-center gap-2 hover:bg-gray-200"
                        >
                            <RotateCcw size={16} />
                            Change Photo
                        </button>
                    )}
                </div>
            ) : (
                /* Upload Options */
                <div className="space-y-3">
                    {/* Camera Option */}
                    {showCamera && (
                        <div
                            onClick={() => cameraInputRef.current?.click()}
                            className="border-2 border-dashed border-green-300 rounded-xl p-5 flex items-center gap-4 bg-green-50 hover:bg-green-100 cursor-pointer transition-colors"
                        >
                            <div className="bg-green-100 p-3 rounded-full text-green-600 flex-shrink-0">
                                <Camera size={28} />
                            </div>
                            <div>
                                <p className="font-medium text-gray-800">Take a Photo</p>
                                <p className="text-xs text-gray-500">Use your camera for a live capture</p>
                            </div>
                            <input
                                type="file"
                                ref={cameraInputRef}
                                onChange={handleFileChange}
                                accept="image/*"
                                capture="user"
                                className="hidden"
                            />
                        </div>
                    )}

                    {/* Upload from Gallery */}
                    <div
                        onClick={() => fileInputRef.current?.click()}
                        className="border-2 border-dashed border-blue-300 rounded-xl p-5 flex items-center gap-4 bg-blue-50 hover:bg-blue-100 cursor-pointer transition-colors"
                    >
                        <div className="bg-blue-100 p-3 rounded-full text-blue-600 flex-shrink-0">
                            <Upload size={28} />
                        </div>
                        <div>
                            <p className="font-medium text-gray-800">{title}</p>
                            <p className="text-xs text-gray-500">{subtitle}</p>
                        </div>
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={handleFileChange}
                            accept="image/*"
                            className="hidden"
                        />
                    </div>
                </div>
            )}
        </div>
    );
};

export default NicUploader;
