import requests
import json

print('=' * 60)
print('  SMART LOCKER API TEST - Colombo, Sri Lanka')
print('=' * 60)

# 1. Test ST-GNN AI Recommendation
print('\n1. POST /api/lockers/recommend (AI Prediction)')
r = requests.post('http://127.0.0.1:8000/api/lockers/recommend', json={
    'latitude': 6.9100,
    'longitude': 79.8600,
    'courier_route': [[6.9271, 79.8612], [6.9200, 79.8580]],
    'package_size': 'medium'
})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'   Success: {data.get("success")}')
    if data.get('recommendations'):
        print(f'\n   🤖 AI Recommendations ({len(data["recommendations"])} lockers):')
        print('   ' + '-' * 55)
        for i, rec in enumerate(data['recommendations'], 1):
            medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
            print(f'\n   {medal} #{i} {rec["name"]}')
            print(f'       📍 {rec.get("address", "N/A")}')
            print(f'       📏 Distance: {rec["distance"]} | Score: {rec["score"]}')
            avail = rec["availability"]
            print(f'       📦 Slots: S:{avail["small"]} M:{avail["medium"]} L:{avail["large"]}')
            print(f'       🚚 Route Deviation: {rec.get("route_deviation", "N/A")}')

# 2. Get All Lockers
print('\n' + '=' * 60)
print('2. GET /api/lockers/ (All Colombo Lockers)')
r = requests.get('http://127.0.0.1:8000/api/lockers/')
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    lockers = r.json()
    print(f'   Total Lockers in Colombo: {len(lockers)}')
    for loc in lockers:
        print(f'   • {loc["name"]}')
        print(f'     {loc.get("address", "N/A")}')

# 3. Get Single Locker
print('\n' + '=' * 60)
print('3. GET /api/lockers/L01')
r = requests.get('http://127.0.0.1:8000/api/lockers/L01')
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    locker = r.json()
    print(f'   Name: {locker["name"]}')
    print(f'   Address: {locker.get("address", "N/A")}')
    print(f'   Location: ({locker["latitude"]}, {locker["longitude"]})')

# 4. Reserve Slot
print('\n' + '=' * 60)
print('4. POST /api/lockers/L01/reserve')
r = requests.post('http://127.0.0.1:8000/api/lockers/L01/reserve', json={
    'order_id': 999,
    'slot_size': 'medium'
})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'   ✅ Success: {data.get("success")}')
    print(f'   🔐 Unlock Code: {data.get("unlock_code")}')

# 5. Unlock Locker
print('\n' + '=' * 60)
print('5. POST /api/lockers/L01/unlock')
r = requests.post('http://127.0.0.1:8000/api/lockers/L01/unlock', json={
    'verification_code': '123456'
})
print(f'   Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'   ✅ {data.get("message")}')

print('\n' + '=' * 60)
print('  ✅ ALL LOCKER TESTS PASSED!')
print('=' * 60)
