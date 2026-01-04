import { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Upload, User, CheckCircle, Shield, CloudUpload } from 'lucide-react';
import NicUploader from '../../components/NicUploader';
import { useDatabase } from '../../context/MockDatabaseContext';

const AuthorizeNeighbor = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const { updateOrder } = useDatabase();
    const [mode, setMode] = useState<'customer' | 'neighbor'>('customer');
    const [neighborName, setNeighborName] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState<string>('');
    
    // Separate states for preview vs upload
    const [selectedImage, setSelectedImage] = useState<{url: string, file: File} | null>(null);
    const [isPhotoConfirmed, setIsPhotoConfirmed] = useState(false);

    const handleCustomerEnrollment = async (file: File) => {
        setUploading(true);
        setUploadStatus('Uploading your face to secure system...');

        try {
            const token = localStorage.getItem('token');
            const formData = new FormData();
            formData.append('file', file);
            formData.append('name', 'Customer');

            const response = await fetch('http://127.0.0.1:8000/api/face/id/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                setUploadStatus(`✅ Face enrolled successfully! Quality: ${(data.quality_score * 100).toFixed(1)}%`);
                setTimeout(() => {
                    navigate('/client/dashboard');
                }, 2000);
            } else {
                setUploadStatus(`❌ ${data.message || 'Enrollment failed'}`);
            }
        } catch (error) {
            setUploadStatus('❌ Connection error. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const handleNeighborAuthorization = async (file: File, url: string) => {
        if (!id) return;
        
        setUploading(true);
        setUploadStatus('Enrolling neighbor face in secure database...');

        try {
            const token = localStorage.getItem('token');
            const formData = new FormData();
            formData.append('file', file);
            formData.append('name', neighborName || 'Neighbor');

            // Store neighbor's face in database (encrypted)
            const response = await fetch('http://127.0.0.1:8000/api/face/id/upload', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: formData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                // Also store in local order for UI reference
                updateOrder(id, {
                    neighborNicImage: url,
                    neighborName: neighborName || 'Neighbor'
                });
                
                setUploadStatus(`✅ Neighbor enrolled! Quality: ${(data.quality_score * 100).toFixed(1)}%\nCourier can now verify against this reference.`);
                setTimeout(() => {
                    navigate('/client/dashboard');
                }, 2500);
            } else {
                setUploadStatus(`❌ ${data.message || 'Enrollment failed'}`);
            }
        } catch (error) {
            setUploadStatus('❌ Connection error. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    // Called when user confirms the photo in NicUploader
    const handleImageConfirmed = useCallback((url: string, file?: File) => {
        if (file) {
            setSelectedImage({ url, file });
            setIsPhotoConfirmed(true);
        }
    }, []);

    // Final upload button handler
    const handleUploadClick = async () => {
        if (!selectedImage) return;
        
        if (mode === 'customer') {
            await handleCustomerEnrollment(selectedImage.file);
        } else {
            await handleNeighborAuthorization(selectedImage.file, selectedImage.url);
        }
    };

    // Reset selection
    const handleModeChange = (newMode: 'customer' | 'neighbor') => {
        setMode(newMode);
        setSelectedImage(null);
        setIsPhotoConfirmed(false);
        setUploadStatus('');
    };

    return (
        <div className="flex flex-col h-full bg-gray-50">
            <header className="bg-white p-4 shadow-sm flex items-center gap-3">
                <button onClick={() => navigate(-1)} className="text-gray-600">
                    <ArrowLeft size={24} />
                </button>
                <div>
                    <h1 className="text-lg font-bold text-gray-800">
                        {mode === 'customer' ? 'Enroll Your Face' : 'Authorize Neighbor'}
                    </h1>
                    {id && <p className="text-xs text-gray-500">Order #{id}</p>}
                </div>
            </header>

            <div className="flex-1 p-4 overflow-y-auto flex flex-col gap-4">
                {/* Mode Selection */}
                <div className="flex gap-2">
                    <button
                        onClick={() => handleModeChange('customer')}
                        className={`flex-1 py-3 px-4 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 ${
                            mode === 'customer' ? 'bg-blue-600 text-white shadow-lg' : 'bg-white text-gray-600 border border-gray-200'
                        }`}
                    >
                        <User size={18} />
                        My Face
                    </button>
                    <button
                        onClick={() => handleModeChange('neighbor')}
                        className={`flex-1 py-3 px-4 rounded-xl font-medium transition-colors flex items-center justify-center gap-2 ${
                            mode === 'neighbor' ? 'bg-orange-600 text-white shadow-lg' : 'bg-white text-gray-600 border border-gray-200'
                        }`}
                    >
                        <Upload size={18} />
                        Neighbor
                    </button>
                </div>

                {/* AI Security Badge */}
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-3 rounded-xl border border-blue-100">
                    <div className="flex items-center gap-2 text-blue-700">
                        <Shield size={18} />
                        <span className="text-sm font-medium">Banking-Grade AI Security</span>
                    </div>
                    <p className="text-xs text-blue-600 mt-1">
                        3-Model AI: ArcFace + Facenet512 + VGG-Face
                    </p>
                </div>

                <div className="bg-white p-4 rounded-2xl shadow-sm flex-1">
                    {mode === 'customer' ? (
                        <>
                            <h3 className="font-semibold mb-2 flex items-center gap-2">
                                <User size={20} className="text-blue-600" />
                                Step 1: Take Your Photo
                            </h3>
                            <p className="text-sm text-gray-600 mb-4">
                                This photo will be your reference image. When the courier arrives, they'll verify your identity against this stored photo.
                            </p>
                            <NicUploader 
                                onImageSelected={handleImageConfirmed}
                                title="Upload Your Photo"
                                subtitle="Clear face photo for best results"
                                showCamera={true}
                                confirmBeforeUpload={true}
                            />
                        </>
                    ) : (
                        <>
                            <h3 className="font-semibold mb-2 flex items-center gap-2">
                                <Upload size={20} className="text-orange-600" />
                                Authorize Someone Else
                            </h3>
                            <p className="text-sm text-gray-600 mb-4">
                                Upload your neighbor's photo. The courier will verify them against this image.
                            </p>
                            
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Authorized Person's Name
                            </label>
                            <input
                                type="text"
                                value={neighborName}
                                onChange={(e) => setNeighborName(e.target.value)}
                                placeholder="Enter their name"
                                className="w-full p-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-orange-500 bg-gray-50 mb-4"
                            />
                            
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Their Reference Photo
                            </label>
                            <NicUploader 
                                onImageSelected={handleImageConfirmed}
                                title="Upload Their Photo"
                                subtitle="NIC photo or clear face photo"
                                showCamera={true}
                                confirmBeforeUpload={true}
                            />
                        </>
                    )}

                    {/* Upload Status */}
                    {uploadStatus && (
                        <div className={`mt-4 p-3 rounded-xl text-sm font-medium whitespace-pre-line ${
                            uploadStatus.includes('✅') 
                                ? 'bg-green-50 text-green-700 border border-green-200' 
                                : 'bg-red-50 text-red-700 border border-red-200'
                        }`}>
                            {uploadStatus}
                        </div>
                    )}

                    {/* Loading State */}
                    {uploading && (
                        <div className="mt-4 flex items-center justify-center gap-2 text-blue-600 py-3">
                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
                            <span className="text-sm">Processing with AI model...</span>
                        </div>
                    )}
                </div>

                {/* Final Upload Button - Only show when photo is confirmed */}
                {isPhotoConfirmed && !uploading && !uploadStatus.includes('✅') && (
                    <button
                        onClick={handleUploadClick}
                        disabled={uploading || (mode === 'neighbor' && !neighborName.trim())}
                        className={`w-full py-4 rounded-xl font-bold shadow-lg flex items-center justify-center gap-3 transition-all ${
                            mode === 'customer'
                                ? 'bg-blue-600 hover:bg-blue-700 text-white'
                                : 'bg-orange-600 hover:bg-orange-700 text-white'
                        } disabled:opacity-50 disabled:cursor-not-allowed`}
                    >
                        <CloudUpload size={22} />
                        {mode === 'customer' ? 'Upload & Enroll My Face' : 'Upload & Authorize Neighbor'}
                    </button>
                )}

                {/* Success confirmation */}
                {uploadStatus.includes('✅') && (
                    <div className="bg-green-50 p-4 rounded-xl border border-green-200 flex items-center gap-3">
                        <CheckCircle className="text-green-600" size={24} />
                        <div>
                            <p className="font-medium text-green-700">Enrollment Complete!</p>
                            <p className="text-xs text-green-600">Redirecting to dashboard...</p>
                        </div>
                    </div>
                )}

                <p className="text-xs text-gray-500 text-center px-4">
                    🔒 All biometric data is encrypted and stored securely using AES-256 encryption.
                </p>
            </div>
        </div>
    );
};

export default AuthorizeNeighbor;
