import requests
import os
import json

def geturlorjson(url, fname):
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8') as f:
            _json = json.load(f)
    else:
        r = requests.get(url)
        _json = r.json()
        with open(fname, 'w', encoding='utf-8') as f:
            f.write(json.dumps(_json))
    return _json

showname = 'supernatural'

os.makedirs('cache', exist_ok=True)

seasons_url = "https://www.tunefind.com/api/frontend/show/%s?fields=seasons&metatags=1" % showname
r = requests.get(seasons_url)
_json = r.json()
season_cnt = int(len(_json['seasons']))

for x in range(1, season_cnt):
    print('# Season %d #' % x)

    season_url = "http://www.tunefind.com/api/frontend/show/%s/season/%s?fields=episodes,theme-song,music-supervisors&metatags=1" % (showname, x)
    _json = geturlorjson(season_url, 'cache/%s_s%s.json' % (showname, x))

    for e in _json['episodes']:
        print('## ==> S%0.2dE%0.2d - %s.txt <== ##' % (int(x), int(e['number']), e['name']))

        episode_url = "http://www.tunefind.com/api/frontend/episode/%s?fields=song-events,questions" % e['id']
        _json = geturlorjson(episode_url, 'cache/%s.json' % (e['id']))

        for s in _json['song_events']:
            print('* Song: %s - %s\r\n' % (s['song']['artist']['name'], s['song']['name']))
            if s['song']['album']:
                print('  Album: %s\r\n' % s['song']['album'])
            if s['description']:
                print('  Description: %s\r\n' % s['description'])
            else:
                print('\r\n')
