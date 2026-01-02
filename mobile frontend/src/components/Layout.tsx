import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { Home, MessageSquare, Map, LogOut } from 'lucide-react';
import clsx from 'clsx';
import { useDatabase } from '../context/MockDatabaseContext';

const Layout = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { logout, currentUserRole } = useDatabase();

    // Check if we're on the route map page for full-height layout
    const isMapRoute = location.pathname === '/route';

    const navItems = [
        { path: '/', icon: Home, label: 'Home', roles: ['client', 'courier'] },
        { path: '/ai-support', icon: MessageSquare, label: 'AI Support', roles: ['client', 'courier'] },
        { path: '/route', icon: Map, label: 'Route', roles: ['courier'] },
    ].filter(item => item.roles.includes(currentUserRole || ''));

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            <main className={clsx(
                "flex-1 pb-20",
                isMapRoute ? "overflow-hidden" : "overflow-y-auto"
            )}>
                <Outlet />
            </main>

            <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 px-4 py-2 flex justify-around items-center z-50">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = location.pathname === item.path;
                    return (
                        <Link
                            key={item.path}
                            to={item.path}
                            className={clsx(
                                "flex flex-col items-center p-2 rounded-lg transition-colors",
                                isActive ? "text-blue-600 bg-blue-50" : "text-gray-500 hover:text-gray-700"
                            )}
                        >
                            <Icon size={24} />
                            <span className="text-xs mt-1 font-medium">{item.label}</span>
                        </Link>
                    );
                })}
                <button
                    onClick={() => {
                        logout();
                        navigate('/login');
                    }}
                    className="flex flex-col items-center p-2 rounded-lg transition-colors text-gray-500 hover:text-red-600"
                >
                    <LogOut size={24} />
                    <span className="text-xs mt-1 font-medium">Logout</span>
                </button>
            </nav>
        </div>
    );
};

export default Layout;
