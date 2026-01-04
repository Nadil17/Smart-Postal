"""
Test Locker Recommendation API
"""
import requests
import json

API_BASE = 'http://127.0.0.1:8000'

def test_locker_api():
    print('='*50)
    print('TESTING LOCKER RECOMMENDATION API')
    print('='*50)

    # Test locker recommendation endpoint
    print('\n1. Testing Locker Recommendation...')
    try:
        # Customer location: Colombo 03
        payload = {
            'latitude': 6.9100,
            'longitude': 79.8600,
            'courier_route': [
                [6.9344, 79.8428],  # Fort
                [6.9200, 79.8550],  # Mid point
                [6.9100, 79.8600]   # Destination
            ]
        }
        
        r = requests.post(f'{API_BASE}/api/lockers/recommend', json=payload, timeout=10)
        
        if r.status_code == 200:
            result = r.json()
            print('   ✓ Recommendation received!')
            print(f'   Success: {result.get("success")}')
            
            if result.get('recommendations'):
                print('\n   Top 3 Locker Recommendations:')
                for i, loc in enumerate(result['recommendations'], 1):
                    print(f'   {i}. {loc["name"]}')
                    print(f'      - Score: {loc["score"]}')
                    print(f'      - Distance: {loc["distance"]}')
                    print(f'      - Availability: {loc["availability"]} slots')
            else:
                print(f'   Error: {result.get("error")}')
        else:
            print(f'   ✗ Failed: {r.status_code} - {r.text[:200]}')
            
    except requests.exceptions.ConnectionError:
        print('   ✗ Backend not running. Start with: python run.py')
    except Exception as e:
        print(f'   ✗ Error: {e}')

    print('\n' + '='*50)

if __name__ == '__main__':
    test_locker_api()
