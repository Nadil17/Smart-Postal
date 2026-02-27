// screens/AutoReroutingScreen.jsx
import React from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
} from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';

const DEFAULT_REGION = {
  latitude: 6.9271, longitude: 79.8612,
  latitudeDelta: 0.12, longitudeDelta: 0.12,
};

const SEVERITY_COLORS = {
  MINIMAL: '#10b981', LOW: '#3b82f6',
  MEDIUM: '#f59e0b', HIGH: '#f97316', CRITICAL: '#ef4444',
};

export default function AutoReroutingScreen({ route, navigation }) {
  const {
    originalRoute, newRoute, impactAnalysis,
    oldConditions, newConditions, deliveries,
  } = route.params || {};

  const origCoords = originalRoute?.deliveries?.map((d) => ({
    latitude: d.latitude, longitude: d.longitude,
  })) || [];

  const newCoords = newRoute?.deliveries?.map((d) => ({
    latitude: d.latitude, longitude: d.longitude,
  })) || [];

  // Find divergence point (first point that differs significantly)
  let divergenceIdx = -1;
  for (let i = 0; i < Math.min(origCoords.length, newCoords.length); i++) {
    const dLat = Math.abs(origCoords[i].latitude - newCoords[i].latitude);
    const dLng = Math.abs(origCoords[i].longitude - newCoords[i].longitude);
    if (dLat > 0.001 || dLng > 0.001) {
      divergenceIdx = i;
      break;
    }
  }

  const region = React.useMemo(() => {
    const allPts = [...origCoords, ...newCoords];
    if (!allPts.length) return DEFAULT_REGION;
    const lats = allPts.map((p) => p.latitude);
    const lngs = allPts.map((p) => p.longitude);
    return {
      latitude: (Math.min(...lats) + Math.max(...lats)) / 2,
      longitude: (Math.min(...lngs) + Math.max(...lngs)) / 2,
      latitudeDelta: (Math.max(...lats) - Math.min(...lats)) * 1.4 + 0.02,
      longitudeDelta: (Math.max(...lngs) - Math.min(...lngs)) * 1.4 + 0.02,
    };
  }, [origCoords, newCoords]);

  const severity = impactAnalysis?.severity || 'MEDIUM';
  const sevColor = SEVERITY_COLORS[severity] || '#f59e0b';

  const wIcon = (w) => ({ clear: '☀️', light_rain: '🌦️', heavy_rain: '🌧️', flooding: '⛈️' }[w] || '🌤️');
  const tIcon = (t) => ({ low: '🟢', moderate: '🟡', high: '🔴', severe: '🔴' }[t] || '🟡');

  return (
    <View style={styles.container}>
      {/* Map */}
      <MapView style={styles.map} initialRegion={region}>
        {/* Original (discarded) route – red dashed */}
        {origCoords.length > 1 && (
          <Polyline
            coordinates={origCoords}
            strokeColor="#ef4444"
            strokeWidth={3}
            lineDashPattern={[10, 6]}
          />
        )}

        {/* New optimised route – green solid */}
        {newCoords.length > 1 && (
          <Polyline
            coordinates={newCoords}
            strokeColor="#10b981"
            strokeWidth={5}
          />
        )}

        {/* Divergence point */}
        {divergenceIdx >= 0 && origCoords[divergenceIdx] && (
          <Marker
            coordinate={origCoords[divergenceIdx]}
            title="Routes Diverge Here ⚠️"
          >
            <View style={styles.divMarker}>
              <Text style={styles.divIcon}>⚠️</Text>
            </View>
          </Marker>
        )}

        {/* Depot */}
        <Marker coordinate={{ latitude: 6.9271, longitude: 79.8612 }} title="Postal Depot">
          <View style={styles.depotMarker}><Text>🏢</Text></View>
        </Marker>

        {/* Delivery points */}
        {deliveries?.map((d, i) => (
          <Marker
            key={i}
            coordinate={{ latitude: d.latitude, longitude: d.longitude }}
          >
            <View style={[styles.stopMarker, d.priority === 'urgent' ? styles.urgentM : styles.regularM]}>
              <Text style={styles.stopNum}>{i + 1}</Text>
            </View>
          </Marker>
        ))}
      </MapView>

      {/* Legend */}
      <View style={styles.legend}>
        <LegendItem color="#ef4444" dashed label="Original Route (Discarded)" />
        <LegendItem color="#10b981" label="New Optimised Route" />
        {divergenceIdx >= 0 && <LegendItem icon="⚠️" label="Divergence Point" />}
      </View>

      {/* Bottom panel */}
      <ScrollView style={styles.panel} nestedScrollEnabled>
        {/* Severity banner */}
        <View style={[styles.severityBanner, { backgroundColor: sevColor + '20', borderColor: sevColor }]}>
          <Text style={[styles.severityText, { color: sevColor }]}>
            🚨  SEVERITY: {severity}
          </Text>
        </View>

        {/* Condition change */}
        <View style={styles.condCard}>
          <Text style={styles.condTitle}>Condition Change Detected</Text>
          <View style={styles.condRow}>
            <CondChange icon={wIcon(oldConditions?.weather)} label="Weather"
              from={oldConditions?.weather} to={newConditions?.weather} />
            <CondChange icon={tIcon(oldConditions?.traffic)} label="Traffic"
              from={oldConditions?.traffic} to={newConditions?.traffic} />
          </View>
        </View>

        {/* Impact metrics */}
        <View style={styles.metricsRow}>
          <MetricCard
            label="Time Change"
            value={`${impactAnalysis?.time_change_minutes > 0 ? '+' : ''}${impactAnalysis?.time_change_minutes} min`}
            color={impactAnalysis?.time_change_minutes > 0 ? '#ef4444' : '#10b981'}
          />
          <MetricCard
            label="Distance Change"
            value={`${impactAnalysis?.distance_change_km > 0 ? '+' : ''}${impactAnalysis?.distance_change_km} km`}
            color={impactAnalysis?.distance_change_km > 0 ? '#ef4444' : '#10b981'}
          />
          <MetricCard
            label="Impact %"
            value={`${impactAnalysis?.time_change_pct?.toFixed(1)}%`}
            color={sevColor}
          />
        </View>

        {/* Route comparison */}
        <View style={styles.compareRow}>
          <RouteBox
            title="🔴 Original"
            dist={originalRoute?.total_distance_km}
            time={originalRoute?.total_time_hours}
            color="#ef4444"
          />
          <View style={styles.arrow}><Text style={styles.arrowText}>→</Text></View>
          <RouteBox
            title="🟢 New"
            dist={newRoute?.total_distance_km}
            time={newRoute?.total_time_hours}
            color="#10b981"
          />
        </View>

        <TouchableOpacity
          style={styles.backBtn}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.backBtnText}>↩ Back to Routes</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const LegendItem = ({ color, dashed, icon, label }) => (
  <View style={styles.legendItem}>
    {icon ? (
      <Text style={styles.legendIcon}>{icon}</Text>
    ) : (
      <View style={[styles.legendLine, { backgroundColor: color, borderStyle: dashed ? 'dashed' : 'solid' }]} />
    )}
    <Text style={styles.legendLabel}>{label}</Text>
  </View>
);

const CondChange = ({ icon, label, from, to }) => (
  <View style={styles.condChange}>
    <Text style={styles.condLabel}>{label}</Text>
    <Text style={styles.condValue}>{icon} {from} → {to}</Text>
  </View>
);

const MetricCard = ({ label, value, color }) => (
  <View style={styles.metricCard}>
    <Text style={[styles.metricValue, { color }]}>{value}</Text>
    <Text style={styles.metricLabel}>{label}</Text>
  </View>
);

const RouteBox = ({ title, dist, time, color }) => (
  <View style={[styles.routeBox, { borderColor: color }]}>
    <Text style={[styles.routeTitle, { color }]}>{title}</Text>
    <Text style={styles.routeStat}>📏 {dist} km</Text>
    <Text style={styles.routeStat}>⏱ {((time || 0) * 60).toFixed(0)} min</Text>
  </View>
);

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  depotMarker: { backgroundColor: '#10b981', borderRadius: 16, padding: 5, borderWidth: 2, borderColor: '#fff' },
  divMarker: { backgroundColor: '#fbbf24', borderRadius: 16, padding: 5, borderWidth: 2, borderColor: '#fff' },
  divIcon: { fontSize: 16 },
  stopMarker: { width: 26, height: 26, borderRadius: 13, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: '#fff' },
  urgentM: { backgroundColor: '#ef4444' },
  regularM: { backgroundColor: '#3b82f6' },
  stopNum: { color: '#fff', fontWeight: '800', fontSize: 11 },

  legend: { flexDirection: 'row', justifyContent: 'center', flexWrap: 'wrap', gap: 12, backgroundColor: '#fff', padding: 8, borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendLine: { width: 24, height: 3, borderRadius: 1 },
  legendIcon: { fontSize: 16 },
  legendLabel: { fontSize: 11, color: '#374151', fontWeight: '600' },

  panel: { maxHeight: 320, backgroundColor: '#f8fafc' },
  severityBanner: { margin: 12, borderRadius: 10, padding: 12, borderWidth: 2 },
  severityText: { fontWeight: '800', fontSize: 16, textAlign: 'center' },

  condCard: { backgroundColor: '#fff', marginHorizontal: 12, borderRadius: 10, padding: 12, marginBottom: 10, shadowColor: '#000', shadowOpacity: 0.05, elevation: 2 },
  condTitle: { fontWeight: '700', fontSize: 14, color: '#1e293b', marginBottom: 8 },
  condRow: { flexDirection: 'row', justifyContent: 'space-around' },
  condChange: { alignItems: 'center' },
  condLabel: { fontSize: 11, color: '#9ca3af' },
  condValue: { fontSize: 13, fontWeight: '600', color: '#1e293b' },

  metricsRow: { flexDirection: 'row', marginHorizontal: 12, gap: 8, marginBottom: 10 },
  metricCard: { flex: 1, backgroundColor: '#fff', borderRadius: 10, padding: 10, alignItems: 'center', shadowColor: '#000', shadowOpacity: 0.05, elevation: 2 },
  metricValue: { fontSize: 16, fontWeight: '800' },
  metricLabel: { fontSize: 10, color: '#9ca3af', marginTop: 2 },

  compareRow: { flexDirection: 'row', alignItems: 'center', marginHorizontal: 12, marginBottom: 10 },
  routeBox: { flex: 1, borderWidth: 2, borderRadius: 10, padding: 10, backgroundColor: '#fff' },
  routeTitle: { fontWeight: '700', fontSize: 13, marginBottom: 4 },
  routeStat: { fontSize: 12, color: '#374151' },
  arrow: { paddingHorizontal: 8 },
  arrowText: { fontSize: 20, color: '#9ca3af' },

  backBtn: { margin: 12, backgroundColor: '#374151', borderRadius: 10, paddingVertical: 13, alignItems: 'center' },
  backBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
