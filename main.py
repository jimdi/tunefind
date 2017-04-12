#!/usr/bin/python3
import requests
import os
import json
import argparse

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

parser = argparse.ArgumentParser(description='Parse OST for TV shows from tunefind')
parser.add_argument('showname', metavar='showname', type=str, help='show name')
args = parser.parse_args()
showname = args.showname

if showname == '' or showname is None:
    print('Show name is required')
    exit()

os.makedirs('cache', exist_ok=True)
os.makedirs('result', exist_ok=True)

seasons_url = 'https://www.tunefind.com/api/frontend/show/%s?fields=seasons&metatags=1' % showname
r = requests.get(seasons_url)
_json = r.json()
if len(_json) == 0:
    print('Can\'t get data for show')
    exit()

season_cnt = int(len(_json['seasons']))

fout = open('result/' + str(showname) + '.md', 'w', encoding='utf-8')

for x in range(1, season_cnt):
    fout.write('# Season %d #\r\n' % x)

    season_url = 'http://www.tunefind.com/api/frontend/show/%s/season/%s?fields=episodes,theme-song,music-supervisors&metatags=1' % (showname, x)
    _json = geturlorjson(season_url, 'cache/%s_s%s.json' % (showname, x))

    for e in _json['episodes']:
        fout.write('## ==> S%0.2dE%0.2d - %s.txt <== ##\r\n' % (int(x), int(e['number']), e['name']))

        episode_url = 'http://www.tunefind.com/api/frontend/episode/%s?fields=song-events,questions' % e['id']
        _json = geturlorjson(episode_url, 'cache/%s.json' % (e['id']))

        for s in _json['song_events']:
            fout.write('* Song: %s - %s\r\n' % (s['song']['artist']['name'], s['song']['name']))
            if s['song']['album']:
                fout.write('  Album: %s\r\n' % s['song']['album'])
            if s['description']:
                fout.write('  Description: %s\r\n' % s['description'])
            else:
                fout.write('\r\n')

fout.close()
