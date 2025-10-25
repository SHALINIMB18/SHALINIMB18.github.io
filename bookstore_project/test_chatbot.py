import requests

# Test the chatbot API
response = requests.post('http://127.0.0.1:8000/api/chatbot/', json={'query': 'hello'})
print('Status:', response.status_code)
print('Response:', response.json())

# Test recommendation
response2 = requests.post('http://127.0.0.1:8000/api/chatbot/', json={'query': 'recommend me a book'})
print('Recommendation Status:', response2.status_code)
print('Recommendation Response:', response2.json())
