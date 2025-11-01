import requests, json
base='http://127.0.0.1:8000'
s = requests.Session()
try:
    r = s.get(base + '/')
    csrftoken = s.cookies.get('csrftoken','')
    print('Got csrftoken cookie:', csrftoken)
    headers = {'Content-Type':'application/json'}
    if csrftoken:
        headers['X-CSRFToken'] = csrftoken
    payload = {'query':'Recommend me a sci-fi book'}
    r2 = s.post(base + '/api/chatbot/', headers=headers, data=json.dumps(payload), timeout=10)
    print('Status:', r2.status_code)
    try:
        print('JSON:', r2.json())
    except Exception:
        print('Text:', r2.text[:1000])
except Exception as e:
    print('Error connecting:', e)
