import { User, Truck, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDatabase } from '../context/MockDatabaseContext';

const RoleSelection = () => {
    const navigate = useNavigate();
    const { setRole } = useDatabase();

    const handleSelectRole = (role: 'client' | 'courier' | 'admin') => {
        setRole(role);
        if (role === 'client') {
            navigate('/client/dashboard');
        } else if (role === 'courier') {
            navigate('/courier/dashboard');
        } else {
            navigate('/admin/dashboard');
        }
    };

    return (
        <div className="flex flex-col items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-6">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">Courier Pro</h1>
            <p className="text-gray-500 mb-10 text-center">Select your role to continue</p>

            <div className="flex flex-col gap-4 w-full max-w-sm">
                <button
                    onClick={() => handleSelectRole('client')}
                    className="flex items-center gap-4 p-6 bg-white rounded-2xl shadow-sm hover:shadow-md transition-all active:scale-95 border border-gray-100"
                >
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600">
                        <User size={24} />
                    </div>
                    <div className="text-left">
                        <h2 className="font-bold text-gray-800">I am a Client</h2>
                        <p className="text-sm text-gray-500">Track parcels & authorize neighbors</p>
                    </div>
                </button>

                <button
                    onClick={() => navigate('/client/checkout')}
                    className="flex items-center gap-4 p-6 bg-white rounded-2xl shadow-sm hover:shadow-md transition-all active:scale-95 border border-gray-100"
                >
                    <div className="w-12 h-12 bg-purple-100 rounded-full flex items-center justify-center text-purple-600">
                        <User size={24} />
                    </div>
                    <div className="text-left">
                        <h2 className="font-bold text-gray-800">Place Order</h2>
                        <p className="text-sm text-gray-500">Enroll Voice & Checkout</p>
                    </div>
                </button>

                <button
                    onClick={() => handleSelectRole('courier')}
                    className="flex items-center gap-4 p-6 bg-white rounded-2xl shadow-sm hover:shadow-md transition-all active:scale-95 border border-gray-100"
                >
                    <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center text-green-600">
                        <Truck size={24} />
                    </div>
                    <div className="text-left">
                        <h2 className="font-bold text-gray-800">I am a Courier</h2>
                        <p className="text-sm text-gray-500">Manage deliveries & verify identity</p>
                    </div>
                </button>

                <button
                    onClick={() => handleSelectRole('admin')}
                    className="flex items-center gap-4 p-6 bg-white rounded-2xl shadow-sm hover:shadow-md transition-all active:scale-95 border border-gray-100"
                >
                    <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600">
                        <Shield size={24} />
                    </div>
                    <div className="text-left">
                        <h2 className="font-bold text-gray-800">I am an Admin</h2>
                        <p className="text-sm text-gray-500">Manage system & monitor operations</p>
                    </div>
                </button>
            </div>
        </div>
    );
};

export default RoleSelection;
