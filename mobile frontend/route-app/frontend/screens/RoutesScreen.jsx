// screens/RoutesScreen.jsx
// ─────────────────────────────────────────────────────────────
// Displays the most optimized delivery path based on:
//   • Weather conditions
//   • Traffic conditions
//   • Mail urgency priority
// ─────────────────────────────────────────────────────────────

import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Alert, ActivityIndicator, Animated,
} from 'react-native';
import MapView, { Marker, Polyline, Callout } from 'react-native-maps';
import { changeConditions } from '../utils/api';

const DEFAULT_REGION = {
  latitude: 6.9271, longitude: 79.8612,
  latitudeDelta: 0.08, longitudeDelta: 0.08,
};
const DEPOT = { latitude: 6.9271, longitude: 79.8612 };
const CHECK_INTERVAL = 10;

const WEATHER_ICON  = { clear: '☀️', light_rain: '🌦️', heavy_rain: '🌧️', flooding: '⛈️' };
const TRAFFIC_ICON  = { low: '🟢', moderate: '🟡', high: '🔴', severe: '🔴' };
const WEATHER_SCORE = { clear: 100, light_rain: 75, heavy_rain: 45, flooding: 20 };
const TRAFFIC_SCORE = { low: 100, moderate: 70, high: 40, severe: 15 };
const SEVERITY_COLOR = { MINIMAL:'#10b981', LOW:'#3b82f6', MEDIUM:'#f59e0b', HIGH:'#f97316', CRITICAL:'#ef4444' };

export default function RoutesScreen({ route, navigation }) {
  const { allRoutes, deliveries = [], sessionId, conditions: initCond } = route.params || {};

  const [conditions, setConditions]       = useState(initCond || { weather:'clear', traffic:'moderate' });
  const [autoMonitor, setAutoMonitor]     = useState(false);
  const [countdown, setCountdown]         = useState(CHECK_INTERVAL);
  const [prevCond, setPrevCond]           = useState(null);
  const [rerouteAlert, setRerouteAlert]   = useState(null);
  const [loading, setLoading]             = useState(false);
  const [routeOrder, setRouteOrder]       = useState(null); // live optimized order

  const monitorRef = useRef(null);
  const countRef   = useRef(null);
  const fadeAnim   = useRef(new Animated.Value(0)).current;

  // ── Compute best route result ──────────────────────────
  const bestResult = allRoutes?.results?.[allRoutes?.best_method];

  // Build ordered deliveries from best result
  const orderedDeliveries = React.useMemo(() => {
    const src = routeOrder || bestResult?.deliveries;
    if (!src) return deliveries;
    return src.filter(d => d.id !== undefined && d.latitude);
  }, [routeOrder, bestResult, deliveries]);

  // Route polyline
  const routeCoords = orderedDeliveries.map(d => ({
    latitude: d.latitude, longitude: d.longitude,
  }));

  // Map region
  const region = React.useMemo(() => {
    if (!deliveries.length) return DEFAULT_REGION;
    const lats = deliveries.map(d => d.latitude);
    const lngs = deliveries.map(d => d.longitude);
    return {
      latitude:  (Math.min(...lats) + Math.max(...lats)) / 2,
      longitude: (Math.min(...lngs) + Math.max(...lngs)) / 2,
      latitudeDelta:  (Math.max(...lats) - Math.min(...lats)) * 1.5 + 0.03,
      longitudeDelta: (Math.max(...lngs) - Math.min(...lngs)) * 1.5 + 0.03,
    };
  }, [deliveries]);

  // ── Optimization score (0-100) ─────────────────────────
  const urgentCount   = deliveries.filter(d => d.priority === 'urgent').length;
  const urgencyScore  = urgentCount > 0
    ? Math.round((bestResult?.urgent_on_time / urgentCount) * 100) || 0
    : 100;
  const weatherScore  = WEATHER_SCORE[conditions.weather] || 75;
  const trafficScore  = TRAFFIC_SCORE[conditions.traffic] || 70;
  const overallScore  = Math.round((urgencyScore * 0.4) + (weatherScore * 0.3) + (trafficScore * 0.3));

  const scoreColor = overallScore >= 80 ? '#10b981'
    : overallScore >= 60 ? '#f59e0b'
    : '#ef4444';

  // ── Auto-monitoring ────────────────────────────────────
  useEffect(() => {
    if (!autoMonitor) {
      clearInterval(monitorRef.current);
      clearInterval(countRef.current);
      setCountdown(CHECK_INTERVAL);
      return;
    }

    const WEATHERS = ['clear','light_rain','heavy_rain'];
    const TRAFFICS = ['low','moderate','high'];

    const check = async () => {
      const newCond = {
        weather: WEATHERS[Math.floor(Math.random() * WEATHERS.length)],
        traffic: TRAFFICS[Math.floor(Math.random() * TRAFFICS.length)],
      };
      setConditions(newCond);
      if (prevCond && (newCond.weather !== prevCond.weather || newCond.traffic !== prevCond.traffic)) {
        await performReroute(prevCond, newCond);
      }
      setPrevCond(newCond);
    };

    check();
    monitorRef.current = setInterval(check, CHECK_INTERVAL * 1000);
    countRef.current   = setInterval(() => setCountdown(c => c <= 1 ? CHECK_INTERVAL : c - 1), 1000);
    return () => { clearInterval(monitorRef.current); clearInterval(countRef.current); };
  }, [autoMonitor]);

  const performReroute = async (oldCond, newCond) => {
    setLoading(true);
    try {
      const result = await changeConditions({
        zone_id: 1, session_id: sessionId,
        deliveries: deliveries.map(d => ({
          address: d.address, latitude: d.latitude, longitude: d.longitude,
          mail_type: d.mail_type || 'Regular Letter',
          priority: d.priority || 'regular',
          parcels: d.parcels || 1,
          urgent: d.urgent || (d.priority === 'urgent' ? 1 : 0),
        })),
        original_traffic: oldCond.traffic, original_weather: oldCond.weather,
        new_traffic: newCond.traffic,       new_weather: newCond.weather,
      });

      const pct = Math.abs(result.impact_analysis.time_change_pct);
      if (pct > 10) {
        setRouteOrder(result.new_route?.deliveries);
        setRerouteAlert({ ...result, timestamp: new Date() });
        Animated.timing(fadeAnim, { toValue:1, duration:400, useNativeDriver:true }).start();
        setTimeout(() => {
          Animated.timing(fadeAnim, { toValue:0, duration:400, useNativeDriver:true }).start(() => setRerouteAlert(null));
        }, 10000);
        navigation.navigate('AutoRerouting', {
          originalRoute: result.original_route, newRoute: result.new_route,
          impactAnalysis: result.impact_analysis,
          oldConditions: oldCond, newConditions: newCond,
          deliveries, sessionId,
        });
      }
    } catch (e) { console.warn('Reroute failed:', e.message); }
    finally { setLoading(false); }
  };

  // ── Route color based on conditions ───────────────────
  const routeColor = conditions.weather === 'heavy_rain' || conditions.traffic === 'high'
    ? '#f97316'
    : overallScore >= 75 ? '#10b981' : '#f59e0b';

  return (
    <View style={styles.container}>

      {/* ── MAP ─────────────────────────────────────────── */}
      <MapView style={styles.map} initialRegion={region}>

        {/* Depot */}
        <Marker coordinate={DEPOT} title="📮 Postal Depot (Start/End)">
          <View style={styles.depotMarker}><Text style={styles.depotIcon}>🏢</Text></View>
        </Marker>

        {/* Delivery stops — ordered by optimization */}
        {orderedDeliveries.map((d, i) => {
          const isUrgent = d.priority === 'urgent';
          return (
            <Marker key={i} coordinate={{ latitude: d.latitude, longitude: d.longitude }}>
              <View style={[styles.stopMarker, isUrgent ? styles.urgentM : styles.regularM]}>
                <Text style={styles.stopNum}>{i + 1}</Text>
              </View>
              <Callout>
                <View style={styles.callout}>
                  <Text style={styles.calloutSeq}>Stop #{i + 1}</Text>
                  <Text style={styles.calloutAddr}>{d.address}</Text>
                  <Text style={styles.calloutType}>{d.mail_type || 'Regular Letter'}</Text>
                  <View style={[styles.calloutBadge, { backgroundColor: isUrgent ? '#fee2e2' : '#dcfce7' }]}>
                    <Text style={[styles.calloutPriority, { color: isUrgent ? '#ef4444' : '#10b981' }]}>
                      {isUrgent ? '🚨 URGENT' : '✅ REGULAR'}
                    </Text>
                  </View>
                </View>
              </Callout>
            </Marker>
          );
        })}

        {/* Optimized route polyline */}
        {routeCoords.length > 1 && (
          <Polyline
            coordinates={[DEPOT, ...routeCoords, DEPOT]}
            strokeColor={routeColor}
            strokeWidth={5}
          />
        )}

        {/* Urgent stops highlighted with outer ring */}
        {orderedDeliveries.filter(d => d.priority === 'urgent').map((d, i) => (
          <Marker key={`urg-${i}`} coordinate={{ latitude: d.latitude, longitude: d.longitude }} anchor={{ x:0.5, y:0.5 }}>
            <View style={styles.urgentRing} />
          </Marker>
        ))}
      </MapView>

      {/* ── OPTIMIZATION SCORE BADGE ────────────────────── */}
      <View style={[styles.scoreBadge, { backgroundColor: scoreColor }]}>
        <Text style={styles.scoreValue}>{overallScore}</Text>
        <Text style={styles.scoreLabel}>OPT{'\n'}SCORE</Text>
      </View>

      {/* ── BOTTOM PANEL ────────────────────────────────── */}
      <View style={styles.panel}>

        {/* Optimization title */}
        <View style={styles.titleRow}>
          <Text style={styles.panelTitle}>🏆 Optimized Route — {allRoutes?.best_method?.replace('_',' ').toUpperCase()}</Text>
        </View>

        {/* 3 Factor bars */}
        <View style={styles.factorsRow}>
          <FactorBar
            icon={WEATHER_ICON[conditions.weather] || '🌤️'}
            label="Weather"
            value={conditions.weather.replace('_',' ')}
            score={weatherScore}
            color={weatherScore >= 75 ? '#10b981' : weatherScore >= 50 ? '#f59e0b' : '#ef4444'}
          />
          <FactorBar
            icon={TRAFFIC_ICON[conditions.traffic] || '🟡'}
            label="Traffic"
            value={conditions.traffic}
            score={trafficScore}
            color={trafficScore >= 75 ? '#10b981' : trafficScore >= 50 ? '#f59e0b' : '#ef4444'}
          />
          <FactorBar
            icon="🚨"
            label="Urgency"
            value={`${urgentCount} urgent`}
            score={urgencyScore}
            color={urgencyScore >= 80 ? '#10b981' : '#f59e0b'}
          />
        </View>

        {/* Route stats */}
        <View style={styles.statsRow}>
          <StatBox icon="📏" label="Distance"  value={`${bestResult?.total_distance_km ?? '--'} km`} />
          <StatBox icon="⏱️" label="Est. Time"  value={`${bestResult ? (bestResult.total_time_hours * 60).toFixed(0) : '--'} min`} />
          <StatBox icon="📦" label="Total Stops" value={deliveries.length} />
          <StatBox icon="🚨" label="Urgent"     value={urgentCount} color="#ef4444" />
        </View>

        {/* Optimization explanation */}
        <View style={[styles.explainBox, { borderLeftColor: scoreColor }]}>
          <Text style={styles.explainTitle}>🧠 Why this route?</Text>
          <Text style={styles.explainText}>
            {urgentCount > 0
              ? `• ${urgentCount} urgent item${urgentCount > 1 ? 's' : ''} prioritized first in sequence\n`
              : '• No urgent items — pure distance optimization\n'}
            {`• ${conditions.weather.replace('_',' ')} weather → ${weatherScore}% efficiency\n`}
            {`• ${conditions.traffic} traffic → ${trafficScore}% road speed\n`}
            {`• Best algorithm: ${allRoutes?.best_method?.replace(/_/g,' ')} selected from 4 methods`}
          </Text>
        </View>

        {/* Improvement vs baseline */}
        {allRoutes && (() => {
          const base = allRoutes.results?.nearest_neighbor;
          const opt  = allRoutes.results?.[allRoutes.best_method];
          if (!base || !opt) return null;
          const saved = (base.total_distance_km - opt.total_distance_km).toFixed(2);
          const pct   = ((saved / base.total_distance_km) * 100).toFixed(1);
          return (
            <View style={styles.improvementBox}>
              <Text style={styles.improvementText}>
                💚 Saves {saved} km ({pct}%) vs unoptimized baseline
              </Text>
            </View>
          );
        })()}

        {/* Action buttons */}
        <View style={styles.btnRow}>
          <TouchableOpacity
            style={[styles.monitorBtn, autoMonitor && styles.monitorBtnActive]}
            onPress={() => { setAutoMonitor(v => !v); setPrevCond(null); }}
          >
            {autoMonitor ? (
              <View style={styles.row}>
                <ActivityIndicator color="#fff" size="small" />
                <Text style={styles.btnText}>  LIVE ({countdown}s)</Text>
              </View>
            ) : (
              <Text style={styles.btnText}>📡  Auto-Monitor</Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.relocBtn}
            onPress={() => navigation.navigate('Relocation', { deliveries, allRoutes, sessionId })}
          >
            <Text style={styles.btnText}>📍  Relocate</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* ── REROUTING ALERT ─────────────────────────────── */}
      {rerouteAlert && (
        <Animated.View style={[styles.alertOverlay, { opacity: fadeAnim }]}>
          <View style={[styles.alertBox, { borderColor: SEVERITY_COLOR[rerouteAlert.impact_analysis?.severity] || '#f59e0b' }]}>
            <Text style={styles.alertTitle}>🚨 Route Updated!</Text>
            <Text style={styles.alertSub}>
              Conditions changed → new optimized path applied{'\n'}
              Impact: {rerouteAlert.impact_analysis?.time_change_minutes} min | {rerouteAlert.impact_analysis?.severity}
            </Text>
            <TouchableOpacity onPress={() => setRerouteAlert(null)}>
              <Text style={styles.alertClose}>✕ Dismiss</Text>
            </TouchableOpacity>
          </View>
        </Animated.View>
      )}

      {loading && (
        <View style={styles.loadingOverlay}>
          <ActivityIndicator color="#fff" size="large" />
          <Text style={styles.loadingText}>Re-optimizing route…</Text>
        </View>
      )}
    </View>
  );
}

// ── Sub-components ─────────────────────────────────────────

const FactorBar = ({ icon, label, value, score, color }) => (
  <View style={styles.factorCard}>
    <Text style={styles.factorIcon}>{icon}</Text>
    <Text style={styles.factorLabel}>{label}</Text>
    <Text style={styles.factorValue} numberOfLines={1}>{value}</Text>
    <View style={styles.barBg}>
      <View style={[styles.barFill, { width: `${score}%`, backgroundColor: color }]} />
    </View>
    <Text style={[styles.factorScore, { color }]}>{score}%</Text>
  </View>
);

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

  // Markers
  depotMarker: { backgroundColor:'#10b981', borderRadius:20, padding:7, borderWidth:2.5, borderColor:'#fff',
    shadowColor:'#000', shadowOpacity:0.3, shadowRadius:4, elevation:5 },
  depotIcon: { fontSize:18 },
  stopMarker: { width:32, height:32, borderRadius:16, justifyContent:'center', alignItems:'center', borderWidth:2.5, borderColor:'#fff',
    shadowColor:'#000', shadowOpacity:0.3, shadowRadius:3, elevation:4 },
  urgentM: { backgroundColor:'#ef4444' },
  regularM: { backgroundColor:'#3b82f6' },
  stopNum: { color:'#fff', fontWeight:'800', fontSize:13 },
  urgentRing: { width:46, height:46, borderRadius:23, borderWidth:3, borderColor:'#ef4444', opacity:0.4 },

  // Callout
  callout: { width:180, padding:10 },
  calloutSeq: { fontSize:11, color:'#9ca3af', fontWeight:'600' },
  calloutAddr: { fontSize:13, fontWeight:'700', color:'#1e293b', marginTop:2 },
  calloutType: { fontSize:11, color:'#64748b', marginTop:2 },
  calloutBadge: { borderRadius:6, paddingHorizontal:6, paddingVertical:3, marginTop:4, alignSelf:'flex-start' },
  calloutPriority: { fontSize:11, fontWeight:'700' },

  // Score badge
  scoreBadge: {
    position:'absolute', top:12, right:12,
    borderRadius:14, padding:10, alignItems:'center',
    shadowColor:'#000', shadowOpacity:0.3, shadowRadius:6, elevation:8,
    minWidth:60,
  },
  scoreValue: { fontSize:24, fontWeight:'900', color:'#fff' },
  scoreLabel: { fontSize:9, color:'rgba(255,255,255,0.9)', fontWeight:'700', textAlign:'center', lineHeight:12 },

  // Panel
  panel: { backgroundColor:'#fff', paddingTop:10, paddingBottom:8, paddingHorizontal:12,
    shadowColor:'#000', shadowOpacity:0.15, shadowRadius:12, elevation:10 },
  titleRow: { marginBottom:8 },
  panelTitle: { fontSize:14, fontWeight:'800', color:'#1e293b' },

  // Factor bars
  factorsRow: { flexDirection:'row', gap:8, marginBottom:10 },
  factorCard: { flex:1, backgroundColor:'#f8fafc', borderRadius:10, padding:8, alignItems:'center', borderWidth:1, borderColor:'#e5e7eb' },
  factorIcon: { fontSize:18, marginBottom:2 },
  factorLabel: { fontSize:10, color:'#9ca3af', fontWeight:'600' },
  factorValue: { fontSize:11, color:'#374151', fontWeight:'700', marginTop:1, textAlign:'center' },
  barBg: { width:'100%', height:5, backgroundColor:'#e5e7eb', borderRadius:3, marginTop:5, overflow:'hidden' },
  barFill: { height:'100%', borderRadius:3 },
  factorScore: { fontSize:12, fontWeight:'800', marginTop:3 },

  // Stats
  statsRow: { flexDirection:'row', justifyContent:'space-around', backgroundColor:'#f8fafc',
    borderRadius:10, paddingVertical:8, marginBottom:8, borderWidth:1, borderColor:'#e5e7eb' },
  statBox: { alignItems:'center', paddingHorizontal:4 },
  statIcon: { fontSize:15 },
  statValue: { fontSize:14, fontWeight:'800', color:'#1e293b' },
  statLabel: { fontSize:9, color:'#9ca3af', marginTop:1 },

  // Explanation
  explainBox: { backgroundColor:'#f0fdf4', borderRadius:8, padding:10, borderLeftWidth:4, marginBottom:8 },
  explainTitle: { fontSize:12, fontWeight:'700', color:'#1e293b', marginBottom:4 },
  explainText: { fontSize:11, color:'#374151', lineHeight:18 },

  // Improvement
  improvementBox: { backgroundColor:'#dcfce7', borderRadius:8, padding:8, marginBottom:8, alignItems:'center' },
  improvementText: { fontSize:12, color:'#065f46', fontWeight:'700' },

  // Buttons
  btnRow: { flexDirection:'row', gap:10 },
  monitorBtn: { flex:1, backgroundColor:'#374151', borderRadius:10, paddingVertical:11, alignItems:'center' },
  monitorBtnActive: { backgroundColor:'#16a34a' },
  relocBtn: { flex:1, backgroundColor:'#f59e0b', borderRadius:10, paddingVertical:11, alignItems:'center' },
  btnText: { color:'#fff', fontWeight:'700', fontSize:13 },
  row: { flexDirection:'row', alignItems:'center' },

  // Alert
  alertOverlay: { position:'absolute', top:12, left:12, right:12 },
  alertBox: { backgroundColor:'#fff', borderRadius:12, padding:14, borderWidth:2,
    shadowColor:'#000', shadowOpacity:0.2, shadowRadius:10, elevation:8 },
  alertTitle: { fontSize:15, fontWeight:'800', color:'#1e293b' },
  alertSub: { fontSize:12, color:'#64748b', marginTop:4, lineHeight:18 },
  alertClose: { marginTop:8, color:'#ef4444', fontWeight:'700' },

  // Loading overlay
  loadingOverlay: { position:'absolute', top:0, left:0, right:0, bottom:0,
    backgroundColor:'rgba(0,0,0,0.5)', justifyContent:'center', alignItems:'center' },
  loadingText: { color:'#fff', marginTop:12, fontSize:15, fontWeight:'700' },
});
