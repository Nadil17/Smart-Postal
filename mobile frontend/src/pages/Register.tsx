import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UserPlus, User, Lock, Mail, Shield, Phone } from 'lucide-react';

const Register = () => {
    const [formData, setFormData] = useState({
        full_name: '',
        email: '',
        phone: '',
        password: '',
        confirmPassword: ''
    });
    
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);
    const navigate = useNavigate();

    const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
        setError('');
    };

    const validateForm = () => {
        if (formData.password.length < 8) {
            setError('Password must be at least 8 characters');
            return false;
        }
        if (!/[A-Z]/.test(formData.password)) {
            setError('Password must contain at least one uppercase letter');
            return false;
        }
        if (!/\d/.test(formData.password)) {
            setError('Password must contain at least one digit');
            return false;
        }
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return false;
        }
        return true;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!validateForm()) return;

        setLoading(true);
        setError('');

        try {
            const response = await fetch('http://127.0.0.1:8000/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password,
                    full_name: formData.full_name,
                    phone: formData.phone,
                    role: 'customer'
                }),
            });

            const data = await response.json();

            if (response.ok) {
                setSuccess(true);
                setTimeout(() => navigate('/login'), 2000);
            } else {
                // This catches the "Email already registered" error you saw in CMD
                setError(data.detail || 'Registration failed');
            }
        } catch (err) {
            setError('Could not connect to the server. Is FastAPI running?');
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="flex flex-col items-center justify-center h-screen bg-green-50">
                <div className="bg-white p-8 rounded-2xl shadow-lg text-center">
                    <Shield size={60} className="text-green-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold">Account Created!</h2>
                    <p className="text-gray-600">Redirecting to login...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-6">
            <div className="w-full max-w-md bg-white p-8 rounded-2xl shadow-xl">
                <div className="text-center mb-6">
                    <UserPlus size={48} className="text-indigo-600 mx-auto mb-2" />
                    <h1 className="text-2xl font-bold">Create Account</h1>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Full Name</label>
                        <div className="relative">
                            <User className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input name="full_name" type="text" onChange={handleChange} required
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input name="email" type="email" onChange={handleChange} required
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Phone</label>
                        <div className="relative">
                            <Phone className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input name="phone" type="text" onChange={handleChange} required
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input name="password" type="password" onChange={handleChange} required
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Confirm Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-3 text-gray-400" size={18} />
                            <input name="confirmPassword" type="password" onChange={handleChange} required
                                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" />
                        </div>
                    </div>

                    {error && <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">{error}</div>}

                    <button type="submit" disabled={loading}
                        className="w-full py-3 bg-indigo-600 text-white rounded-lg font-bold hover:bg-indigo-700 transition disabled:bg-gray-400">
                        {loading ? 'Processing...' : 'Register'}
                    </button>

                    <div className="mt-4 text-center">
                        <p className="text-sm text-gray-600">
                            Already have an account?{' '}
                            <a href="/login" className="text-indigo-600 font-medium hover:text-indigo-700">
                                Sign In
                            </a>
                        </p>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default Register;