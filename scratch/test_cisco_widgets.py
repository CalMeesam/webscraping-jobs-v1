import json

with open('scratch/cisco_widgets.json', 'r', encoding='utf-8') as f:
    payloads = json.load(f)

for i, p in enumerate(payloads):
    s = json.dumps(p)
    if 'ASIC' in s:
        print(f'Payload {i} has ASIC! (Length: {len(s)})')

        def find_items(obj, path=''):
            if isinstance(obj, dict):
                if any(k in obj for k in ['title', 'jobTitle', 'positionTitle']):
                    t = obj.get('title') or obj.get('jobTitle') or obj.get('positionTitle')
                    loc_keys = [k for k in obj if 'loc' in k.lower() or 'city' in k.lower() or 'country' in k.lower() or 'state' in k.lower()]
                    print(f'  Match at {path}:')
                    print(f'    Title: {repr(t)}')
                    print(f'    Loc keys: {loc_keys}')
                    print(f'    Loc values: {[obj[k] for k in loc_keys]}')
                    print(f'    All keys: {list(obj.keys())[:15]}')
                for k, v in obj.items():
                    find_items(v, f'{path}.{k}' if path else k)
            elif isinstance(obj, list):
                for idx, item in enumerate(obj):
                    find_items(item, f'{path}[{idx}]')

        find_items(p)
