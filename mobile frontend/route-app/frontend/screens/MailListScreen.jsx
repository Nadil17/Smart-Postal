// screens/MailListScreen.jsx
import React, { useState, useEffect } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ActivityIndicator, Alert, TextInput,
} from 'react-native';
import { optimizeRoute } from '../utils/api';

const MAIL_ICONS = {
  'Court Notice': '⚖️', 'Legal Document': '📋', 'Speed Post': '⚡',
  'Registered Letter': '📮', 'Regular Letter': '✉️', default: '📬',
};

export default function MailListScreen({ route, navigation }) {
  const { deliveries = [], sessionId } = route.params || {};
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all'); // 'all' | 'urgent' | 'regular'
  const [conditions, setConditions] = useState({
    weather: 'clear',
    traffic: 'moderate',
  });

  const urgentCount = deliveries.filter((d) => d.priority === 'urgent').length;
  const regularCount = deliveries.length - urgentCount;

  const filtered = deliveries.filter((d) => {
    const matchSearch =
      d.address.toLowerCase().includes(search.toLowerCase()) ||
      (d.mail_type || '').toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === 'all' ||
      (filter === 'urgent' && d.priority === 'urgent') ||
      (filter === 'regular' && d.priority !== 'urgent');
    return matchSearch && matchFilter;
  });

  const handleOptimize = async () => {
    if (deliveries.length === 0) return;
    setLoading(true);
    try {
      const payload = {
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
          sender_type: d.sender_type || 'Individual',
          recipient_type: d.recipient_type || 'Individual',
        })),
        weather_condition: conditions.weather,
        traffic_level: conditions.traffic,
        methods: ['nearest_neighbor', 'urgent_priority', '2opt', 'q_learning'],
      };

      const result = await optimizeRoute(payload);
      navigation.navigate('Routes', {
        allRoutes: result,
        deliveries,
        sessionId,
        conditions,
      });
    } catch (e) {
      Alert.alert('Optimization Error', e.message);
    } finally {
      setLoading(false);
    }
  };

  const renderItem = ({ item, index }) => {
    const isUrgent = item.priority === 'urgent';
    const icon = MAIL_ICONS[item.mail_type] || MAIL_ICONS.default;

    return (
      <View style={[styles.item, isUrgent ? styles.urgentItem : styles.regularItem]}>
        <View style={[styles.badge, isUrgent ? styles.urgentBadge : styles.regularBadge]}>
          <Text style={styles.badgeNum}>{index + 1}</Text>
        </View>

        <View style={styles.itemContent}>
          <Text style={styles.itemAddress} numberOfLines={1}>{item.address}</Text>
          <Text style={styles.itemMeta}>
            {icon} {item.mail_type || 'Regular Letter'}
          </Text>
          <Text style={styles.itemCoords}>
            📍 {parseFloat(item.latitude).toFixed(4)},{' '}
            {parseFloat(item.longitude).toFixed(4)}
          </Text>
        </View>

        <View style={[styles.priorityTag, isUrgent ? styles.urgentTag : styles.regularTag]}>
          <Text style={styles.priorityTagText}>
            {isUrgent ? '🚨 URGENT' : '✅ REGULAR'}
          </Text>
        </View>
      </View>
    );
  };

  return (
    <View style={styles.container}>
      {/* Stats Bar */}
      <View style={styles.statsBar}>
        <Chip label={`📦 Total: ${deliveries.length}`} active={filter === 'all'} onPress={() => setFilter('all')} />
        <Chip label={`🚨 Urgent: ${urgentCount}`} active={filter === 'urgent'} color="#ef4444" onPress={() => setFilter('urgent')} />
        <Chip label={`✅ Regular: ${regularCount}`} active={filter === 'regular'} color="#10b981" onPress={() => setFilter('regular')} />
      </View>

      {/* Conditions Selector */}
      <View style={styles.condRow}>
        <Text style={styles.condLabel}>🌤 Weather:</Text>
        {['clear', 'light_rain', 'heavy_rain'].map((w) => (
          <TouchableOpacity
            key={w}
            style={[styles.condBtn, conditions.weather === w && styles.condBtnActive]}
            onPress={() => setConditions((c) => ({ ...c, weather: w }))}
          >
            <Text style={[styles.condBtnText, conditions.weather === w && styles.condBtnTextActive]}>
              {w === 'clear' ? '☀️' : w === 'light_rain' ? '🌦' : '🌧'}
            </Text>
          </TouchableOpacity>
        ))}
        <Text style={[styles.condLabel, { marginLeft: 12 }]}>🚦 Traffic:</Text>
        {['low', 'moderate', 'high'].map((t) => (
          <TouchableOpacity
            key={t}
            style={[styles.condBtn, conditions.traffic === t && styles.condBtnActive]}
            onPress={() => setConditions((c) => ({ ...c, traffic: t }))}
          >
            <Text style={[styles.condBtnText, conditions.traffic === t && styles.condBtnTextActive]}>
              {t === 'low' ? '🟢' : t === 'moderate' ? '🟡' : '🔴'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Search */}
      <TextInput
        style={styles.search}
        placeholder="🔍 Search address or mail type..."
        value={search}
        onChangeText={setSearch}
        placeholderTextColor="#9ca3af"
      />

      {/* List */}
      <FlatList
        data={filtered}
        keyExtractor={(_, i) => i.toString()}
        renderItem={renderItem}
        contentContainerStyle={{ paddingBottom: 100 }}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>No deliveries match your filter</Text>
          </View>
        }
      />

      {/* Optimize Button */}
      <View style={styles.footer}>
        <TouchableOpacity
          style={[styles.optimizeBtn, loading && styles.disabled]}
          onPress={handleOptimize}
          disabled={loading || deliveries.length === 0}
        >
          {loading ? (
            <View style={styles.row}>
              <ActivityIndicator color="#fff" size="small" />
              <Text style={styles.optimizeBtnText}> Optimizing…</Text>
            </View>
          ) : (
            <Text style={styles.optimizeBtnText}>🚀  Optimize Route ({deliveries.length} stops)</Text>
          )}
        </TouchableOpacity>
      </View>
    </View>
  );
}

const Chip = ({ label, active, color = '#2563eb', onPress }) => (
  <TouchableOpacity
    onPress={onPress}
    style={[styles.chip, active && { backgroundColor: color, borderColor: color }]}
  >
    <Text style={[styles.chipText, active && { color: '#fff' }]}>{label}</Text>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  statsBar: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  chip: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  chipText: { fontSize: 12, color: '#374151', fontWeight: '600' },
  condRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: '#f1f5f9',
    gap: 6,
  },
  condLabel: { fontSize: 12, fontWeight: '600', color: '#374151' },
  condBtn: { borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, padding: 4, backgroundColor: '#fff' },
  condBtnActive: { backgroundColor: '#dbeafe', borderColor: '#3b82f6' },
  condBtnText: { fontSize: 16 },
  condBtnTextActive: {},
  search: {
    margin: 12,
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 12,
    marginBottom: 8,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  urgentItem: { backgroundColor: '#fff5f5', borderColor: '#fca5a5' },
  regularItem: { backgroundColor: '#fff', borderColor: '#e5e7eb' },
  badge: { width: 32, height: 32, borderRadius: 16, justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  urgentBadge: { backgroundColor: '#ef4444' },
  regularBadge: { backgroundColor: '#3b82f6' },
  badgeNum: { color: '#fff', fontSize: 13, fontWeight: '800' },
  itemContent: { flex: 1 },
  itemAddress: { fontSize: 14, fontWeight: '600', color: '#1e293b' },
  itemMeta: { fontSize: 12, color: '#64748b', marginTop: 2 },
  itemCoords: { fontSize: 11, color: '#94a3b8', marginTop: 1 },
  priorityTag: { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 4 },
  urgentTag: { backgroundColor: '#fee2e2' },
  regularTag: { backgroundColor: '#dcfce7' },
  priorityTagText: { fontSize: 10, fontWeight: '700' },
  footer: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: 'rgba(248,250,252,0.95)',
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
  },
  optimizeBtn: {
    backgroundColor: '#2563eb',
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: 'center',
  },
  optimizeBtnText: { color: '#fff', fontSize: 16, fontWeight: '700' },
  disabled: { opacity: 0.6 },
  row: { flexDirection: 'row', alignItems: 'center' },
  empty: { padding: 40, alignItems: 'center' },
  emptyText: { color: '#9ca3af', fontSize: 14 },
});
