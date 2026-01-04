import AdminLayout from '../../components/admin/AdminLayout';
import StatCard from '../../components/admin/StatCard';
import { Users, Package, Truck, DollarSign, TrendingUp, AlertCircle } from 'lucide-react';

const AdminDashboard = () => {
  const stats = [
    {
      title: 'Total Users',
      value: '2,543',
      icon: Users,
      trend: { value: 12.5, isPositive: true },
      color: 'blue' as const,
    },
    {
      title: 'Active Parcels',
      value: '847',
      icon: Package,
      trend: { value: 8.2, isPositive: true },
      color: 'green' as const,
    },
    {
      title: 'Active Couriers',
      value: '156',
      icon: Truck,
      trend: { value: 3.1, isPositive: false },
      color: 'purple' as const,
    },
    {
      title: 'Revenue (LKR)',
      value: '1.2M',
      icon: DollarSign,
      trend: { value: 15.3, isPositive: true },
      color: 'orange' as const,
    },
  ];

  const recentActivities = [
    { id: 1, type: 'delivery', message: 'Parcel #SP-12345 delivered successfully', time: '2 min ago' },
    { id: 2, type: 'user', message: 'New user registered: John Doe', time: '15 min ago' },
    { id: 3, type: 'courier', message: 'Courier #C-789 completed route', time: '23 min ago' },
    { id: 4, type: 'payment', message: 'Payment received: LKR 2,500', time: '45 min ago' },
    { id: 5, type: 'alert', message: 'Delivery delayed: Parcel #SP-67890', time: '1 hour ago' },
  ];

  const pendingActions = [
    { id: 1, action: 'Verify new courier applications', count: 8, priority: 'high' },
    { id: 2, action: 'Resolve customer disputes', count: 3, priority: 'high' },
    { id: 3, action: 'Review identity verifications', count: 12, priority: 'medium' },
    { id: 4, action: 'Approve refund requests', count: 5, priority: 'medium' },
  ];

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-600 mt-2">Welcome back! Here's what's happening today.</p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat) => (
            <StatCard key={stat.title} {...stat} />
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Recent Activities */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp className="w-6 h-6 text-indigo-600" />
              <h2 className="text-xl font-bold text-gray-900">Recent Activities</h2>
            </div>
            <div className="space-y-4">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-start gap-3 p-3 hover:bg-gray-50 rounded-lg transition-colors">
                  <div className="w-2 h-2 bg-indigo-600 rounded-full mt-2 flex-shrink-0"></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-900">{activity.message}</p>
                    <p className="text-xs text-gray-500 mt-1">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pending Actions */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center gap-2 mb-6">
              <AlertCircle className="w-6 h-6 text-orange-600" />
              <h2 className="text-xl font-bold text-gray-900">Pending Actions</h2>
            </div>
            <div className="space-y-3">
              {pendingActions.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:border-indigo-300 transition-colors cursor-pointer"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">{item.action}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs text-gray-500">{item.count} items</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          item.priority === 'high'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        {item.priority}
                      </span>
                    </div>
                  </div>
                  <button className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
                    Review →
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Quick Stats Chart Placeholder */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Delivery Performance (Last 7 Days)</h2>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
            <p className="text-gray-500">Chart visualization will be added here</p>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default AdminDashboard;
