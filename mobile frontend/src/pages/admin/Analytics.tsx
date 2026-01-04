import AdminLayout from '../../components/admin/AdminLayout';
import StatCard from '../../components/admin/StatCard';
import { TrendingUp, Package, DollarSign, Users, Clock } from 'lucide-react';

const Analytics = () => {
  const stats = [
    {
      title: 'Total Revenue',
      value: 'LKR 1.2M',
      icon: DollarSign,
      trend: { value: 15.3, isPositive: true },
      color: 'green' as const,
    },
    {
      title: 'Deliveries',
      value: '8,472',
      icon: Package,
      trend: { value: 12.5, isPositive: true },
      color: 'blue' as const,
    },
    {
      title: 'New Users',
      value: '342',
      icon: Users,
      trend: { value: 8.7, isPositive: true },
      color: 'purple' as const,
    },
    {
      title: 'Avg. Delivery Time',
      value: '2.4h',
      icon: Clock,
      trend: { value: 5.2, isPositive: false },
      color: 'orange' as const,
    },
  ];

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-600 mt-2">Performance metrics and insights</p>
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat) => (
            <StatCard key={stat.title} {...stat} />
          ))}
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue Chart */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-6 h-6 text-green-600" />
              <h2 className="text-xl font-bold text-gray-900">Revenue Trend</h2>
            </div>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
              <p className="text-gray-500">Line chart: Revenue over time</p>
            </div>
          </div>

          {/* Delivery Status */}
          <div className="bg-white rounded-xl shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <Package className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-bold text-gray-900">Delivery Status</h2>
            </div>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
              <p className="text-gray-500">Pie chart: Delivered, In-transit, Pending</p>
            </div>
          </div>
        </div>

        {/* Performance Metrics */}
        <div className="bg-white rounded-xl shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Delivery Performance</h2>
          <div className="h-80 flex items-center justify-center bg-gray-50 rounded-lg">
            <p className="text-gray-500">Bar chart: Deliveries per day for last 30 days</p>
          </div>
        </div>

        {/* Regional Performance */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Top Performing Regions</h2>
            <div className="space-y-3">
              {[
                { region: 'Colombo', deliveries: 2456, percentage: 29 },
                { region: 'Kandy', deliveries: 1823, percentage: 21.5 },
                { region: 'Galle', deliveries: 1456, percentage: 17.2 },
                { region: 'Negombo', deliveries: 987, percentage: 11.6 },
                { region: 'Others', deliveries: 1750, percentage: 20.7 },
              ].map((item) => (
                <div key={item.region}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-gray-700">{item.region}</span>
                    <span className="text-sm text-gray-600">
                      {item.deliveries} ({item.percentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-indigo-600 h-2 rounded-full transition-all"
                      style={{ width: `${item.percentage}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Peak Hours</h2>
            <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
              <p className="text-gray-500">Heatmap: Delivery activity by hour</p>
            </div>
          </div>
        </div>
      </div>
    </AdminLayout>
  );
};

export default Analytics;
