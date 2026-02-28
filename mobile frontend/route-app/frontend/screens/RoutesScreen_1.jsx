// screens/RoutesScreen.jsx
import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Alert, ActivityIndicator, Animated,
} from 'react-native';
import MapView, { Marker, Polyline, Callout } from 'react-native-maps';
import { changeConditions, optimizeRoute } from '../utils/api';

const DEFAULT_REGION = {
  latitude: 6.9271, longitude: 79.8612,
  latitudeDelta: 0.08, longitudeDelta: 0.08,
};
const CHECK_INTERVAL = 10; // seconds

const WEATHER_STATES = ['clear', 'light_rain', 'heavy_rain'];
const TRAFFIC_STATES = ['low', 'moderate', 'high'];

export default function RoutesScreen({ route, navigation }) {
  const { allRoutes, deliveries, sessionId, conditions: initConditions } = route.params || {};

  const [selectedMethod, setSelectedMethod] = useState(allRoutes?.best_method || 'q_learning');
  const [autoMonitor, setAutoMonitor] = useState(false);
  const [countdown, setCountdown] = useState(CHECK_INTERVAL);
  const [currentConditions, setCurrentConditions] = useState(initConditions || { weather: 'clear', traffic: 'moderate' });
  const [prevConditions, setPrevConditions] = useState(null);
  const [rerouteAlert, setRerouteAlert] = useState(null);
  const [loading, setLoading] = useState(false);

  const monitorRef = useRef(null);
  const countRef   = useRef(null);
  const fadeAnim   = useRef(new Animated.Value(0)).current;

  const bestResult = allRoutes?.results?.[selectedMethod];
  const depotCoord = { latitude: DEFAULT_REGION.latitude, longitude: DEFAULT_REGION.longitude };

  // ── Route path for polyline ────────────────────────────
  const routeCoords =
    bestResult?.deliveries?.map((d) => ({
      latitude: d.latitude,
      longitude: d.longitude,
    })) || [];

  // ── Map region to fit all markers ──────────────────────
  const region = React.useMemo(() => {
    if (!deliveries || deliveries.length === 0) return DEFAULT_REGION;
    const lats = deliveries.map((d) => d.latitude);
    const lngs = deliveries.map((d) => d.longitude);
    const minLat = Math.min(...lats), maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs), maxLng = Math.max(...lngs);
    return {
      latitude: (minLat + maxLat) / 2,
      longitude: (minLng + maxLng) / 2,
      latitudeDelta: (maxLat - minLat) * 1.4 + 0.02,
      longitudeDelta: (maxLng - minLng) * 1.4 + 0.02,
    };
  }, [deliveries]);

  // ── Auto-monitoring logic ─────────────────────────────
  useEffect(() => {
    if (!autoMonitor) {
      clearInterval(monitorRef.current);
      clearInterval(countRef.current);
      setCountdown(CHECK_INTERVAL);
      return;
    }

    const checkAndReroute = async () => {
      const weathers = WEATHER_STATES;
      const traffics = TRAFFIC_STATES;
      const newCond = {
        weather: weathers[Math.floor(Math.random() * weathers.length)],
        traffic: traffics[Math.floor(Math.random() * traffics.length)],
      };
      setCurrentConditions(newCond);

      if (prevConditions &&
          (newCond.weather !== prevConditions.weather ||
           newCond.traffic !== prevConditions.traffic)) {
        await performReroute(prevConditions, newCond);
      }
      setPrevConditions(newCond);
    };

    checkAndReroute();
    monitorRef.current = setInterval(checkAndReroute, CHECK_INTERVAL * 1000);
    countRef.current = setInterval(() => setCountdown((c) => (c <= 1 ? CHECK_INTERVAL : c - 1)), 1000);

    return () => {
      clearInterval(monitorRef.current);
      clearInterval(countRef.current);
    };
  }, [autoMonitor]);

  const performReroute = async (oldCond, newCond) => {
    setLoading(true);
    try {
      const result = await changeConditions({
        zone_id: 1,
        session_id: sessionId,
        deliveries: deliveries.map((d) => ({
          address: d.address,
          latitude: d.latitude,
          longitude: d.longitude,
          mail_type: d.mail_type || 'Regular Letter',
          priority: d.priority || 'regular',
          parcels: d.parcels || 1,
          urgent: d.urgent || (d.priority === 'urgent' ? 1 : 0),
        })),
        original_traffic: oldCond.traffic,
        original_weather: oldCond.weather,
        new_traffic: newCond.traffic,
        new_weather: newCond.weather,
      });

      const pct = Math.abs(result.impact_analysis.time_change_pct);
      if (pct > 10) {
        setRerouteAlert({ ...result, timestamp: new Date() });
        // Fade in alert
        Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }).start();
        setTimeout(() => {
          Animated.timing(fadeAnim, { toValue: 0, duration: 400, useNativeDriver: true }).start(() =>
            setRerouteAlert(null)
          );
        }, 10000);

        navigation.navigate('AutoRerouting', {
          originalRoute: result.original_route,
          newRoute: result.new_route,
          impactAnalysis: result.impact_analysis,
          oldConditions: oldCond,
          newConditions: newCond,
          deliveries,
          sessionId,
        });
      }
    } catch (e) {
      console.warn('Rerouting failed:', e.message);
    } finally {
      setLoading(false);
    }
  };

  const severityColor = (s) =>
    ({ MINIMAL: '#10b981', LOW: '#3b82f6', MEDIUM: '#f59e0b', HIGH: '#f97316', CRITICAL: '#ef4444' }[s] || '#f59e0b');

  const methodLabels = {
    nearest_neighbor: 'Baseline (NN)',
    urgent_priority: 'Urgent Priority',
    '2opt': '2-Opt Search',
    q_learning: 'Q-Learning ⭐',
  };

  return (
    <View style={styles.container}>
      {/* Map */}
      <MapView style={styles.map} initialRegion={region}>
        {/* Depot */}
        <Marker coordinate={depotCoord} title="Postal Depot" pinColor="green">
          <View style={styles.depotMarker}>
            <Text style={styles.depotIcon}>🏢</Text>
          </View>
        </Marker>

        {/* Delivery stops */}
        {deliveries?.map((d, i) => (
          <Marker
            key={d.id || i}
            coordinate={{ latitude: d.latitude, longitude: d.longitude }}
            pinColor={d.priority === 'urgent' ? '#ef4444' : '#3b82f6'}
          >
            <View style={[styles.stopMarker, d.priority === 'urgent' ? styles.urgentMarker : styles.regularMarker]}>
              <Text style={styles.stopNum}>{i + 1}</Text>
            </View>
            <Callout>
              <View style={styles.callout}>
                <Text style={styles.calloutTitle}>{d.address}</Text>
                <Text style={styles.calloutSub}>{d.mail_type}</Text>
                <Text style={[styles.calloutPriority, { color: d.priority === 'urgent' ? '#ef4444' : '#10b981' }]}>
                  {d.priority?.toUpperCase()}
                </Text>
              </View>
            </Callout>
          </Marker>
        ))}

        {/* Route line */}
        {routeCoords.length > 1 && (
          <Polyline
            coordinates={routeCoords}
            strokeColor={selectedMethod === 'q_learning' ? '#10b981' : '#3b82f6'}
            strokeWidth={4}
            lineDashPattern={selectedMethod === 'nearest_neighbor' ? [10, 5] : undefined}
          />
        )}
      </MapView>

      {/* Panel */}
      <View style={styles.panel}>
        {/* Method selector */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.methodScroll}>
          {Object.entries(methodLabels).map(([key, label]) => {
            const res = allRoutes?.results?.[key];
            return (
              <TouchableOpacity
                key={key}
                style={[styles.methodBtn, selectedMethod === key && styles.methodBtnActive]}
                onPress={() => setSelectedMethod(key)}
              >
                <Text style={[styles.methodBtnLabel, selectedMethod === key && styles.methodBtnLabelActive]}>
                  {label}
                </Text>
                {res && (
                  <Text style={styles.methodBtnDist}>{res.total_distance_km} km</Text>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* Stats row */}
        {bestResult && (
          <View style={styles.statsRow}>
            <StatBox icon="📏" label="Distance" value={`${bestResult.total_distance_km} km`} />
            <StatBox icon="⏱️" label="Est. Time" value={`${(bestResult.total_time_hours * 60).toFixed(0)} min`} />
            <StatBox icon="🚨" label="Urgent ✓" value={`${bestResult.urgent_on_time}`} color="#ef4444" />
            <StatBox icon="🌤" label="Weather" value={currentConditions.weather} />
          </View>
        )}

        {/* Improvement vs baseline */}
        {allRoutes && (
          <View style={styles.improvementRow}>
            {(() => {
              const base = allRoutes.results.nearest_neighbor;
              const opt  = allRoutes.results[allRoutes.best_method];
              const saved = (base.total_distance_km - opt.total_distance_km).toFixed(2);
              const pct   = ((saved / base.total_distance_km) * 100).toFixed(1);
              return (
                <Text style={styles.improvementText}>
                  💚  Best ({allRoutes.best_method}): saves {saved} km ({pct}%) vs baseline
                </Text>
              );
            })()}
          </View>
        )}

        {/* Control row */}
        <View style={styles.controlRow}>
          <TouchableOpacity
            style={[styles.monitorBtn, autoMonitor && styles.monitorBtnActive]}
            onPress={() => { setAutoMonitor((v) => !v); setPrevConditions(null); }}
          >
            {autoMonitor ? (
              <View style={styles.row}>
                <ActivityIndicator color="#fff" size="small" />
                <Text style={styles.monitorBtnText}>  LIVE ({countdown}s)</Text>
              </View>
            ) : (
              <Text style={styles.monitorBtnText}>▶  Start Auto-Monitor</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.relocationBtn}
            onPress={() =>
              navigation.navigate('Relocation', {
                deliveries, allRoutes, sessionId,
              })
            }
          >
            <Text style={styles.relocationBtnText}>📍 Relocate</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Rerouting Alert Overlay */}
      {rerouteAlert && (
        <Animated.View style={[styles.alertOverlay, { opacity: fadeAnim }]}>
          <View style={[styles.alertBox, { borderColor: severityColor(rerouteAlert.impact_analysis?.severity) }]}>
            <Text style={styles.alertTitle}>🚨 Auto-Rerouting Applied!</Text>
            <Text style={styles.alertSub}>
              Time impact: {rerouteAlert.impact_analysis?.time_change_minutes} min |{' '}
              Severity: {rerouteAlert.impact_analysis?.severity}
            </Text>
            <TouchableOpacity onPress={() => setRerouteAlert(null)}>
              <Text style={styles.alertClose}>✕ Dismiss</Text>
            </TouchableOpacity>
          </View>
        </Animated.View>
      )}
    </View>
  );
}

const StatBox = ({ icon, label, value, color = '#1e293b' }) => (
  <View style={styles.statBox}>
    <Text style={styles.statIcon}>{icon}</Text>
    <Text style={[styles.statValue, { color }]}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  depotMarker: { backgroundColor: '#10b981', borderRadius: 20, padding: 6, borderWidth: 2, borderColor: '#fff' },
  depotIcon: { fontSize: 18 },
  stopMarker: { width: 30, height: 30, borderRadius: 15, justifyContent: 'center', alignItems: 'center', borderWidth: 2, borderColor: '#fff' },
  urgentMarker: { backgroundColor: '#ef4444' },
  regularMarker: { backgroundColor: '#3b82f6' },
  stopNum: { color: '#fff', fontWeight: '800', fontSize: 12 },
  callout: { width: 160, padding: 8 },
  calloutTitle: { fontSize: 13, fontWeight: '700', color: '#1e293b' },
  calloutSub: { fontSize: 11, color: '#64748b', marginTop: 2 },
  calloutPriority: { fontSize: 11, fontWeight: '700', marginTop: 2 },

  panel: {
    backgroundColor: '#fff',
    paddingTop: 8,
    paddingBottom: 12,
    shadowColor: '#000',
    shadowOpacity: 0.12,
    shadowRadius: 10,
    elevation: 8,
  },
  methodScroll: { paddingHorizontal: 12, marginBottom: 8 },
  methodBtn: {
    borderWidth: 1, borderColor: '#d1d5db', borderRadius: 10,
    paddingHorizontal: 14, paddingVertical: 8, marginRight: 8,
    backgroundColor: '#f8fafc', alignItems: 'center',
  },
  methodBtnActive: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  methodBtnLabel: { fontSize: 12, fontWeight: '600', color: '#374151' },
  methodBtnLabelActive: { color: '#fff' },
  methodBtnDist: { fontSize: 11, color: '#6b7280', marginTop: 2 },

  statsRow: { flexDirection: 'row', justifyContent: 'space-around', paddingHorizontal: 8 },
  statBox: { alignItems: 'center', padding: 8 },
  statIcon: { fontSize: 16 },
  statValue: { fontSize: 13, fontWeight: '700', color: '#1e293b' },
  statLabel: { fontSize: 10, color: '#9ca3af' },

  improvementRow: { backgroundColor: '#f0fdf4', marginHorizontal: 12, borderRadius: 8, padding: 8, marginBottom: 8 },
  improvementText: { fontSize: 12, color: '#065f46', textAlign: 'center', fontWeight: '600' },

  controlRow: { flexDirection: 'row', paddingHorizontal: 12, gap: 10 },
  monitorBtn: { flex: 1, backgroundColor: '#374151', borderRadius: 10, paddingVertical: 12, alignItems: 'center' },
  monitorBtnActive: { backgroundColor: '#16a34a' },
  monitorBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  relocationBtn: { backgroundColor: '#f59e0b', borderRadius: 10, paddingHorizontal: 18, paddingVertical: 12, alignItems: 'center' },
  relocationBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  row: { flexDirection: 'row', alignItems: 'center' },

  alertOverlay: { position: 'absolute', top: 10, left: 12, right: 12 },
  alertBox: {
    backgroundColor: '#fff', borderRadius: 12, padding: 14,
    borderWidth: 2, shadowColor: '#000', shadowOpacity: 0.2, shadowRadius: 10, elevation: 8,
  },
  alertTitle: { fontSize: 16, fontWeight: '800', color: '#1e293b' },
  alertSub: { fontSize: 13, color: '#64748b', marginTop: 4 },
  alertClose: { marginTop: 8, color: '#ef4444', fontWeight: '700' },
});
