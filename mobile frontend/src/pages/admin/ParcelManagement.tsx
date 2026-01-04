import { useState } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import DataTable from '../../components/admin/DataTable';
import { Search, Filter, Package, MapPin } from 'lucide-react';

interface Parcel {
  id: string;
  sender: string;
  recipient: string;
  status: 'pending' | 'in-transit' | 'delivered' | 'failed';
  courier: string;
  location: string;
  date: string;
}

const ParcelManagement = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  const mockParcels: Parcel[] = [
    {
      id: 'SP-12345',
      sender: 'Kamal Perera',
      recipient: 'Nimal Silva',
      status: 'in-transit',
      courier: 'C-001',
      location: 'Colombo 07',
      date: '2024-12-30',
    },
    {
      id: 'SP-12346',
      sender: 'Sunil Fernando',
      recipient: 'Priya Jayawardena',
      status: 'delivered',
      courier: 'C-002',
      location: 'Kandy',
      date: '2024-12-29',
    },
    {
      id: 'SP-12347',
      sender: 'Rohini Gunawardena',
      recipient: 'Ajith Bandara',
      status: 'pending',
      courier: '-',
      location: 'Warehouse',
      date: '2024-12-30',
    },
    {
      id: 'SP-12348',
      sender: 'Tharaka Rathnayake',
      recipient: 'Chamari Perera',
      status: 'in-transit',
      courier: 'C-003',
      location: 'Galle',
      date: '2024-12-30',
    },
    {
      id: 'SP-12349',
      sender: 'Malini Wijesekara',
      recipient: 'Ravi Mendis',
      status: 'failed',
      courier: 'C-001',
      location: 'Negombo',
      date: '2024-12-29',
    },
  ];

  const columns = [
    {
      header: 'Parcel ID',
      accessor: 'id' as keyof Parcel,
      className: 'font-mono font-semibold',
    },
    {
      header: 'Sender',
      accessor: 'sender' as keyof Parcel,
    },
    {
      header: 'Recipient',
      accessor: 'recipient' as keyof Parcel,
    },
    {
      header: 'Status',
      accessor: ((row: Parcel) => (
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${
            row.status === 'delivered'
              ? 'bg-green-100 text-green-700'
              : row.status === 'in-transit'
              ? 'bg-blue-100 text-blue-700'
              : row.status === 'failed'
              ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-700'
          }`}
        >
          {row.status.toUpperCase().replace('-', ' ')}
        </span>
      )) as any,
    },
    {
      header: 'Courier',
      accessor: 'courier' as keyof Parcel,
      className: 'font-mono',
    },
    {
      header: 'Location',
      accessor: ((row: Parcel) => (
        <div className="flex items-center gap-1">
          <MapPin className="w-4 h-4 text-gray-400" />
          <span>{row.location}</span>
        </div>
      )) as any,
    },
    {
      header: 'Date',
      accessor: 'date' as keyof Parcel,
    },
  ];

  const handleRowClick = (parcel: Parcel) => {
    console.log('Parcel clicked:', parcel);
    // TODO: Navigate to parcel detail page
  };

  const filteredParcels = mockParcels.filter((parcel) => {
    const matchesSearch =
      parcel.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      parcel.sender.toLowerCase().includes(searchTerm.toLowerCase()) ||
      parcel.recipient.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = filterStatus === 'all' || parcel.status === filterStatus;

    return matchesSearch && matchesStatus;
  });

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Parcel Management</h1>
            <p className="text-gray-600 mt-2">Track and manage all parcels</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <Package className="w-5 h-5 text-gray-600" />
              <p className="text-sm text-gray-600">Total Parcels</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">8,472</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">In Transit</p>
            <p className="text-2xl font-bold text-blue-600">847</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Delivered Today</p>
            <p className="text-2xl font-bold text-green-600">342</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <p className="text-sm text-gray-600">Failed/Pending</p>
            <p className="text-2xl font-bold text-red-600">23</p>
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
                placeholder="Search by parcel ID, sender, or recipient..."
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
                <option value="pending">Pending</option>
                <option value="in-transit">In Transit</option>
                <option value="delivered">Delivered</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table */}
        <DataTable data={filteredParcels} columns={columns} onRowClick={handleRowClick} />
      </div>
    </AdminLayout>
  );
};

export default ParcelManagement;
