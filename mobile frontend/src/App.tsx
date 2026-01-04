import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import AiSupport from './pages/AiSupport';
import CourierCall from './pages/CourierCall';
import RouteMap from './pages/RouteMap';
import ClientDashboard from './pages/client/ClientDashboard';
import AuthorizeNeighbor from './pages/client/AuthorizeNeighbor';
import Checkout from './pages/client/Checkout';
import CourierDashboard from './pages/courier/CourierDashboard';
import DeliveryDetail from './pages/courier/DeliveryDetail';
import AdminDashboard from './pages/admin/AdminDashboard';
import UserManagement from './pages/admin/UserManagement';
import ParcelManagement from './pages/admin/ParcelManagement';
import CourierManagement from './pages/admin/CourierManagement';
import Analytics from './pages/admin/Analytics';
import BlockchainMonitor from './pages/admin/BlockchainMonitor';
import LockerNetworkMonitor from './pages/admin/LockerNetworkMonitor';
import { DatabaseProvider } from './context/MockDatabaseContext';
import LockerSelection from './pages/client/LockerSelection';
import LockerNavigation from './pages/courier/LockerNavigation';

const RoleBasedRedirect = () => {
  // Get user role from localStorage
  const userStr = localStorage.getItem('user');
  if (!userStr) {
    return <Navigate to="/login" replace />;
  }

  try {
    const user = JSON.parse(userStr);
    const role = user.role;

    if (role === 'customer' || role === 'client') {
      return <Navigate to="/client/dashboard" replace />;
    } else if (role === 'courier') {
      return <Navigate to="/courier/dashboard" replace />;
    } else if (role === 'admin') {
      return <Navigate to="/admin/dashboard" replace />;
    }
  } catch (e) {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  }

  return <Navigate to="/login" replace />;
};

function App() {
  return (
    <DatabaseProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/client/checkout" element={<Checkout />} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<RoleBasedRedirect />} />

            {/* Client Routes */}
            <Route path="client/dashboard" element={<ClientDashboard />} />
            <Route path="client/authorize/:id" element={<AuthorizeNeighbor />} />

                    {/* Locker Routes */}
        <Route path="/client/locker-selection" element={<LockerSelection />} />
        <Route path="/courier/locker/:orderId/:lockerId" element={<LockerNavigation />} />

            {/* Courier Routes */}
            <Route path="courier/dashboard" element={<CourierDashboard />} />
            <Route path="courier/delivery/:id" element={<DeliveryDetail />} />

            {/* Other Functions */}
            <Route path="ai-support" element={<AiSupport />} />
            <Route path="call" element={<CourierCall />} />
            <Route path="route" element={<RouteMap />} />
          </Route>

          {/* Admin Routes - Separate from Layout */}
          <Route path="/admin" element={<ProtectedRoute />}>
            <Route path="dashboard" element={<AdminDashboard />} />
            <Route path="users" element={<UserManagement />} />
            <Route path="parcels" element={<ParcelManagement />} />
            <Route path="couriers" element={<CourierManagement />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="blockchain" element={<BlockchainMonitor />} />
            <Route path="lockers" element={<LockerNetworkMonitor />} />
          </Route>
        </Routes>
      </Router>
    </DatabaseProvider>
  );
}

export default App;
