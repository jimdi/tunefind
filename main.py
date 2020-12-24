#!/usr/bin/python3
import argparse
import json
import os

import requests
from requests.models import Response

BASE_API_URL = 'http://www.tunefind.com/api/frontend/'


def get_url_or_json_from_cache(url, filename, use_cache=True):
    if os.path.exists(filename) & bool(use_cache):
        with open(filename, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
    else:
        r = requests.get(url)
        json_data = r.json()
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(json.dumps(json_data))
    return json_data


def get_seasons_cnt(show_name):
    seasons_url = 'https://www.tunefind.com/api/frontend/show/%s?fields=seasons&metatags=1' % show_name
    response: Response = requests.get(seasons_url)
    if response.status_code == 404:
        print('404. Nothing found for', show_name)
        exit()

    json_data = response.json()
    if len(json_data) == 0 and response.status_code == 200:
        print('Can\'t get data for', show_name)
        exit()

    season_cnt = int(len(json_data['seasons']))
    return season_cnt


def get_episodes(show_name, season_cnt, use_cache=True):
    global BASE_API_URL
    songs_info = ''

    for x in range(1, season_cnt + 1):
        season_num = str(x).zfill(2)
        songs_info += f'# Season {season_num} #\r\n'
        print(f'Parsing data for season {x} of {season_cnt}')
        # out_filename.write('# Season %d #\r\n' % x)

        season_url = BASE_API_URL + f'show/{show_name}/season/{str(x)}?fields=episodes,theme-song,music-supervisors&metatags=1'
        json_data = get_url_or_json_from_cache(season_url, f'cache/{show_name}_s{x}.json', use_cache)

        if json_data:
            for episodes in json_data['episodes']:
                songs_info += f'## ==> S{season_num}E{str(episodes["number"]).zfill(2)} - {episodes["name"].strip()} <== ##\r\n'
                episode_url = BASE_API_URL + f'episode/{episodes["id"]}?fields=song-events,questions'
                json_data = get_url_or_json_from_cache(episode_url, f'cache/{episodes["id"]}.json', use_cache)

                for songs_list in json_data['episode']['song_events']:
                    for artists_list in songs_list['song']['artists']:
                        songs_info += f'* Song: {artists_list["name"].strip()} - {songs_list["song"]["name"].strip()}\r\n'
                        if songs_list['song']['album']:
                            songs_info += f'  Album: {songs_list["song"]["album"].strip()}\r\n'
                        if songs_list['description']:
                            songs_info += f'  Description: {songs_list["description"].strip()}\r\n'

    print('Parsing done. Saving result to file')

    with open(f'result/{show_name}.md', 'w', encoding='utf-8') as f:
        f.write(songs_info)


def main():
    parser = argparse.ArgumentParser(description='Parse OST for TV shows from tunefind', prefix_chars='-/')
    parser.add_argument('showname', type=str, help='show name from tunefind url')
    parser.add_argument('--cache', '--c', default=True, action=argparse.BooleanOptionalAction, help='use cache or not?')
    args = parser.parse_args()
    show_name = args.showname
    use_cache = args.cache

    if show_name == '' or show_name is None:
        print('Show name is required')
        exit()

    os.makedirs('cache', exist_ok=True)
    os.makedirs('result', exist_ok=True)

    seasons_cnt = get_seasons_cnt(show_name)
    get_episodes(show_name, seasons_cnt, use_cache)


if __name__ == "__main__":
    main()
