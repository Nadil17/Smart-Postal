import { useState } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import DataTable from '../../components/admin/DataTable';
import { Search, Filter, UserPlus, CheckCircle, XCircle, X, User, Lock, Mail, Phone } from 'lucide-react';

interface User {
  id: string;
  name: string;
  email: string;
  role: 'client' | 'courier' | 'admin';
  status: 'active' | 'inactive' | 'suspended';
  verified: boolean;
  joinDate: string;
}

const UserManagement = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterRole, setFilterRole] = useState<string>('all');
  const [showAddCourier, setShowAddCourier] = useState(false);
  const [courierForm, setCourierForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: ''
  });
  const [formError, setFormError] = useState('');
  const [formLoading, setFormLoading] = useState(false);

  const handleCourierSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError('');
    setFormLoading(true);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://127.0.0.1:8000/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          ...courierForm,
          role: 'courier'
        }),
      });

      const data = await response.json();

      if (response.ok) {
        alert('Courier registered successfully!');
        setShowAddCourier(false);
        setCourierForm({ full_name: '', email: '', phone: '', password: '' });
      } else {
        setFormError(data.detail || 'Registration failed');
      }
    } catch (err) {
      setFormError('Could not connect to server');
    } finally {
      setFormLoading(false);
    }
  };

  const mockUsers: User[] = [
    {
      id: 'U001',
      name: 'Kamal Perera',
      email: 'kamal@email.com',
      role: 'client',
      status: 'active',
      verified: true,
      joinDate: '2024-12-15',
    },
    {
      id: 'U002',
      name: 'Nimal Silva',
      email: 'nimal@email.com',
      role: 'courier',
      status: 'active',
      verified: true,
      joinDate: '2024-11-20',
    },
    {
      id: 'U003',
      name: 'Sunil Fernando',
      email: 'sunil@email.com',
      role: 'client',
      status: 'active',
      verified: false,
      joinDate: '2024-12-28',
    },
    {
      id: 'U004',
      name: 'Priya Jayawardena',
      email: 'priya@email.com',
      role: 'courier',
      status: 'inactive',
      verified: true,
      joinDate: '2024-10-05',
    },
    {
      id: 'U005',
      name: 'Admin User',
      email: 'admin@smartpostal.com',
      role: 'admin',
      status: 'active',
      verified: true,
      joinDate: '2024-01-01',
    },
  ];

  const columns = [
    {
      header: 'User ID',
      accessor: 'id' as keyof User,
      className: 'font-mono',
    },
    {
      header: 'Name',
      accessor: 'name' as keyof User,
      className: 'font-medium',
    },
    {
      header: 'Email',
      accessor: 'email' as keyof User,
    },
    {
      header: 'Role',
      accessor: ((row: User) => (
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            row.role === 'admin'
              ? 'bg-purple-100 text-purple-700'
              : row.role === 'courier'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {row.role.toUpperCase()}
        </span>
      )) as any,
    },
    {
      header: 'Status',
      accessor: ((row: User) => (
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            row.status === 'active'
              ? 'bg-green-100 text-green-700'
              : row.status === 'suspended'
              ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {row.status.toUpperCase()}
        </span>
      )) as any,
    },
    {
      header: 'Verified',
      accessor: ((row: User) => (
        <div className="flex items-center gap-1">
          {row.verified ? (
            <CheckCircle className="w-5 h-5 text-green-600" />
          ) : (
            <XCircle className="w-5 h-5 text-red-600" />
          )}
        </div>
      )) as any,
    },
    {
      header: 'Join Date',
      accessor: 'joinDate' as keyof User,
    },
  ];

  const handleRowClick = (user: User) => {
    console.log('User clicked:', user);
    // TODO: Navigate to user detail page
  };

  const filteredUsers = mockUsers.filter((user) => {
    const matchesSearch =
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.id.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesRole = filterRole === 'all' || user.role === filterRole;

    return matchesSearch && matchesRole;
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">User Management</h1>
            <p className="text-gray-600 mt-2">Manage all users in the system</p>
          </div>
          <button 
            onClick={() => setShowAddCourier(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">
            <UserPlus className="w-5 h-5" />
            Register Courier
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Total Users</p>
            <p className="text-2xl font-bold text-gray-900">2,543</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Active Users</p>
            <p className="text-2xl font-bold text-green-600">2,198</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Couriers</p>
            <p className="text-2xl font-bold text-blue-600">156</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Unverified</p>
            <p className="text-2xl font-bold text-orange-600">89</p>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-md p-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name, email, or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Role Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={filterRole}
                onChange={(e) => setFilterRole(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">All Roles</option>
                <option value="client">Clients</option>
                <option value="courier">Couriers</option>
                <option value="admin">Admins</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <DataTable data={filteredUsers} columns={columns} onRowClick={handleRowClick} />
      </div>

      {/* Add Courier Modal */}
      {showAddCourier && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-800">Register Courier</h2>
              <button onClick={() => setShowAddCourier(false)} className="text-gray-400 hover:text-gray-600">
                <X size={24} />
              </button>
            </div>

            <form onSubmit={handleCourierSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-3 text-gray-400" size={18} />
                  <input 
                    type="text" 
                    required
                    value={courierForm.full_name}
                    onChange={(e) => setCourierForm({...courierForm, full_name: e.target.value})}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" 
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 text-gray-400" size={18} />
                  <input 
                    type="email" 
                    required
                    value={courierForm.email}
                    onChange={(e) => setCourierForm({...courierForm, email: e.target.value})}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" 
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Phone</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-3 text-gray-400" size={18} />
                  <input 
                    type="text" 
                    required
                    value={courierForm.phone}
                    onChange={(e) => setCourierForm({...courierForm, phone: e.target.value})}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" 
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 text-gray-400" size={18} />
                  <input 
                    type="password" 
                    required
                    minLength={8}
                    value={courierForm.password}
                    onChange={(e) => setCourierForm({...courierForm, password: e.target.value})}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500" 
                    placeholder="Min 8 chars, 1 uppercase, 1 digit"
                  />
                </div>
              </div>

              {formError && <div className="p-3 text-sm text-red-600 bg-red-50 rounded-lg">{formError}</div>}

              <button 
                type="submit" 
                disabled={formLoading}
                className="w-full py-3 bg-indigo-600 text-white rounded-lg font-bold hover:bg-indigo-700 transition disabled:bg-gray-400">
                {formLoading ? 'Registering...' : 'Register Courier'}
              </button>
            </form>
          </div>
        </div>
      )}
    </AdminLayout>
  );
};

export default UserManagement;
