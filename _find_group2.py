import requests, json
headers = {'apikey': 'evolution-test-token'}
base = 'http://localhost:8088'

# Check instance state
r = requests.get(f'{base}/instance/connectionState/bibliobot', headers=headers, timeout=10)
if r.status_code == 200:
    data = r.json()
    inst = data.get('instance', {})
    print('Instance state:', json.dumps(inst, indent=2, ensure_ascii=False)[:500])

# Try to get group info from the instance fetch
r = requests.get(f'{base}/instance/fetchInstances', headers=headers, timeout=10)
if r.status_code == 200:
    for inst in r.json():
        if inst.get('name') == 'bibliobot':
            print(f"Owner JID: {inst.get('ownerJid')}")
            print(f"Profile: {inst.get('profileName')}")

# Try POST endpoints that might list chats
for ep in ['/chat/find/bibliobot', '/chat/list/bibliobot']:
    r = requests.post(f'{base}{ep}', json={}, headers=headers, timeout=10)
    if r.status_code != 404:
        print(f'POST {ep}: {r.status_code} {r.text[:200]}')
