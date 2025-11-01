import os
import sys
import django
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore_project.settings')
django.setup()

from books.chatbot_utils import call_external_chat_api, chatbot

print('CHATBOT_API_URL=', os.environ.get('CHATBOT_API_URL'))
print('CHATBOT_API_KEY present=', bool(os.environ.get('CHATBOT_API_KEY')))
print('CHATBOT_API_TIMEOUT=', os.environ.get('CHATBOT_API_TIMEOUT'))

query = 'Recommend a fantasy book'
print('\nCalling external API wrapper with timeout=3...')
try:
    resp = call_external_chat_api(query, timeout=3)
    print('External response:', resp)
except Exception as e:
    print('External call raised exception:')
    traceback.print_exc()

print('\nCalling local chatbot...')
try:
    local = chatbot.chat(query)
    print('Local chatbot response:', local)
except Exception as e:
    print('Local chatbot raised exception:')
    traceback.print_exc()
