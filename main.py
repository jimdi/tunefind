import requests
import os
import json

url = "http://www.tunefind.com/api/frontend/show/shameless/season/%s?fields=episodes,theme-song,music-supervisors&metatags=1"
url2 = "http://www.tunefind.com/api/frontend/episode/%s?fields=song-events,questions"

os.makedirs('cache', exist_ok=True)

for x in range(1, 8):
    print('# Season %d #' % x)

    fname = 'cache/%s.json' % (x)
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8') as f:
            _json = json.load(f)
    else:
        r = requests.get(url % x)
        _json = r.json()
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(json.dumps(_json))

    for e in _json['episodes']:
        print('## ==> S%0.2dE%0.2d - %s.txt <== ##' % (int(x), int(e['number']), e['name']))

        fname = 'cache/%s.json' % (e['id'])
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8') as f:
                _json = json.load(f)
        else:
            r = requests.get(url2 % e['id'])
            _json = r.json()
            with open(fname, 'w', encoding='utf-8') as f:
                f.write(json.dumps(_json))

        for s in _json['song_events']:
            print('* Song: %s - %s\r\n' % (s['song']['artist']['name'], s['song']['name']))
            if s['song']['album']:
                print('  Album: %s\r\n' % s['song']['album'])
            if s['description']:
                print('  Description: %s\r\n' % s['description'])
            else:
                print('\r\n')