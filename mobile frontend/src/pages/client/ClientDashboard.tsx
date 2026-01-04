import { Package, ShieldCheck, MapPin, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useDatabase } from '../../context/MockDatabaseContext';
import { useState, useEffect } from 'react';

const ClientDashboard = () => {
    const { orders } = useDatabase();
    const navigate = useNavigate();
    const [userName, setUserName] = useState('Client');

    useEffect(() => {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            try {
                const user = JSON.parse(userStr);
                setUserName(user.full_name || 'Client');
            } catch (e) {
                console.error('Error parsing user data');
            }
        }
    }, []);

    return (
        <div className="flex flex-col h-full bg-gray-50">
            <header className="bg-white p-4 shadow-sm">
                <h1 className="text-lg font-bold text-gray-800">My Parcels</h1>
                <p className="text-xs text-gray-500">Welcome back, {userName}</p>
            </header>

            <div className="p-4 flex flex-col gap-4">
                {orders.map(order => (
                    <div key={order.id} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                        <div className="flex justify-between items-start mb-3">
                            <div className="flex items-center gap-2">
                                <div className="bg-blue-50 p-2 rounded-lg text-blue-600">
                                    <Package size={20} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-gray-800">{order.id}</h3>
                                    <p className="text-xs text-gray-500">{order.status.toUpperCase()}</p>
                                </div>
                            </div>
                        </div>

                        <p className="text-sm text-gray-600 mb-4">{order.address}</p>

                        {order.status === 'pending' && (
                            <div className="space-y-2">
                                {/* AI-Powered Locker Selection Button */}
                                <button
                                    onClick={() => navigate(`/client/locker-selection?orderId=${order.id}`)}
                                    className="w-full py-2 px-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:from-purple-700 hover:to-blue-700 transition-colors"
                                >
                                    <MapPin size={16} />
                                    <span>Deliver to Smart Locker</span>
                                    <Sparkles size={14} className="text-yellow-300" />
                                </button>
                                
                                {/* Authorize Neighbor Button */}
                                <button
                                    onClick={() => navigate(`/client/authorize/${order.id}`)}
                                    className="w-full py-2 px-4 bg-blue-50 text-blue-600 rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-blue-100 transition-colors"
                                >
                                    <ShieldCheck size={16} />
                                    Authorize Neighbor
                                </button>
                            </div>
                        )}

                        {order.neighborNicImage && (
                            <div className="mt-2 text-xs text-green-600 flex items-center gap-1">
                                <ShieldCheck size={12} />
                                Neighbor Authorized
                            </div>
                        )}
                    </div>
                ))}

                {orders.length === 0 && (
                    <div className="bg-white p-8 rounded-xl shadow-sm text-center">
                        <Package size={48} className="mx-auto text-gray-300 mb-4" />
                        <h3 className="font-semibold text-gray-700">No Active Parcels</h3>
                        <p className="text-sm text-gray-500 mt-2">
                            Your incoming parcels will appear here
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ClientDashboard;
