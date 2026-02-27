// screens/RelocationScreen.jsx
import React, { useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  TextInput, ActivityIndicator, Alert,
} from 'react-native';
import MapView, { Marker, Polyline } from 'react-native-maps';
import { optimizeRoute, saveRelocation } from '../utils/api';

const DEPOT = { latitude: 6.9271, longitude: 79.8612 };

export default function RelocationScreen({ route, navigation }) {
  const { deliveries = [], allRoutes, sessionId } = route.params || {};

  const [selectedId, setSelectedId] = useState(null);
  const [newAddress, setNewAddress] = useState('');
  const [newLat, setNewLat] = useState('');
  const [newLng, setNewLng] = useState('');
  const [geocoding, setGeocoding] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null); // { before, after, relocationData }

  const selectedDelivery = deliveries.find((d) => d.id === selectedId || d.id === Number(selectedId));

  // ── Geocode address ───────────────────────────────────
  const geocodeAddress = async () => {
    if (!newAddress) return;
    setGeocoding(true);
    try {
      await new Promise((r) => setTimeout(r, 800));
      const url =
        `https://nominatim.openstreetmap.org/search?format=json` +
        `&q=${encodeURIComponent(newAddress + ', Sri Lanka')}&limit=1`;
      const res = await fetch(url, { headers: { 'User-Agent': 'PostalRouteApp/1.0' } });
      const data = await res.json();
      if (data && data.length > 0) {
        setNewLat(data[0].lat);
        setNewLng(data[0].lon);
      } else {
        Alert.alert('Not Found', 'Address not found. Please enter coordinates manually.');
      }
    } catch (e) {
      Alert.alert('Geocoding Error', e.message);
    } finally {
      setGeocoding(false);
    }
  };

  // ── Haversine ─────────────────────────────────────────
  const haversine = (lat1, lon1, lat2, lon2) => {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) ** 2;
    return (R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))).toFixed(3);
  };

  // ── Compare relocation ────────────────────────────────
  const compareRelocation = async () => {
    if (!selectedDelivery || !newLat || !newLng) {
      Alert.alert('Missing Info', 'Select a delivery and provide new coordinates.');
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const updatedDeliveries = deliveries.map((d) =>
        d.id === selectedDelivery.id
          ? { ...d, latitude: parseFloat(newLat), longitude: parseFloat(newLng), address: newAddress || d.address }
          : d
      );

      const payload = {
        zone_id: 1,
        session_id: sessionId,
        deliveries: updatedDeliveries.map((d) => ({
          address: d.address,
          latitude: d.latitude,
          longitude: d.longitude,
          mail_type: d.mail_type || 'Regular Letter',
          priority: d.priority || 'regular',
          parcels: d.parcels || 1,
          urgent: d.urgent || (d.priority === 'urgent' ? 1 : 0),
        })),
        methods: ['nearest_neighbor', 'urgent_priority', '2opt', 'q_learning'],
      };

      const newRoutesResult = await optimizeRoute(payload);
      const distChange = haversine(
        selectedDelivery.latitude, selectedDelivery.longitude,
        parseFloat(newLat), parseFloat(newLng)
      );

      const relData = {
        session_id: sessionId,
        delivery_id: selectedDelivery.id,
        old_address: selectedDelivery.address,
        new_address: newAddress || selectedDelivery.address,
        old_latitude: selectedDelivery.latitude,
        old_longitude: selectedDelivery.longitude,
        new_latitude: parseFloat(newLat),
        new_longitude: parseFloat(newLng),
        distance_change_km: parseFloat(distChange),
        before_route: allRoutes || {},
        after_route: newRoutesResult,
      };

      // Save to DB
      try { await saveRelocation(relData); } catch (_) {}

      setResult({
        before: allRoutes,
        after: newRoutesResult,
        relocationData: relData,
        updatedDeliveries,
      });
    } catch (e) {
      Alert.alert('Error', e.message);
    } finally {
      setLoading(false);
    }
  };

  // ── Map region ────────────────────────────────────────
  const mapRegion = React.useMemo(() => {
    const pts = deliveries;
    if (!pts.length) return { ...DEPOT, latitudeDelta: 0.1, longitudeDelta: 0.1 };
    const lats = pts.map((d) => d.latitude);
    const lngs = pts.map((d) => d.longitude);
    return {
      latitude: (Math.min(...lats) + Math.max(...lats)) / 2,
      longitude: (Math.min(...lngs) + Math.max(...lngs)) / 2,
      latitudeDelta: (Math.max(...lats) - Math.min(...lats)) * 1.5 + 0.03,
      longitudeDelta: (Math.max(...lngs) - Math.min(...lngs)) * 1.5 + 0.03,
    };
  }, [deliveries]);

  const beforeCoords = result?.before?.results?.[result.before.best_method]?.deliveries?.map((d) => ({
    latitude: d.latitude, longitude: d.longitude,
  })) || [];

  const afterCoords = result?.after?.results?.[result.after.best_method]?.deliveries?.map((d) => ({
    latitude: d.latitude, longitude: d.longitude,
  })) || [];

  return (
    <View style={styles.container}>
      {/* Map */}
      <MapView style={styles.map} initialRegion={mapRegion}>
        <Marker coordinate={DEPOT} title="Depot">
          <View style={styles.depotM}><Text>🏢</Text></View>
        </Marker>

        {/* Original deliveries */}
        {deliveries.map((d, i) => (
          <Marker
            key={i}
            coordinate={{ latitude: d.latitude, longitude: d.longitude }}
            pinColor={d.id === selectedDelivery?.id ? '#f97316' : (d.priority === 'urgent' ? '#ef4444' : '#3b82f6')}
            title={d.address}
          />
        ))}

        {/* New position if typed */}
        {newLat && newLng && (
          <Marker
            coordinate={{ latitude: parseFloat(newLat), longitude: parseFloat(newLng) }}
            pinColor="#f97316"
            title={`New: ${newAddress || 'New Location'}`}
          />
        )}

        {/* Before route (blue dashed) */}
        {result && beforeCoords.length > 1 && (
          <Polyline coordinates={beforeCoords} strokeColor="#3b82f6" strokeWidth={3} lineDashPattern={[8, 5]} />
        )}

        {/* After route (green solid) */}
        {result && afterCoords.length > 1 && (
          <Polyline coordinates={afterCoords} strokeColor="#10b981" strokeWidth={4} />
        )}
      </MapView>

      {/* Legend when result is shown */}
      {result && (
        <View style={styles.legend}>
          <LegendItem color="#3b82f6" dashed label="Before Relocation" />
          <LegendItem color="#10b981" label="After Relocation" />
          <LegendItem icon="🟠" label="Moved Location" />
        </View>
      )}

      {/* Panel */}
      <ScrollView style={styles.panel} nestedScrollEnabled>
        <Text style={styles.panelTitle}>📍 Customer Relocation Tool</Text>

        {/* Delivery selector */}
        <Text style={styles.label}>Select Delivery</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.deliveryScroll}>
          {deliveries.map((d) => (
            <TouchableOpacity
              key={d.id}
              style={[styles.deliveryChip, selectedId === d.id && styles.deliveryChipActive]}
              onPress={() => setSelectedId(d.id)}
            >
              <Text style={[styles.deliveryChipText, selectedId === d.id && styles.deliveryChipTextActive]} numberOfLines={1}>
                #{d.id} {d.address.substring(0, 20)}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {selectedDelivery && (
          <View style={styles.currentInfo}>
            <Text style={styles.currentLabel}>Current: {selectedDelivery.address}</Text>
            <Text style={styles.currentCoords}>
              📍 {selectedDelivery.latitude.toFixed(5)}, {selectedDelivery.longitude.toFixed(5)}
            </Text>
          </View>
        )}

        {/* New address input */}
        <Text style={styles.label}>New Address</Text>
        <View style={styles.row}>
          <TextInput
            style={[styles.input, { flex: 1 }]}
            placeholder="e.g., Galle Road, Colombo 03"
            value={newAddress}
            onChangeText={setNewAddress}
          />
          <TouchableOpacity style={styles.geocodeBtn} onPress={geocodeAddress} disabled={geocoding}>
            {geocoding ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.geocodeBtnText}>📍</Text>}
          </TouchableOpacity>
        </View>

        <View style={styles.row}>
          <TextInput
            style={[styles.input, { flex: 1, marginRight: 8 }]}
            placeholder="Latitude"
            value={newLat}
            onChangeText={setNewLat}
            keyboardType="decimal-pad"
          />
          <TextInput
            style={[styles.input, { flex: 1 }]}
            placeholder="Longitude"
            value={newLng}
            onChangeText={setNewLng}
            keyboardType="decimal-pad"
          />
        </View>

        <TouchableOpacity
          style={[styles.compareBtn, loading && styles.disabled]}
          onPress={compareRelocation}
          disabled={loading}
        >
          {loading ? (
            <View style={styles.row}>
              <ActivityIndicator color="#fff" size="small" />
              <Text style={styles.compareBtnText}> Comparing…</Text>
            </View>
          ) : (
            <Text style={styles.compareBtnText}>⚖️  Compare Impact</Text>
          )}
        </TouchableOpacity>

        {/* Result comparison */}
        {result && (
          <View style={styles.resultCard}>
            <Text style={styles.resultTitle}>📊 Relocation Impact</Text>
            <View style={styles.resultInfo}>
              <Text style={styles.resultItem}>📍 Moved: {result.relocationData.distance_change_km} km</Text>
            </View>
            <View style={styles.compareRow}>
              <RouteCard
                title="🔵 Before"
                dist={result.before.results?.[result.before.best_method]?.total_distance_km}
                time={result.before.results?.[result.before.best_method]?.total_time_hours}
                color="#3b82f6"
              />
              <View style={styles.arrow}><Text style={styles.arrowTxt}>→</Text></View>
              <RouteCard
                title="🟢 After"
                dist={result.after.results?.[result.after.best_method]?.total_distance_km}
                time={result.after.results?.[result.after.best_method]?.total_time_hours}
                color="#10b981"
              />
            </View>
          </View>
        )}

        {/* Back button */}
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>↩ Back to Routes</Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const LegendItem = ({ color, dashed, icon, label }) => (
  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5 }}>
    {icon ? <Text>{icon}</Text> : <View style={{ width: 20, height: 3, backgroundColor: color, borderRadius: 1 }} />}
    <Text style={{ fontSize: 11, color: '#374151', fontWeight: '600' }}>{label}</Text>
  </View>
);

const RouteCard = ({ title, dist, time, color }) => (
  <View style={[styles.routeCard, { borderColor: color }]}>
    <Text style={[styles.routeCardTitle, { color }]}>{title}</Text>
    <Text style={styles.routeCardStat}>📏 {dist} km</Text>
    <Text style={styles.routeCardStat}>⏱ {((time || 0) * 60).toFixed(0)} min</Text>
  </View>
);

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  depotM: { backgroundColor: '#10b981', borderRadius: 14, padding: 4, borderWidth: 2, borderColor: '#fff' },
  legend: { flexDirection: 'row', justifyContent: 'center', gap: 12, padding: 8, backgroundColor: '#fff', borderBottomWidth: 1, borderBottomColor: '#e5e7eb' },
  panel: { maxHeight: 400, backgroundColor: '#f8fafc', padding: 14 },
  panelTitle: { fontSize: 17, fontWeight: '800', color: '#1e293b', marginBottom: 12 },
  label: { fontSize: 13, fontWeight: '600', color: '#374151', marginBottom: 6 },
  deliveryScroll: { marginBottom: 10 },
  deliveryChip: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 6, marginRight: 8, backgroundColor: '#fff' },
  deliveryChipActive: { backgroundColor: '#2563eb', borderColor: '#2563eb' },
  deliveryChipText: { fontSize: 12, color: '#374151', maxWidth: 120 },
  deliveryChipTextActive: { color: '#fff' },
  currentInfo: { backgroundColor: '#fff', borderRadius: 8, padding: 10, marginBottom: 10, borderWidth: 1, borderColor: '#e5e7eb' },
  currentLabel: { fontSize: 13, fontWeight: '600', color: '#1e293b' },
  currentCoords: { fontSize: 11, color: '#9ca3af', marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'center', marginBottom: 10 },
  input: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, paddingHorizontal: 12, paddingVertical: 9, fontSize: 13 },
  geocodeBtn: { backgroundColor: '#2563eb', borderRadius: 8, padding: 10, marginLeft: 8 },
  geocodeBtnText: { fontSize: 18 },
  compareBtn: { backgroundColor: '#7c3aed', borderRadius: 10, paddingVertical: 13, alignItems: 'center', marginBottom: 14 },
  compareBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  disabled: { opacity: 0.6 },
  resultCard: { backgroundColor: '#fff', borderRadius: 12, padding: 14, marginBottom: 12, borderWidth: 1, borderColor: '#e5e7eb' },
  resultTitle: { fontSize: 15, fontWeight: '700', marginBottom: 8, color: '#1e293b' },
  resultInfo: { marginBottom: 8 },
  resultItem: { fontSize: 13, color: '#374151' },
  compareRow: { flexDirection: 'row', alignItems: 'center' },
  routeCard: { flex: 1, borderWidth: 2, borderRadius: 8, padding: 10 },
  routeCardTitle: { fontWeight: '700', fontSize: 12, marginBottom: 4 },
  routeCardStat: { fontSize: 11, color: '#374151' },
  arrow: { paddingHorizontal: 8 },
  arrowTxt: { fontSize: 20, color: '#9ca3af' },
  backBtn: { backgroundColor: '#374151', borderRadius: 10, paddingVertical: 13, alignItems: 'center', marginBottom: 20 },
  backBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
});
