#!/usr/bin/python3
import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, quote

import requests
from requests.exceptions import RequestException

BASE_URL = 'https://www.tunefind.com'
SEARCH_URL = f'{BASE_URL}/search'

CACHE_DIR = Path('cache')
RESULT_DIR = Path('result')
LOG_DIR = Path('logs')

# Settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.2
CACHE_TTL = 7 * 24 * 3600
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

logger = logging.getLogger('tunefind')

def setup_logging(verbose: bool = False):
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    log_fmt = '%(asctime)s | %(levelname)-8s | %(message)s'
    
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(logging.Formatter(log_fmt, datefmt='%H:%M:%S'))
    logger.addHandler(ch)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / f"tunefind_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fh)
    except OSError as e:
        print(f"Warning: Could not write to log file: {e}", file=sys.stderr)

def validate_input(identifier: str) -> tuple[str, str]:
    if not identifier:
        raise ValueError("Identifier cannot be empty")

    if identifier.startswith('http'):
        parsed = urlparse(identifier)
        if parsed.netloc not in ['www.tunefind.com', 'tunefind.com']:
            raise ValueError(f"Invalid domain: {parsed.netloc}")
        
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) < 2:
            raise ValueError("URL path too short (e.g. /show/name)")
        
        content_type = path_parts[0]
        slug = path_parts[1]
    elif '/' in identifier:
        parts = identifier.split('/', 1)
        content_type, slug = parts
    else:
        content_type, slug = 'show', identifier

    if content_type not in ['show', 'movie']:
        raise ValueError(f"Invalid type: '{content_type}'. Must be 'show' or 'movie'.")

    if not re.match(r'^[a-z0-9\-]+$', slug):
        raise ValueError(f"Invalid slug format: '{slug}'. Only latin letters, numbers and hyphens allowed.")

    return content_type, slug

def safe_request(url: str) -> requests.Response | None:
    logger.debug(f"Requesting: {url}")
    try:
        response = requests.get(
            url, 
            timeout=REQUEST_TIMEOUT,
            headers={'User-Agent': USER_AGENT}
        )
        if response.status_code == 404:
            logger.error("Page not found (404)")
            return None
        if response.status_code == 403:
            logger.error("Access Denied (403). Maybe Cloudflare protection?")
            return None
        response.raise_for_status()
        return response
    except RequestException as e:
        logger.error(f"Network Error: {e}")
        return None

def get_json_cached(url: str, use_cache: bool = True) -> dict | None:
    safe_name = re.sub(r'[^\w\-]', '_', url)[:100]
    cache_file = CACHE_DIR / f"{safe_name}.json"

    if use_cache and cache_file.exists():
        try:
            mtime = cache_file.stat().st_mtime
            if (time.time() - mtime) < CACHE_TTL:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"Loaded from cache: {cache_file.name}")
                    return data
            else:
                logger.debug("Cache expired")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Cache read error: {e}")

    response = safe_request(url)
    if not response:
        return None

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON response")
        return None

    if use_cache:
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved to cache: {cache_file.name}")
        except IOError as e:
            logger.warning(f"Cache write error: {e}")

    return data

def search(query: str) -> list[dict] | None:
    url = f"{SEARCH_URL}?query={quote(query)}&_data=routes%2Fsearch"
    data = get_json_cached(url)
    if not data or 'searchResult' not in data:
        return []

    entries = data['searchResult'].get('searchEntries', [])
    return [e for e in entries if e.get('type') in ['show', 'movie']]

def parse_show_songs(data: dict) -> str:
    api = data.get('apiData')
    if not api:
        logger.error("Missing 'apiData' in show response")
        return ""

    seasons = api.get('parents', [])
    if not seasons:
        logger.warning("No seasons found")
        return ""

    output = []
    
    for season in seasons:
        s_name = season.get('name', 'Season 0')
        s_num = s_name.split()[-1]
        season_id = season.get('id')
        season_url = f"{BASE_URL}/show/{slug_placeholder}/season-{s_num}?_data=routes%2Fshow.%24mediaId.%24season"
        pass 

    return "" 

def get_show_data(slug: str) -> dict | None:
    url = f"{BASE_URL}/show/{slug}?_data=routes%2Fshow.%24mediaId"
    return get_json_cached(url)

def get_season_episodes(slug: str, season_num: str) -> dict | None:
    url = f"{BASE_URL}/show/{slug}/season-{season_num}?_data=routes%2Fshow.%24mediaId.%24season"
    return get_json_cached(url)

def get_episode_songs(slug: str, season_num: str, ep_id: str) -> list[dict] | None:
    url = f"{BASE_URL}/show/{slug}/season-{season_num}/{ep_id}?_data=routes%2Fshow.%24mediaId.%24season_.%24episode.%24"
    data = get_json_cached(url)
    if data:
        return data.get('apiData', {}).get('songs', [])
    return []

def get_movie_songs(slug: str) -> list[dict] | None:
    url = f"{BASE_URL}/movie/{slug}?_data=routes%2Fmovie.%24mediaId.%24"
    data = get_json_cached(url)
    if data:
        return data.get('apiData', {}).get('songs', [])
    return []

def format_song(song: dict) -> str:
    artists = ", ".join([a.get('name', '?') for a in song.get('artists', [])])
    name = song.get('name', 'Unknown Title')
    desc = song.get('description', '').strip()
    
    lines = [f"- **{artists}** — _{name}_"]
    if desc:
        lines.append(f"  > {desc}")
    return "\n".join(lines)

def scrape_show(slug: str) -> str:
    logger.info(f"Scanning show: {slug}")
    
    show_info = get_show_data(slug)
    if not show_info:
        return ""

    seasons = show_info.get('apiData', {}).get('parents', [])
    if not seasons:
        logger.warning("No seasons found in API response")
        return ""

    md_content = [f"# {slug} (Show)\n"]

    for season in seasons:
        s_num_raw = season.get('name', 'Season 0').split()[-1]
        s_num = int(s_num_raw) if s_num_raw.isdigit() else 0
        if s_num == 0: continue

        logger.info(f"  -> Season {s_num}")
        season_data = get_season_episodes(slug, str(s_num))
        if not season_data:
            continue

        episodes = season_data.get('apiData', {}).get('children', [])
        if not episodes:
            logger.warning(f"  No episodes found for Season {s_num}")
            continue

        md_content.append(f"\n## Season {s_num}\n")

        for ep in episodes:
            ep_name = ep.get('name', f'Episode {ep.get("id", "?")}')
            ep_id = ep.get('id')
            if not ep_id: continue

            logger.debug(f"    - Episode: {ep_name}")
            md_content.append(f"\n### {ep_name}\n")

            songs = get_episode_songs(slug, str(s_num), str(ep_id))
            if songs:
                for song in songs:
                    md_content.append(format_song(song))
            else:
                md_content.append("_No songs found_")
        
        time.sleep(REQUEST_DELAY)

    return "\n".join(md_content)

def scrape_movie(slug: str) -> str:
    logger.info(f"Scanning movie: {slug}")
    songs = get_movie_songs(slug)
    
    if not songs:
        return ""

    md_content = [f"# {slug} (Movie)\n"]
    for song in songs:
        md_content.append(format_song(song))

    return "\n".join(md_content)

slug_placeholder = ""

def main():
    global slug_placeholder
    
    parser = argparse.ArgumentParser(description='Tunefind OST Downloader')
    parser.add_argument('identifier', nargs='?', help='URL, slug, or type/slug')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-cache', action='store_true', help='Disable caching')
    parser.add_argument('-s', '--search', action='store_true', help='Search mode')
    
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    
    use_cache = not args.no_cache
    
    try:
        content_type = "show"
        slug = ""

        if args.search or (not args.identifier):
            query = input("Enter search query: ").strip()
            if not query:
                logger.info("Search cancelled")
                sys.exit(0)
            
            results = search(query)
            if not results:
                logger.info("Nothing found")
                sys.exit(0)
            
            print("\nFound results:")
            for i, r in enumerate(results, 1):
                print(f"{i}. [{r['type']}] {r['title']} ({r.get('url', '')})")
            
            choice = input("\nSelect number: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(results):
                selected = results[int(choice)-1]
                content_type = selected['type']
                parts = selected['url'].split('/')
                slug = parts[-1] if parts else ""
            else:
                logger.info("Invalid choice")
                sys.exit(0)
        
        else:
            content_type, slug = validate_input(args.identifier)

        if not slug:
            logger.error("Could not determine slug")
            sys.exit(1)
        
        slug_placeholder = slug
        logger.info(f"Target: [{content_type}] {slug}")

        result_text = ""
        if content_type == 'movie':
            result_text = scrape_movie(slug)
        else:
            result_text = scrape_show(slug)

        if result_text:
            RESULT_DIR.mkdir(exist_ok=True)
            out_file = RESULT_DIR / f"{slug}.md"
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(result_text)
            logger.info(f"Success! Saved to {out_file}")
        else:
            logger.error("Failed to fetch data or empty result")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Aborted by user")
        sys.exit(130)
    except ValueError as e:
        logger.error(f"Validation Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    main()
