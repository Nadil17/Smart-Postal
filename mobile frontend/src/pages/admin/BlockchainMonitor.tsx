import { useState, useEffect } from 'react';
import AdminLayout from '../../components/admin/AdminLayout';
import DataTable from '../../components/admin/DataTable';
import { 
  Blocks, 
  Activity, 
  Shield,
  DollarSign, 
  Users, 
  Download,
  RefreshCcw,
  FileText
} from 'lucide-react';

interface BlockchainStats {
  total_verifications: number;
  total_deliveries: number;
  total_cod_transactions: number;
  total_cod_amount_lkr: number;
  total_disputes: number;
  resolved_disputes: number;
}

interface BlockchainProof {
  delivery_id: string;
  block_number: number;
  transaction_hash: string;
  commitment_hash: string;
  timestamp: string;
  record_type: string;
  verification_status: string;
}

interface DashboardData {
  blockchain_status: string;
  contract_address: string;
  rpc_url: string;
  statistics: BlockchainStats;
  recent_proofs: BlockchainProof[];
}

interface AllRecordsResponse {
  success: boolean;
  records: BlockchainProof[];
  total: number;
  page: number;
  limit: number;
  statistics: BlockchainStats;
}

const BlockchainMonitor = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [records, setRecords] = useState<AllRecordsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchDeliveryId, setSearchDeliveryId] = useState('');
  const [selectedDelivery, setSelectedDelivery] = useState<string | null>(null);
  const [auditTrail, setAuditTrail] = useState<any>(null);
  const [showAuditModal, setShowAuditModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = 'http://localhost:8000/api/blockchain';

  useEffect(() => {
    fetchDashboard();
    fetchRecords();
  }, []);

  useEffect(() => {
    fetchRecords();
  }, [currentPage, filterType]);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/dashboard`);
      if (!response.ok) throw new Error('Failed to fetch dashboard');
      const data = await response.json();
      setDashboard(data);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchRecords = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        limit: '10',
      });
      if (filterType !== 'all') params.append('record_type', filterType);

      const response = await fetch(`${API_BASE}/admin/all-records?${params}`);
      if (!response.ok) throw new Error('Failed to fetch records');
      const data = await response.json();
      setRecords(data);
    } catch (err) {
      console.error('Records fetch error:', err);
    }
  };

  const fetchAuditTrail = async (deliveryId: string) => {
    try {
      setSelectedDelivery(deliveryId);
      const response = await fetch(`${API_BASE}/admin/delivery/${deliveryId}/full-audit`);
      if (!response.ok) throw new Error('Failed to fetch audit trail');
      const data = await response.json();
      setAuditTrail(data);
      setShowAuditModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit trail');
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchDashboard();
    await fetchRecords();
    setRefreshing(false);
  };

  const exportRecords = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/export`);
      if (!response.ok) throw new Error('Failed to export records');
      const data = await response.json();
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `blockchain-records-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export records');
    }
  };

  const formatTxHash = (hash: string) => {
    if (!hash) return 'N/A';
    return `${hash.slice(0, 10)}...${hash.slice(-8)}`;
  };

  const getProofTypeBadge = (type: string) => {
    const badges: Record<string, { bg: string; text: string; label: string }> = {
      VERIFICATION: { bg: 'bg-green-100', text: 'text-green-700', label: 'Verification' },
      COD: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'COD' },
      CONSENT: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'Consent' },
      DISPUTE: { bg: 'bg-red-100', text: 'text-red-700', label: 'Dispute' },
    };
    const badge = badges[type] || { bg: 'bg-purple-100', text: 'text-purple-700', label: type || 'Unknown' };
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${badge.bg} ${badge.text}`}>
        {badge.label}
      </span>
    );
  };

  const columns = [
    {
      header: 'Type',
      accessor: ((row: BlockchainProof) => getProofTypeBadge(row.record_type)) as any,
    },
    {
      header: 'Delivery ID',
      accessor: 'delivery_id' as keyof BlockchainProof,
      className: 'font-mono text-xs',
    },
    {
      header: 'Block #',
      accessor: ((row: BlockchainProof) => `#${row.block_number || 'N/A'}`) as any,
      className: 'font-mono',
    },
    {
      header: 'Transaction Hash',
      accessor: ((row: BlockchainProof) => (
        <span className="font-mono text-xs">{formatTxHash(row.transaction_hash)}</span>
      )) as any,
    },
    {
      header: 'Timestamp',
      accessor: ((row: BlockchainProof) => new Date(row.timestamp).toLocaleString()) as any,
    },
    {
      header: 'Actions',
      accessor: ((row: BlockchainProof) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            fetchAuditTrail(row.delivery_id);
          }}
          className="text-indigo-600 hover:text-indigo-800 text-sm font-medium flex items-center gap-1"
        >
          <FileText className="w-4 h-4" />
          Audit
        </button>
      )) as any,
    },
  ];

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent"></div>
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Blockchain Monitor</h1>
            <p className="text-gray-600 mt-2">
              Real-time blockchain verification records • Privacy-First Delivery System
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCcw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={exportRecords}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* Network Status Banner */}
        {dashboard && (
          <div className={`rounded-lg p-4 ${
            dashboard.blockchain_status === 'online' 
              ? 'bg-green-50 border border-green-200'
              : 'bg-red-50 border border-red-200'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  dashboard.blockchain_status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`}></div>
                <span className={`font-medium ${
                  dashboard.blockchain_status === 'online' ? 'text-green-700' : 'text-red-700'
                }`}>
                  {dashboard.blockchain_status === 'online' ? 'Blockchain Network Active' : 'Blockchain Network Offline'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>Network: <span className="font-mono font-semibold">Hardhat Local</span></span>
                <span>Contract: <span className="font-mono">{formatTxHash(dashboard.contract_address || '')}</span></span>
              </div>
            </div>
          </div>
        )}

        {/* Statistics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <Blocks className="w-5 h-5 text-purple-600" />
              <p className="text-sm text-gray-600">Total Proofs</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {dashboard?.statistics?.total_verifications || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-600" />
              <p className="text-sm text-gray-600">Deliveries</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {dashboard?.statistics?.total_deliveries || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-green-600" />
              <p className="text-sm text-gray-600">Verifications</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {dashboard?.statistics?.total_verifications || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-yellow-600" />
              <p className="text-sm text-gray-600">COD Transactions</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {dashboard?.statistics?.total_cod_transactions || 0}
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5 text-indigo-600" />
              <p className="text-sm text-gray-600">Disputes</p>
            </div>
            <p className="text-2xl font-bold text-gray-900 mt-1">
              {dashboard?.statistics?.total_disputes || 0}
            </p>
          </div>
        </div>

        {/* Smart Contract Info */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Smart Contract: DeliveryProofRegistry</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900">Contract Address</h3>
              <p className="text-sm text-gray-600 font-mono mt-1 break-all">
                {dashboard?.contract_address || 'Not connected'}
              </p>
            </div>
            <div className="border border-gray-200 rounded-lg p-4">
              <h3 className="font-semibold text-gray-900">RPC Endpoint</h3>
              <p className="text-sm text-gray-600 font-mono mt-1">
                {dashboard?.rpc_url || 'Not connected'}
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-4 italic">
            🔒 Compliant with Sri Lanka's Personal Data Protection Act (PDPA) and Electronic Transactions Act
          </p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl shadow-md p-4">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex items-center gap-2">
              <label className="text-sm text-gray-600">Filter by Type:</label>
              <select
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value);
                  setCurrentPage(1);
                }}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              >
                <option value="all">All Types</option>
                <option value="proof">Verification Proofs</option>
                <option value="cod">COD Transactions</option>
                <option value="consent">Neighbor Consents</option>
                <option value="dispute">Disputes</option>
              </select>
            </div>
            <div className="flex items-center gap-2 flex-1 max-w-xs">
              <label className="text-sm text-gray-600">Search:</label>
              <input
                type="text"
                placeholder="Delivery ID"
                value={searchDeliveryId}
                onChange={(e) => setSearchDeliveryId(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && fetchRecords()}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm flex-1"
              />
            </div>
            <button
              onClick={fetchRecords}
              className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm"
            >
              Search
            </button>
          </div>
        </div>

        {/* Records Table */}
        <div className="space-y-4">
          <h2 className="text-xl font-bold text-gray-900">Blockchain Records</h2>
          {records && records.records.length > 0 ? (
            <>
              <DataTable data={records.records} columns={columns} />
              
              {/* Pagination */}
              {records.total > records.limit && (
                <div className="flex items-center justify-between bg-white rounded-lg shadow-md p-4">
                  <p className="text-sm text-gray-600">
                    Showing page {records.page} of {Math.ceil(records.total / records.limit)} ({records.total} total records)
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                      disabled={currentPage === 1}
                      className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <button
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage >= Math.ceil(records.total / records.limit)}
                      className="px-3 py-1 border rounded hover:bg-gray-50 disabled:opacity-50"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-xl shadow-md p-12 text-center">
              <Blocks className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-600">No blockchain records found</h3>
              <p className="text-sm text-gray-500 mt-2">
                Verification proofs will appear here once deliveries are processed
              </p>
            </div>
          )}
        </div>

        {/* Audit Trail Modal */}
        {showAuditModal && auditTrail && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xl font-bold">Delivery Audit Trail</h3>
                    <p className="text-sm text-gray-500 font-mono">{selectedDelivery}</p>
                  </div>
                  <button
                    onClick={() => setShowAuditModal(false)}
                    className="text-gray-400 hover:text-gray-600 text-2xl"
                  >
                    ×
                  </button>
                </div>

                <div className="space-y-4">
                  {auditTrail.identity_verification && (
                    <AuditSection
                      title="Identity Verification"
                      icon={<Shield className="w-5 h-5 text-white" />}
                      color="green"
                      data={auditTrail.identity_verification}
                    />
                  )}
                  {auditTrail.cod_transaction && (
                    <AuditSection
                      title="COD Transaction"
                      icon={<DollarSign className="w-5 h-5 text-white" />}
                      color="yellow"
                      data={auditTrail.cod_transaction}
                    />
                  )}
                  {auditTrail.neighbor_consent && (
                    <AuditSection
                      title="Neighbor Consent"
                      icon={<Users className="w-5 h-5 text-white" />}
                      color="blue"
                      data={auditTrail.neighbor_consent}
                    />
                  )}
                </div>

                {/* Status */}
                <div className="mt-6 flex items-center justify-between">
                  <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                    auditTrail.delivery_complete 
                      ? 'bg-green-100 text-green-700'
                      : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {auditTrail.delivery_complete ? '✓ Delivery Complete' : '⏳ In Progress'}
                  </span>
                </div>

                {/* Compliance Note */}
                <div className="mt-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
                  <p className="text-sm text-purple-800">
                    <span className="font-semibold">🔒 Legal Compliance:</span> {auditTrail.legal_compliance_note}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Error Toast */}
        {error && (
          <div className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg">
            {error}
            <button onClick={() => setError(null)} className="ml-2 font-bold">×</button>
          </div>
        )}
      </div>
    </AdminLayout>
  );
};

// Audit Section Component
const AuditSection = ({ title, icon, color, data }: {
  title: string;
  icon: React.ReactNode;
  color: 'green' | 'yellow' | 'blue';
  data: any;
}) => {
  const bgColors = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500',
  };

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-8 h-8 rounded-full ${bgColors[color]} flex items-center justify-center`}>
          {icon}
        </div>
        <h4 className="font-semibold">{title}</h4>
      </div>
      <div className="space-y-2 text-sm pl-11">
        <p><span className="text-gray-500">Block Number:</span> <span className="font-mono">#{data.block_number}</span></p>
        <p><span className="text-gray-500">Transaction Hash:</span> <span className="font-mono text-xs break-all">{data.transaction_hash}</span></p>
        <p><span className="text-gray-500">Commitment Hash:</span> <span className="font-mono text-xs break-all">{data.commitment_hash?.slice(0, 48)}...</span></p>
        <p><span className="text-gray-500">Timestamp:</span> {new Date(data.timestamp).toLocaleString()}</p>
      </div>
    </div>
  );
};

export default BlockchainMonitor;
