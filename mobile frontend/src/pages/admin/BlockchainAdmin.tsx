import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CubeTransparentIcon, 
  ShieldCheckIcon, 
  CurrencyDollarIcon,
  UserGroupIcon,
  ClockIcon,
  DocumentArrowDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
  FunnelIcon
} from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import Layout from '../../components/Layout';

interface BlockchainStats {
  contract_address: string;
  rpc_url: string;
  total_proofs: number;
  total_deliveries: number;
  total_verifications: number;
  total_cod_transactions: number;
  total_consents: number;
  blockchain_active: boolean;
}

interface BlockchainProof {
  delivery_id: string;
  block_number: number;
  transaction_hash: string;
  commitment_hash: string;
  timestamp: string;
  proof_type: string;
}

interface DashboardData {
  contract_info: {
    address: string;
    rpc_url: string;
    network: string;
  };
  statistics: BlockchainStats;
  recent_proofs: BlockchainProof[];
}

interface AllRecordsResponse {
  records: BlockchainProof[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  filters_applied: {
    proof_type: string | null;
    delivery_id: string | null;
  };
}

const BlockchainAdmin = () => {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [records, setRecords] = useState<AllRecordsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'records' | 'audit'>('overview');
  const [currentPage, setCurrentPage] = useState(1);
  const [filterType, setFilterType] = useState<string>('all');
  const [searchDeliveryId, setSearchDeliveryId] = useState('');
  const [selectedDelivery, setSelectedDelivery] = useState<string | null>(null);
  const [auditTrail, setAuditTrail] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const API_BASE = 'http://localhost:8000/api/blockchain';

  useEffect(() => {
    fetchDashboard();
  }, []);

  useEffect(() => {
    if (activeTab === 'records') {
      fetchRecords();
    }
  }, [activeTab, currentPage, filterType]);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/admin/dashboard`);
      if (!response.ok) throw new Error('Failed to fetch dashboard');
      const data = await response.json();
      setDashboard(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const fetchRecords = async () => {
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '10',
      });
      if (filterType !== 'all') params.append('proof_type', filterType);
      if (searchDeliveryId) params.append('delivery_id', searchDeliveryId);

      const response = await fetch(`${API_BASE}/admin/all-records?${params}`);
      if (!response.ok) throw new Error('Failed to fetch records');
      const data = await response.json();
      setRecords(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load records');
    }
  };

  const fetchAuditTrail = async (deliveryId: string) => {
    try {
      setSelectedDelivery(deliveryId);
      const response = await fetch(`${API_BASE}/admin/delivery/${deliveryId}/full-audit`);
      if (!response.ok) throw new Error('Failed to fetch audit trail');
      const data = await response.json();
      setAuditTrail(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit trail');
    }
  };

  const exportRecords = async () => {
    try {
      const response = await fetch(`${API_BASE}/admin/export`);
      if (!response.ok) throw new Error('Failed to export records');
      const data = await response.json();
      
      // Create downloadable JSON file
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

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getProofTypeIcon = (type: string) => {
    switch (type) {
      case 'identity_verification':
        return <ShieldCheckIcon className="w-5 h-5 text-green-500" />;
      case 'cod_transaction':
        return <CurrencyDollarIcon className="w-5 h-5 text-yellow-500" />;
      case 'neighbor_consent':
        return <UserGroupIcon className="w-5 h-5 text-blue-500" />;
      default:
        return <CubeTransparentIcon className="w-5 h-5 text-purple-500" />;
    }
  };

  const getProofTypeBadgeColor = (type: string) => {
    switch (type) {
      case 'identity_verification':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'cod_transaction':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'neighbor_consent':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
      default:
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400';
    }
  };

  if (loading) {
    return (
      <Layout title="Blockchain Admin">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout title="Blockchain Admin">
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link to="/role-selection" className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700">
              <ChevronLeftIcon className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                Blockchain Dashboard
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Privacy-First Delivery Verification System
              </p>
            </div>
          </div>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={exportRecords}
            className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg shadow-lg"
          >
            <DocumentArrowDownIcon className="w-5 h-5" />
            <span>Export</span>
          </motion.button>
        </div>

        {/* Status Banner */}
        {dashboard && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-4 rounded-xl ${
              dashboard.statistics.blockchain_active 
                ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${dashboard.statistics.blockchain_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                <span className={`font-medium ${dashboard.statistics.blockchain_active ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'}`}>
                  {dashboard.statistics.blockchain_active ? 'Blockchain Active' : 'Blockchain Offline'}
                </span>
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <span className="font-mono">{dashboard.contract_info.network}</span>
                <span className="mx-2">•</span>
                <span className="font-mono text-xs">{formatTxHash(dashboard.contract_info.address)}</span>
              </div>
            </div>
          </motion.div>
        )}

        {/* Tab Navigation */}
        <div className="flex space-x-2 border-b border-gray-200 dark:border-gray-700">
          {(['overview', 'records', 'audit'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium transition-colors ${
                activeTab === tab
                  ? 'text-purple-600 border-b-2 border-purple-600'
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'overview' && dashboard && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-6"
            >
              {/* Statistics Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard
                  title="Total Proofs"
                  value={dashboard.statistics.total_proofs}
                  icon={<CubeTransparentIcon className="w-6 h-6" />}
                  color="purple"
                />
                <StatCard
                  title="Verifications"
                  value={dashboard.statistics.total_verifications}
                  icon={<ShieldCheckIcon className="w-6 h-6" />}
                  color="green"
                />
                <StatCard
                  title="COD Transactions"
                  value={dashboard.statistics.total_cod_transactions}
                  icon={<CurrencyDollarIcon className="w-6 h-6" />}
                  color="yellow"
                />
                <StatCard
                  title="Neighbor Consents"
                  value={dashboard.statistics.total_consents}
                  icon={<UserGroupIcon className="w-6 h-6" />}
                  color="blue"
                />
              </div>

              {/* Recent Activity */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                  <ClockIcon className="w-5 h-5 text-purple-500" />
                  <span>Recent Blockchain Activity</span>
                </h3>
                {dashboard.recent_proofs.length > 0 ? (
                  <div className="space-y-3">
                    {dashboard.recent_proofs.map((proof, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                      >
                        <div className="flex items-center space-x-3">
                          {getProofTypeIcon(proof.proof_type)}
                          <div>
                            <p className="font-medium text-sm">{proof.delivery_id}</p>
                            <p className="text-xs text-gray-500">Block #{proof.block_number}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className={`text-xs px-2 py-1 rounded-full ${getProofTypeBadgeColor(proof.proof_type)}`}>
                            {proof.proof_type.replace('_', ' ')}
                          </span>
                          <p className="text-xs text-gray-500 mt-1">{formatTimestamp(proof.timestamp)}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <CubeTransparentIcon className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p>No blockchain activity yet</p>
                  </div>
                )}
              </div>

              {/* Contract Info */}
              <div className="bg-gradient-to-r from-purple-600/10 to-blue-600/10 rounded-xl p-6 border border-purple-200 dark:border-purple-800">
                <h3 className="text-lg font-semibold mb-4">Smart Contract Information</h3>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-gray-500 dark:text-gray-400">Contract Address</label>
                    <p className="font-mono text-sm break-all">{dashboard.contract_info.address}</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 dark:text-gray-400">RPC URL</label>
                    <p className="font-mono text-sm">{dashboard.contract_info.rpc_url}</p>
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-4 italic">
                  🔒 Compliant with Sri Lanka's PDPA and Electronic Transactions Act
                </p>
              </div>
            </motion.div>
          )}

          {activeTab === 'records' && (
            <motion.div
              key="records"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              {/* Filters */}
              <div className="flex flex-wrap gap-4 items-center bg-white dark:bg-gray-800 p-4 rounded-xl shadow">
                <div className="flex items-center space-x-2">
                  <FunnelIcon className="w-5 h-5 text-gray-500" />
                  <select
                    value={filterType}
                    onChange={(e) => {
                      setFilterType(e.target.value);
                      setCurrentPage(1);
                    }}
                    className="bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2 text-sm"
                  >
                    <option value="all">All Types</option>
                    <option value="identity_verification">Identity Verification</option>
                    <option value="cod_transaction">COD Transaction</option>
                    <option value="neighbor_consent">Neighbor Consent</option>
                  </select>
                </div>
                <div className="flex items-center space-x-2 flex-1 max-w-xs">
                  <MagnifyingGlassIcon className="w-5 h-5 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search by Delivery ID"
                    value={searchDeliveryId}
                    onChange={(e) => setSearchDeliveryId(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && fetchRecords()}
                    className="bg-gray-100 dark:bg-gray-700 rounded-lg px-3 py-2 text-sm flex-1"
                  />
                </div>
              </div>

              {/* Records Table */}
              <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-700">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Delivery ID</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Block #</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tx Hash</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Timestamp</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                      {records?.records.map((record, index) => (
                        <motion.tr
                          key={index}
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: index * 0.05 }}
                          className="hover:bg-gray-50 dark:hover:bg-gray-700/50"
                        >
                          <td className="px-4 py-3">
                            <span className={`text-xs px-2 py-1 rounded-full ${getProofTypeBadgeColor(record.proof_type)}`}>
                              {record.proof_type.replace('_', ' ')}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-mono text-sm">{record.delivery_id}</td>
                          <td className="px-4 py-3 text-sm">#{record.block_number}</td>
                          <td className="px-4 py-3 font-mono text-xs">{formatTxHash(record.transaction_hash)}</td>
                          <td className="px-4 py-3 text-xs text-gray-500">{formatTimestamp(record.timestamp)}</td>
                          <td className="px-4 py-3">
                            <button
                              onClick={() => {
                                setActiveTab('audit');
                                fetchAuditTrail(record.delivery_id);
                              }}
                              className="text-purple-600 hover:text-purple-800 text-sm font-medium"
                            >
                              View Audit
                            </button>
                          </td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                {records && records.total_pages > 1 && (
                  <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-sm text-gray-500">
                      Showing page {records.page} of {records.total_pages} ({records.total} total records)
                    </p>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                        disabled={currentPage === 1}
                        className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 disabled:opacity-50"
                      >
                        <ChevronLeftIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setCurrentPage(Math.min(records.total_pages, currentPage + 1))}
                        disabled={currentPage === records.total_pages}
                        className="p-2 rounded-lg bg-gray-100 dark:bg-gray-700 disabled:opacity-50"
                      >
                        <ChevronRightIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {activeTab === 'audit' && (
            <motion.div
              key="audit"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="space-y-4"
            >
              {selectedDelivery && auditTrail ? (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h3 className="text-xl font-bold">Delivery Audit Trail</h3>
                      <p className="text-sm text-gray-500 font-mono">{selectedDelivery}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-sm ${
                      auditTrail.delivery_complete 
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                    }`}>
                      {auditTrail.delivery_complete ? 'Complete' : 'In Progress'}
                    </span>
                  </div>

                  {/* Timeline */}
                  <div className="relative">
                    <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-purple-500 to-blue-500"></div>
                    <div className="space-y-6">
                      {auditTrail.identity_verification && (
                        <AuditTimelineItem
                          icon={<ShieldCheckIcon className="w-5 h-5 text-white" />}
                          color="green"
                          title="Identity Verification"
                          data={auditTrail.identity_verification}
                        />
                      )}
                      {auditTrail.cod_transaction && (
                        <AuditTimelineItem
                          icon={<CurrencyDollarIcon className="w-5 h-5 text-white" />}
                          color="yellow"
                          title="COD Transaction"
                          data={auditTrail.cod_transaction}
                        />
                      )}
                      {auditTrail.neighbor_consent && (
                        <AuditTimelineItem
                          icon={<UserGroupIcon className="w-5 h-5 text-white" />}
                          color="blue"
                          title="Neighbor Consent"
                          data={auditTrail.neighbor_consent}
                        />
                      )}
                    </div>
                  </div>

                  {/* Legal Compliance Note */}
                  <div className="mt-6 p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
                    <p className="text-sm text-purple-800 dark:text-purple-300">
                      <span className="font-semibold">🔒 Legal Compliance:</span> {auditTrail.legal_compliance_note}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-12 text-center">
                  <CubeTransparentIcon className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                  <h3 className="text-lg font-medium text-gray-600 dark:text-gray-400">Select a delivery to view audit trail</h3>
                  <p className="text-sm text-gray-500 mt-2">Go to Records tab and click "View Audit" on any record</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Toast */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg"
            >
              {error}
              <button onClick={() => setError(null)} className="ml-2 font-bold">×</button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Layout>
  );
};

// Stat Card Component
const StatCard = ({ title, value, icon, color }: { 
  title: string; 
  value: number; 
  icon: React.ReactNode;
  color: 'purple' | 'green' | 'yellow' | 'blue';
}) => {
  const colorClasses = {
    purple: 'from-purple-500 to-purple-600 bg-purple-100 dark:bg-purple-900/30',
    green: 'from-green-500 to-green-600 bg-green-100 dark:bg-green-900/30',
    yellow: 'from-yellow-500 to-yellow-600 bg-yellow-100 dark:bg-yellow-900/30',
    blue: 'from-blue-500 to-blue-600 bg-blue-100 dark:bg-blue-900/30',
  };

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-4"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-xl bg-gradient-to-br ${colorClasses[color]}`}>
          {icon}
        </div>
      </div>
    </motion.div>
  );
};

// Audit Timeline Item Component
const AuditTimelineItem = ({ icon, color, title, data }: {
  icon: React.ReactNode;
  color: 'green' | 'yellow' | 'blue';
  title: string;
  data: any;
}) => {
  const bgColors = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    blue: 'bg-blue-500',
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className="relative pl-12"
    >
      <div className={`absolute left-0 top-0 w-8 h-8 rounded-full ${bgColors[color]} flex items-center justify-center shadow-lg`}>
        {icon}
      </div>
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
        <h4 className="font-semibold">{title}</h4>
        <div className="mt-2 space-y-1 text-sm">
          <p><span className="text-gray-500">Block:</span> #{data.block_number}</p>
          <p><span className="text-gray-500">Tx Hash:</span> <span className="font-mono text-xs">{data.transaction_hash}</span></p>
          <p><span className="text-gray-500">Commitment:</span> <span className="font-mono text-xs break-all">{data.commitment_hash?.slice(0, 32)}...</span></p>
          <p><span className="text-gray-500">Timestamp:</span> {new Date(data.timestamp).toLocaleString()}</p>
        </div>
      </div>
    </motion.div>
  );
};

export default BlockchainAdmin;
