import { useState } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import DataTable from '../../components/admin/DataTable';
import { Search, Filter, Truck, Star } from 'lucide-react';

interface Courier {
  id: string;
  name: string;
  phone: string;
  status: 'active' | 'inactive' | 'on-break';
  deliveries: number;
  rating: number;
  location: string;
}

const CourierManagement = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const mockCouriers: Courier[] = [
    {
      id: 'C-001',
      name: 'Nimal Silva',
      phone: '+94 77 123 4567',
      status: 'active',
      deliveries: 145,
      rating: 4.8,
      location: 'Colombo 07',
    },
    {
      id: 'C-002',
      name: 'Priya Jayawardena',
      phone: '+94 71 234 5678',
      status: 'active',
      deliveries: 198,
      rating: 4.9,
      location: 'Kandy',
    },
    {
      id: 'C-003',
      name: 'Tharaka Rathnayake',
      phone: '+94 76 345 6789',
      status: 'on-break',
      deliveries: 87,
      rating: 4.6,
      location: 'Galle',
    },
    {
      id: 'C-004',
      name: 'Chamika Fernando',
      phone: '+94 75 456 7890',
      status: 'active',
      deliveries: 223,
      rating: 4.95,
      location: 'Negombo',
    },
    {
      id: 'C-005',
      name: 'Roshan Perera',
      phone: '+94 72 567 8901',
      status: 'inactive',
      deliveries: 56,
      rating: 4.2,
      location: 'Moratuwa',
    },
  ];

  const columns = [
    {
      header: 'Courier ID',
      accessor: 'id' as keyof Courier,
      className: 'font-mono font-semibold',
    },
    {
      header: 'Name',
      accessor: 'name' as keyof Courier,
      className: 'font-medium',
    },
    {
      header: 'Phone',
      accessor: 'phone' as keyof Courier,
    },
    {
      header: 'Status',
      accessor: ((row: Courier) => (
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            row.status === 'active'
              ? 'bg-green-100 text-green-700'
              : row.status === 'on-break'
              ? 'bg-yellow-100 text-yellow-700'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {row.status.toUpperCase().replace('-', ' ')}
        </span>
      )) as any,
    },
    {
      header: 'Deliveries',
      accessor: 'deliveries' as keyof Courier,
      className: 'font-semibold',
    },
    {
      header: 'Rating',
      accessor: ((row: Courier) => (
        <div className="flex items-center gap-1">
          <Star className="w-4 h-4 text-yellow-500 fill-yellow-500" />
          <span className="font-semibold">{row.rating.toFixed(1)}</span>
        </div>
      )) as any,
    },
    {
      header: 'Current Location',
      accessor: 'location' as keyof Courier,
    },
  ];

  const handleRowClick = (courier: Courier) => {
    console.log('Courier clicked:', courier);
    // TODO: Navigate to courier detail page
  };

  const filteredCouriers = mockCouriers.filter((courier) => {
    const matchesSearch =
      courier.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      courier.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      courier.phone.includes(searchTerm);

    const matchesStatus = filterStatus === 'all' || courier.status === filterStatus;

    return matchesSearch && matchesStatus;
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Courier Management</h1>
            <p className="text-gray-600 mt-2">Manage and monitor all delivery couriers</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-gray-600" />
              <p className="text-sm text-gray-600">Total Couriers</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">156</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Active Now</p>
            <p className="text-2xl font-bold text-green-600">87</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">On Break</p>
            <p className="text-2xl font-bold text-yellow-600">15</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Avg. Rating</p>
            <div className="flex items-center gap-1 mt-1">
              <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
              <p className="text-2xl font-bold text-gray-900">4.7</p>
            </div>
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
                placeholder="Search by ID, name, or phone..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-400" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="on-break">On Break</option>
                <option value="inactive">Inactive</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <DataTable data={filteredCouriers} columns={columns} onRowClick={handleRowClick} />
      </div>
    </AdminLayout>
  );
};

export default CourierManagement;
