// screens/UploadScreen.jsx
// ─────────────────────────────────────────────────────
// Fixed: bulk classification, timeout protection,
//        offline fallback using business rules
// ─────────────────────────────────────────────────────

import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Alert,
} from 'react-native';
import * as DocumentPicker from 'expo-document-picker';
import * as FileSystem from 'expo-file-system/legacy';
import Papa from 'papaparse';
import { API_BASE } from '../utils/api';

const DEFAULT_CENTER = { lat: 6.9271, lng: 79.8612 };

// ── Business rules fallback (no API needed) ───────────
const URGENT_MAIL_TYPES = [
  'court notice','legal document','registered letter','speed post',
  'certified mail','government notice','tax notice','medical report',
  'insurance claim','summons',
];
const URGENT_SENDERS = [
  'court','law firm','government office','tax office',
  'bank','hospital','insurance company',
];

const classifyLocally = (mail_type = '', sender_type = '') => {
  const mt = mail_type.toLowerCase();
  const st = sender_type.toLowerCase();
  const isUrgent = URGENT_MAIL_TYPES.some(u => mt.includes(u)) ||
                   URGENT_SENDERS.some(u => st.includes(u));
  return isUrgent ? 'urgent' : 'regular';
};

// ── Fetch with timeout ────────────────────────────────
const fetchWithTimeout = (url, options = {}, timeout = 5000) => {
  return Promise.race([
    fetch(url, options),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error('timeout')), timeout)
    ),
  ]);
};

// ── Geocode single address ────────────────────────────
const geocode = async (address) => {
  await new Promise(r => setTimeout(r, 600)); // rate limit
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json` +
      `&q=${encodeURIComponent(address + ', Sri Lanka')}&limit=1`;
    const res = await fetchWithTimeout(url, {
      headers: { 'User-Agent': 'PostalRouteApp/1.0' },
    }, 6000);
    const data = await res.json();
    if (data && data.length > 0) {
      return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon), ok: true };
    }
  } catch (_) {}
  // fallback coords near Colombo
  return {
    lat: DEFAULT_CENTER.lat + (Math.random() - 0.5) * 0.1,
    lng: DEFAULT_CENTER.lng + (Math.random() - 0.5) * 0.1,
    ok: false,
  };
};

// ── Bulk classify via API (single call) ───────────────
const bulkClassify = async (items) => {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/ml/classify-bulk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(items),
    }, 8000);
    if (!res.ok) throw new Error('bad response');
    return await res.json(); // array of { priority, confidence }
  } catch (_) {
    // fallback: classify locally
    return items.map(i => ({ priority: classifyLocally(i.mail_type, i.sender_type) }));
  }
};

// ── Save deliveries to DB (fire and forget) ───────────
const saveToDb = async (sessionId, deliveries) => {
  try {
    await fetchWithTimeout(`${API_BASE}/deliveries/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, deliveries }),
    }, 8000);
  } catch (_) {
    console.warn('DB save skipped (backend unavailable)');
  }
};

// ── Get session ID ────────────────────────────────────
const getSessionId = async () => {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/session/new`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    }, 5000);
    const data = await res.json();
    return data.session_id;
  } catch (_) {
    return `local_${Date.now()}`;
  }
};

// ─────────────────────────────────────────────────────
export default function UploadScreen({ navigation }) {
  const [loading, setLoading]   = useState(false);
  const [progress, setProgress] = useState('');
  const [step, setStep]         = useState(0); // 0-100
  const [stats, setStats]       = useState(null);
  const [backendOk, setBackendOk] = useState(null); // null=unknown

  // ── Check backend connectivity ────────────────────
  const checkBackend = async () => {
    try {
      const res = await fetchWithTimeout(`${API_BASE.replace('/api','')}`, {}, 4000);
      setBackendOk(res.ok);
      return res.ok;
    } catch (_) {
      setBackendOk(false);
      return false;
    }
  };

  // ── Pick CSV ──────────────────────────────────────
  const pickCSV = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['text/csv', 'text/comma-separated-values', '*/*'],
        copyToCacheDirectory: true,
      });
      if (result.canceled) return;

      setLoading(true);
      setStats(null);
      setStep(0);

      setProgress('Checking connection…');
      const online = await checkBackend();

      const fileUri = result.assets[0].uri;
      setProgress('Reading file…');
      const content = await FileSystem.readAsStringAsync(fileUri);

      Papa.parse(content, {
        header: true,
        skipEmptyLines: true,
        complete: async (parsed) => {
          try {
            await processRows(parsed.data, online);
          } catch (e) {
            Alert.alert('Error', e.message);
            setLoading(false);
            setProgress('');
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

  const processRows = async (rows, online) => {
    const total = rows.length;
    const sessionId = await getSessionId();

    // ── STEP 1: Geocode rows missing lat/lng ─────────
    const needsGeocode = rows.filter(r => {
      const lat = parseFloat(r.latitude || r.lat || '');
      const lng = parseFloat(r.longitude || r.lng || r.lon || '');
      return isNaN(lat) || isNaN(lng);
    });

    const geocoded = {};
    if (needsGeocode.length > 0) {
      for (let i = 0; i < needsGeocode.length; i++) {
        const row = needsGeocode[i];
        const addr = row.address || row.Address || '';
        setProgress(`📍 Geocoding ${i + 1}/${needsGeocode.length}: ${addr.substring(0,30)}…`);
        setStep(Math.round((i / needsGeocode.length) * 40));
        const coords = await geocode(addr);
        geocoded[addr] = coords;
      }
    }

    // ── STEP 2: Build delivery list ──────────────────
    setProgress('📋 Building delivery list…');
    setStep(50);

    const deliveries = rows.map((row, i) => {
      let lat = parseFloat(row.latitude || row.lat || '');
      let lng = parseFloat(row.longitude || row.lng || row.lon || '');
      const addr = row.address || row.Address || `Stop ${i + 1}`;

      if (isNaN(lat) || isNaN(lng)) {
        const gc = geocoded[addr] || { lat: DEFAULT_CENTER.lat, lng: DEFAULT_CENTER.lng };
        lat = gc.lat;
        lng = gc.lng;
      }

      return {
        id: i + 1,
        address: addr,
        latitude: lat,
        longitude: lng,
        mail_type: row.mail_type || row.type || 'Regular Letter',
        priority: '',  // filled in step 3
        sender_type: row.sender_type || 'Individual',
        recipient_type: row.recipient_type || 'Individual',
        parcels: parseInt(row.parcels || '1', 10) || 1,
        urgent: 0,
      };
    });

    // ── STEP 3: Bulk classify (1 API call total) ─────
    setProgress('🧠 Classifying mail priorities…');
    setStep(70);

    const needsClassify = deliveries.filter(d => {
      const raw = (rows[d.id - 1]?.priority || '').toLowerCase();
      return raw !== 'urgent' && raw !== 'regular';
    });

    let classifyResults = [];
    if (needsClassify.length > 0) {
      const payload = needsClassify.map(d => ({
        mail_type: d.mail_type,
        sender_type: d.sender_type,
        recipient_type: d.recipient_type,
        time_received: new Date().toISOString(),
        day_of_week: new Date().toLocaleDateString('en-US', { weekday: 'long' }),
      }));
      classifyResults = await bulkClassify(payload);
    }

    // Assign priorities
    let classifyIdx = 0;
    deliveries.forEach((d, i) => {
      const rawPriority = (rows[i]?.priority || '').toLowerCase();
      if (rawPriority === 'urgent' || rawPriority === 'regular') {
        d.priority = rawPriority;
      } else {
        d.priority = classifyResults[classifyIdx]?.priority || classifyLocally(d.mail_type, d.sender_type);
        classifyIdx++;
      }
      d.urgent = d.priority === 'urgent' ? 1 : 0;
    });

    // ── STEP 4: Save to DB (non-blocking) ───────────
    setProgress('💾 Saving to database…');
    setStep(90);
    saveToDb(sessionId, deliveries); // fire and forget

    // ── Done ─────────────────────────────────────────
    setStep(100);
    const urgentCount  = deliveries.filter(d => d.priority === 'urgent').length;
    const regularCount = deliveries.length - urgentCount;

    setStats({ total: deliveries.length, urgent: urgentCount, regular: regularCount, sessionId, online });
    setLoading(false);
    setProgress('');

    navigation.navigate('MailList', { deliveries, sessionId });
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>

      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🗺️ Postal Route Optimizer</Text>
        <Text style={styles.headerSub}>Sri Lanka Smart Delivery System</Text>
      </View>

      {/* Backend status */}
      {backendOk !== null && (
        <View style={[styles.statusBar, { backgroundColor: backendOk ? '#dcfce7' : '#fef9c3' }]}>
          <Text style={[styles.statusText, { color: backendOk ? '#166534' : '#854d0e' }]}>
            {backendOk ? '✅ Backend connected' : '⚠️ Backend offline — using local classification'}
          </Text>
        </View>
      )}

      {/* Upload card */}
      <View style={styles.card}>
        <Text style={styles.cardTitle}>📂 Upload Deliveries CSV</Text>
        <Text style={styles.cardDesc}>
          Required: <Text style={styles.bold}>address, mail_type</Text>{'\n'}
          Optional: latitude, longitude, priority, parcels
        </Text>

        <TouchableOpacity
          style={[styles.uploadBtn, loading && styles.disabled]}
          onPress={pickCSV}
          disabled={loading}
        >
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.uploadBtnText}>📁  Choose CSV File</Text>
          }
        </TouchableOpacity>

        {/* Progress */}
        {loading && (
          <View style={styles.progressContainer}>
            <Text style={styles.progressText}>{progress}</Text>
            <View style={styles.progressBarBg}>
              <View style={[styles.progressBarFill, { width: `${step}%` }]} />
            </View>
            <Text style={styles.progressPct}>{step}%</Text>
          </View>
        )}
      </View>

      {/* Stats */}
      {stats && (
        <View style={styles.statsCard}>
          <Text style={styles.statsTitle}>✅ Upload Complete!</Text>
          <View style={styles.statsRow}>
            <StatBadge label="Total"   value={stats.total}   color="#3b82f6" />
            <StatBadge label="Urgent"  value={stats.urgent}  color="#ef4444" />
            <StatBadge label="Regular" value={stats.regular} color="#10b981" />
          </View>
          {!stats.online && (
            <Text style={styles.offlineNote}>
              ℹ️ Priorities assigned using local business rules (backend was offline)
            </Text>
          )}
        </View>
      )}

      {/* CSV format guide */}
      <View style={[styles.card, { backgroundColor: '#f0fdf4' }]}>
        <Text style={styles.cardTitle}>📋 CSV Format</Text>
        <Text style={styles.codeText}>
          address,mail_type,sender_type,priority{'\n'}
          "Colombo 07",Court Notice,Court,urgent{'\n'}
          "Galle Road",Regular Letter,Individual,regular
        </Text>
        <Text style={styles.tip}>
          💡 Tip: Include latitude & longitude to skip geocoding and load instantly
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
  container:    { flexGrow:1, backgroundColor:'#f8fafc', padding:16 },
  header:       { backgroundColor:'#1e40af', borderRadius:16, padding:20, marginBottom:16, alignItems:'center' },
  headerTitle:  { fontSize:22, fontWeight:'bold', color:'#fff' },
  headerSub:    { fontSize:13, color:'#bfdbfe', marginTop:4 },

  statusBar:    { borderRadius:10, padding:10, marginBottom:12, alignItems:'center' },
  statusText:   { fontSize:13, fontWeight:'600' },

  card:         { backgroundColor:'#fff', borderRadius:14, padding:18, marginBottom:16,
                  shadowColor:'#000', shadowOpacity:0.07, shadowRadius:8, elevation:3 },
  cardTitle:    { fontSize:16, fontWeight:'700', marginBottom:8, color:'#1e293b' },
  cardDesc:     { fontSize:13, color:'#64748b', lineHeight:20, marginBottom:14 },
  bold:         { fontWeight:'700', color:'#1e293b' },

  uploadBtn:    { backgroundColor:'#2563eb', borderRadius:10, paddingVertical:14, alignItems:'center' },
  uploadBtnText:{ color:'#fff', fontSize:16, fontWeight:'700' },
  disabled:     { opacity:0.6 },

  progressContainer: { marginTop:14 },
  progressText: { fontSize:13, color:'#3b82f6', marginBottom:6 },
  progressBarBg:{ height:8, backgroundColor:'#e5e7eb', borderRadius:4, overflow:'hidden' },
  progressBarFill:{ height:'100%', backgroundColor:'#3b82f6', borderRadius:4 },
  progressPct:  { fontSize:12, color:'#6b7280', marginTop:4, textAlign:'right' },

  statsCard:    { backgroundColor:'#ecfdf5', borderRadius:14, padding:18, marginBottom:16,
                  borderWidth:1, borderColor:'#6ee7b7' },
  statsTitle:   { fontSize:16, fontWeight:'700', marginBottom:12, color:'#065f46' },
  statsRow:     { flexDirection:'row', justifyContent:'space-around' },
  statBadge:    { alignItems:'center', borderWidth:2, borderRadius:10,
                  paddingHorizontal:16, paddingVertical:8, backgroundColor:'#fff' },
  statValue:    { fontSize:26, fontWeight:'800' },
  statLabel:    { fontSize:12, color:'#6b7280', marginTop:2 },
  offlineNote:  { fontSize:12, color:'#92400e', marginTop:10, textAlign:'center' },

  codeText:     { fontFamily:'monospace', fontSize:12, color:'#374151',
                  backgroundColor:'#f1f5f9', padding:10, borderRadius:8, lineHeight:20 },
  tip:          { fontSize:12, color:'#059669', marginTop:8, fontStyle:'italic' },
});
