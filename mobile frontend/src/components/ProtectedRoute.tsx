import { Navigate, Outlet } from 'react-router-dom';
import type { ReactNode } from 'react';

interface ProtectedRouteProps {
    children?: ReactNode;
}

const ProtectedRoute = ({ children }: ProtectedRouteProps) => {
    // Check if user is authenticated via localStorage token
    const token = localStorage.getItem('token');
    const isAuthenticated = !!token;

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return children ? <>{children}</> : <Outlet />;
};

export default ProtectedRoute;
