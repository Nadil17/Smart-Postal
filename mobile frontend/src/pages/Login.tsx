import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { LogIn, User, Lock } from 'lucide-react';

const Login = () => {
    // We keep the variable name 'username' to match your UI, 
    // but we will send it as 'email' to the backend.
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // 1. Point to your real FastAPI URL
            const response = await fetch('http://127.0.0.1:8000/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // 2. Mapping: send the UI 'username' to the backend 'email' field
                body: JSON.stringify({ 
                    email: username, 
                    password: password 
                })
            });

            const data = await response.json();

            if (response.ok) {
                // 3. Store the Token and User Info in LocalStorage
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('user', JSON.stringify(data.user));

                // 4. Redirect based on the ROLE from MySQL
                // Backend uses: 'customer', 'courier', 'admin'
                const userRole = data.user.role;
                
                if (userRole === 'admin') {
                    navigate('/admin/dashboard');
                } else if (userRole === 'courier') {
                    navigate('/courier/dashboard');
                } else {
                    // This handles 'customer' / 'client'
                    navigate('/client/dashboard');
                }
            } else {
                // Catches 'Invalid credentials' or 'Inactive account'
                setError(data.detail || 'Login failed');
            }
        } catch (err) {
            setError('Cannot connect to Server. Please check if FastAPI and XAMPP are running.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex flex-col items-center justify-center h-screen bg-gradient-to-br from-blue-50 to-indigo-50 p-6">
            <div className="w-full max-w-md">
                <div className="text-center mb-8">
                    <div className="w-20 h-20 bg-blue-600 rounded-full mx-auto mb-4 flex items-center justify-center">
                        <LogIn size={40} className="text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-gray-800">Courier Pro</h1>
                    <p className="text-gray-500 mt-2">Sign in to continue</p>
                </div>

                <form onSubmit={handleSubmit} className="bg-white p-8 rounded-2xl shadow-lg">
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Username (Email)
                        </label>
                        <div className="relative">
                            <User size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder="Enter your email"
                                required
                            />
                        </div>
                    </div>

                    <div className="mb-6">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Password
                        </label>
                        <div className="relative">
                            <Lock size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder="Enter password"
                                required
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full py-3 bg-blue-600 text-white rounded-lg font-bold shadow-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                    >
                        {loading ? 'Authenticating...' : 'Sign In'}
                    </button>

                    <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-600 font-medium mb-2">Login Help:</p>
                        <p className="text-xs text-gray-500 italic">Use the email you registered with (e.g., dev_test_01@example.com)</p>
                    </div>

                    <div className="mt-6 text-center">
                        <p className="text-sm text-gray-600">
                            Don't have an account?{' '}
                            <Link to="/register" className="text-blue-600 font-medium hover:text-blue-700">
                                Create Account
                            </Link>
                        </p>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default Login;