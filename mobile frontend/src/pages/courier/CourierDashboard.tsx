import { Package, MapPin, Truck, RefreshCw, AlertCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { ordersApi } from '../../services/api';
import type { FrontendOrder } from '../../services/api';

const CourierDashboard = () => {
    const navigate = useNavigate();
    const [orders, setOrders] = useState<FrontendOrder[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [userName, setUserName] = useState('Courier');

    // Fetch orders from backend
    const fetchOrders = async () => {
        try {
            setLoading(true);
            setError(null);
            const fetchedOrders = await ordersApi.getOrders();
            setOrders(fetchedOrders);
        } catch (err) {
            console.error('Error fetching orders:', err);
            setError(err instanceof Error ? err.message : 'Failed to load orders');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // Get user name from localStorage
        const userStr = localStorage.getItem('user');
        if (userStr) {
            try {
                const user = JSON.parse(userStr);
                setUserName(user.full_name || 'Courier');
            } catch (e) {
                console.error('Error parsing user data');
            }
        }

        // Fetch orders from backend
        fetchOrders();
    }, []);

    return (
        <div className="flex flex-col h-full bg-gray-50">
            <header className="bg-white p-4 shadow-sm">
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-lg font-bold text-gray-800">Delivery List</h1>
                        <p className="text-xs text-gray-500">Welcome, {userName}</p>
                    </div>
                    <button
                        onClick={fetchOrders}
                        disabled={loading}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                    >
                        <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
                    </button>
                </div>
                <button
                    onClick={() => navigate('/route')}
                    className="mt-2 w-full py-2 bg-blue-100 text-blue-700 rounded-lg text-sm font-medium flex items-center justify-center gap-2"
                >
                    <MapPin size={16} /> View Optimized Route
                </button>
            </header>

            <div className="p-4 flex flex-col gap-4">
                {/* Loading State */}
                {loading && (
                    <div className="flex items-center justify-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                        <span className="ml-2 text-gray-600">Loading orders...</span>
                    </div>
                )}

                {/* Error State */}
                {error && !loading && (
                    <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
                        <AlertCircle className="text-red-500" size={24} />
                        <div>
                            <p className="text-red-700 font-medium">Error loading orders</p>
                            <p className="text-red-600 text-sm">{error}</p>
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {!loading && !error && orders.length === 0 && (
                    <div className="text-center py-8">
                        <Package size={48} className="mx-auto text-gray-300 mb-4" />
                        <p className="text-gray-500">No deliveries assigned</p>
                        <p className="text-gray-400 text-sm">Check back later for new orders</p>
                    </div>
                )}

                {/* Orders List */}
                {!loading && orders.map(order => (
                    <div key={order.orderId} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                        <div className="flex justify-between items-start mb-3">
                            <div className="flex items-center gap-2">
                                <div className="bg-green-50 p-2 rounded-lg text-green-600">
                                    <Package size={20} />
                                </div>
                                <div>
                                    <h3 className="font-bold text-gray-800">{order.orderNumber}</h3>
                                    <p className="text-xs text-gray-500">Customer #{order.customerId}</p>
                                </div>
                            </div>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                                order.status === 'delivered' ? 'bg-green-100 text-green-600' :
                                order.status === 'in_transit' ? 'bg-blue-100 text-blue-600' :
                                order.status === 'out_for_delivery' ? 'bg-yellow-100 text-yellow-600' :
                                'bg-gray-100 text-gray-600'
                            }`}>
                                {order.status.toUpperCase().replace('_', ' ')}
                            </span>
                        </div>

                        <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
                            <MapPin size={16} />
                            {order.address}
                        </div>
                        <p className="text-xs text-gray-400 mb-4">{order.city}</p>

                        <button
                            onClick={() => navigate(`/courier/delivery/${order.orderId}`)}
                            className="w-full py-2 px-4 bg-green-600 text-white rounded-lg text-sm font-medium flex items-center justify-center gap-2 hover:bg-green-700 transition-colors shadow-sm"
                        >
                            <Truck size={16} />
                            Start Delivery
                        </button>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default CourierDashboard;
