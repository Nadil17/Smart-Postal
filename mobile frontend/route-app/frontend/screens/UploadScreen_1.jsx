// screens/UploadScreen.jsx
import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Alert,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from "expo-file-system/legacy";
import Papa from 'papaparse';
import { classifyPriority, saveDeliveries, newSession } from '../utils/api';

const DEFAULT_CENTER = { lat: 6.9271, lng: 79.8612 };

export default function UploadScreen({ navigation }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState('');
  const [stats, setStats] = useState(null);

  // ── Geocode via Nominatim ──────────────────────────────────
  const geocode = async (address) => {
    await new Promise((r) => setTimeout(r, 800)); // rate-limit
    try {
      const url =
        `https://nominatim.openstreetmap.org/search?format=json` +
        `&q=${encodeURIComponent(address + ', Sri Lanka')}&limit=1`;
      const res = await fetch(url, {
        headers: { 'User-Agent': 'PostalRouteApp/1.0' },
      });
      const data = await res.json();
      if (data && data.length > 0) {
        return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) };
      }
    } catch (_) {}
    // fallback
    return {
      lat: DEFAULT_CENTER.lat + (Math.random() - 0.5) * 0.1,
      lng: DEFAULT_CENTER.lng + (Math.random() - 0.5) * 0.1,
    };
  };

  // ── Pick & process CSV ────────────────────────────────────
  const pickCSV = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['text/csv', 'text/comma-separated-values', '*/*'],
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;

      setLoading(true);
      setStats(null);

      const fileUri = result.assets[0].uri;
      const content = await FileSystem.readAsStringAsync(fileUri);

      Papa.parse(content, {
        header: true,
        skipEmptyLines: true,
        complete: async (parsed) => {
          try {
            await processRows(parsed.data);
          } catch (e) {
            Alert.alert('Error', e.message);
            setLoading(false);
          }
        },
        error: (e) => {
          Alert.alert('Parse Error', e.message);
          setLoading(false);
        },
      });
    } catch (e) {
      Alert.alert('Error', e.message);
      setLoading(false);
    }
  };

  const processRows = async (rows) => {
    const session = (await newSession()).session_id;
    const deliveries = [];
    const total = rows.length;

    for (let i = 0; i < rows.length; i++) {
      const row = rows[i];
      setProgress(`Processing ${i + 1}/${total}…`);

      // ── Geocode if lat/lng missing ──────────────
      let lat = parseFloat(row.latitude || row.lat || '');
      let lng = parseFloat(row.longitude || row.lng || row.lon || '');

      if (isNaN(lat) || isNaN(lng)) {
        const coords = await geocode(row.address || row.Address || '');
        lat = coords.lat;
        lng = coords.lng;
      }

      // ── Priority classification ─────────────────
      let priority = (row.priority || '').toLowerCase();
      if (priority !== 'urgent' && priority !== 'regular') {
        try {
          const cls = await classifyPriority({
            mail_type: row.mail_type || row.type || 'Regular Letter',
            sender_type: row.sender_type || 'Individual',
            recipient_type: row.recipient_type || 'Individual',
            time_received: new Date().toISOString(),
            day_of_week: new Date().toLocaleDateString('en-US', { weekday: 'long' }),
          });
          priority = cls.priority;
        } catch (_) {
          priority = 'regular';
        }
      }

      deliveries.push({
        id: i + 1,
        session_id: session,
        address: row.address || row.Address || `Stop ${i + 1}`,
        latitude: lat,
        longitude: lng,
        mail_type: row.mail_type || row.type || 'Regular Letter',
        priority,
        sender_type: row.sender_type || 'Individual',
        recipient_type: row.recipient_type || 'Individual',
        parcels: parseInt(row.parcels || '1', 10) || 1,
        urgent: priority === 'urgent' ? 1 : 0,
      });
    }

    setProgress('Saving to database…');
    try {
      await saveDeliveries(session, deliveries);
    } catch (e) {
      console.warn('DB save skipped:', e.message);
    }

    const urgentCount = deliveries.filter((d) => d.priority === 'urgent').length;
    setStats({
      total: deliveries.length,
      urgent: urgentCount,
      regular: deliveries.length - urgentCount,
      session,
    });
    setLoading(false);
    setProgress('');

    // Navigate to MailList
    navigation.navigate('MailList', { deliveries, sessionId: session });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🗺️ Postal Route Optimizer</Text>
        <Text style={styles.headerSub}>Sri Lanka Smart Delivery System</Text>
      </View>

      {/* Upload Card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📂 Upload Deliveries CSV</Text>
        <Text style={styles.cardDesc}>
          CSV must include: address, mail_type{'\n'}
          Optional: latitude, longitude, priority
        </Text>

        <TouchableOpacity
          style={[styles.uploadBtn, loading && styles.disabled]}
          onPress={pickCSV}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.uploadBtnText}>📁  Choose CSV File</Text>
          )}
        </TouchableOpacity>

        {!!progress && (
          <View style={styles.progressBox}>
            <ActivityIndicator color="#3b82f6" size="small" />
            <Text style={styles.progressText}>{progress}</Text>
          </View>
        )}
      </View>

      {/* Stats after upload */}
      {stats && (
        <View style={styles.statsCard}>
          <Text style={styles.statsTitle}>✅ Upload Complete</Text>
          <View style={styles.statsRow}>
            <StatBadge label="Total" value={stats.total} color="#3b82f6" />
            <StatBadge label="Urgent" value={stats.urgent} color="#ef4444" />
            <StatBadge label="Regular" value={stats.regular} color="#10b981" />
          </View>
        </View>
      )}

      {/* Sample CSV format */}
      <View style={[styles.card, { backgroundColor: '#f0fdf4' }]}>
        <Text style={styles.cardTitle}>📋 CSV Format Example</Text>
        <Text style={styles.codeText}>
          address,mail_type,sender_type{'\n'}
          "Colombo 07",Court Notice,Court{'\n'}
          "Galle Road",Regular Letter,Individual
        </Text>
      </View>
    </ScrollView>
  );
}

const StatBadge = ({ label, value, color }) => (
  <View style={[styles.statBadge, { borderColor: color }]}>
    <Text style={[styles.statValue, { color }]}>{value}</Text>
    <Text style={styles.statLabel}>{label}</Text>
  </View>
);

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: '#f8fafc', padding: 16 },
  header: {
    backgroundColor: '#1e40af',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
    alignItems: 'center',
  },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#fff' },
  headerSub: { fontSize: 13, color: '#bfdbfe', marginTop: 4 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 18,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardTitle: { fontSize: 16, fontWeight: '700', marginBottom: 8, color: '#1e293b' },
  cardDesc: { fontSize: 13, color: '#64748b', lineHeight: 20, marginBottom: 14 },
  uploadBtn: {
    backgroundColor: '#2563eb',
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
  },
  uploadBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  disabled: { opacity: 0.6 },
  progressBox: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    gap: 8,
  },
  progressText: { color: '#3b82f6', fontSize: 13, marginLeft: 8 },
  statsCard: {
    backgroundColor: '#ecfdf5',
    borderRadius: 14,
    padding: 18,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#6ee7b7',
  },
  statsTitle: { fontSize: 16, fontWeight: '700', marginBottom: 12, color: '#065f46' },
  statsRow: { flexDirection: 'row', justifyContent: 'space-around' },
  statBadge: {
    alignItems: 'center',
    borderWidth: 2,
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 8,
    backgroundColor: '#fff',
  },
  statValue: { fontSize: 26, fontWeight: '800' },
  statLabel: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  codeText: {
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#374151',
    backgroundColor: '#f1f5f9',
    padding: 10,
    borderRadius: 8,
    lineHeight: 20,
  },
});
