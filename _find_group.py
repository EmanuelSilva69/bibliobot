import requests, json
headers = {'apikey': 'evolution-test-token'}
base = 'http://localhost:8088'

endpoints = [
    '/message/list/bibliobot',
    '/message/bibliobot/list',
    '/chat/find/bibliobot',
    '/chat/list',
    '/instance/list',
    '/instance/connectionState/bibliobot',
    '/chat/findInstances/bibliobot',
]

for ep in endpoints:
    r = requests.get(f'{base}{ep}', headers=headers, timeout=10)
    if r.status_code == 200:
        print(f'200: {ep}')
        data = r.json()
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and 'jid' in item:
                    jid = item.get('jid','')
                    name = item.get('name','') or item.get('metadata',{}).get('subject','')
                    if '@g.us' in jid:
                        print(f'  GRUPO: {jid} | {name}')
        elif isinstance(data, dict):
            print(f'  keys: {list(data.keys())[:10]}')
    elif r.status_code != 404:
        print(f'{r.status_code}: {ep}')
