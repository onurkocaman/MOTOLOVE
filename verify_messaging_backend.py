
import werkzeug
werkzeug.__version__ = "2.2.2" # Monkeypatch for Flask compatibility
from app import app
import json

def verify_backend():
    print("Testing Messaging API Backend...")
    
    with app.test_client() as client:
        # 1. Simulate Login as User 1
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['user_name'] = 'Test User'
        
        # Verify URL Map for the route
        adapter = app.url_map.bind('localhost')
        match = adapter.match('/api/messages/conversations', method='GET')
        print(f"Route matches endpoint: {match}")

            
        print("\n[TEST] GET /api/messages/conversations")
        try:
            res = client.get('/api/messages/conversations')
            print(f"Status Code: {res.status_code}")
            
            if res.status_code == 200:
                data = res.get_json()
                print("Response JSON:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get('success'):
                    convs = data.get('conversations', [])
                    print(f"Found {len(convs)} conversations.")
                    if len(convs) > 0:
                        first_conv_id = convs[0]['conversation_id']
                        
                        # 2. Test Get Messages for First Conversation
                        print(f"\n[TEST] GET /api/messages/conversation/{first_conv_id}")
                        res_msg = client.get(f'/api/messages/conversation/{first_conv_id}')
                        print(f"Status Code: {res_msg.status_code}")
                        print("Response JSON:")
                        print(json.dumps(res_msg.get_json(), indent=2, ensure_ascii=False))
                else:
                    print("API returned success=False")
            else:
                print("Failed to get conversations.")
                print(res.text)

        except Exception as e:
            print(f"Test Exception: {e}")

if __name__ == "__main__":
    verify_backend()
