#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KhFree Data Scraper - Runs via GitHub Actions daily
Scrapes khdiamond.net RSS feeds server-side (no CORS/Cloudflare issues)
Saves to kh_data.json which khfree.html reads directly
"""
import json, sys, time, re, urllib.request, urllib.error
from xml.etree import ElementTree as ET
from datetime import datetime

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
BASE = 'https://khdiamond.net'

# RSS Feed URLs - use ASCII slugs where possible
FEEDS = {
    'movies':  f'{BASE}/movies/feed/',
    'tvshows': f'{BASE}/tvshows/feed/',
    'khdub':   f'{BASE}/genre/khdub/feed/',
    'free':    f'{BASE}/genre/%E1%9E%A5%E1%9E%8F%E1%9E%82%E1%9E%B7%E1%9E%8F%E1%9E%90%E1%9F%92%E1%9E%9B%E1%9F%83/feed/',
    'korea':   f'{BASE}/genre/korea-series/feed/',
    'china':   f'{BASE}/genre/china-series/feed/',
    'japan':   f'{BASE}/genre/japan/feed/',
    'anime':   f'{BASE}/genre/%E1%9E%97%E1%9E%B6%E1%9E%82-anime/feed/',
    'action':  f'{BASE}/genre/action/feed/',
    'horror':  f'{BASE}/genre/horror/feed/',
    'khsub':   f'{BASE}/genre/khsub/feed/',
    'romance': f'{BASE}/genre/romance/feed/',
}

NS = {
    'media': 'http://search.yahoo.com/mrss/',
    'content': 'http://purl.org/rss/1.0/modules/content/',
    'dc': 'http://purl.org/dc/elements/1.1/',
}

def fetch_url(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': UA,
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'no-cache',
            })
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode('utf-8', errors='replace')
        except Exception as e:
            print(f'  Attempt {attempt+1} failed: {e}', file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
    return None

def extract_img(text):
    if not text:
        return ''
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', text)
    return m.group(1) if m else ''

def extract_year(pub_date):
    if not pub_date:
        return ''
    m = re.search(r'\d{4}', pub_date)
    return m.group() if m else ''

def parse_feed(xml_text, tab):
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f'  XML parse error: {e}', file=sys.stderr)
        return items

    channel = root.find('channel')
    if channel is None:
        return items

    for item_el in channel.findall('item'):
        # Title
        title_el = item_el.find('title')
        title = (title_el.text or '').strip() if title_el is not None else ''
        title = re.sub(r'<[^>]+>', '', title).strip()
        if not title:
            continue

        # Link
        link_el = item_el.find('link')
        link = (link_el.text or '').strip() if link_el is not None else ''
        if not link:
            # Try guid
            guid_el = item_el.find('guid')
            link = (guid_el.text or '').strip() if guid_el is not None else ''

        # Type + Slug from link
        m = re.search(r'/(movies|tvshows)/([^/?#\s]+)', link)
        itype = m.group(1) if m else ('tvshows' if tab == 'tvshows' else 'movies')
        slug = m.group(2) if m else ''
        if not slug:
            continue

        # Poster - try media:thumbnail, media:content, enclosure, then description
        poster = ''
        mt = item_el.find('media:thumbnail', NS)
        if mt is not None:
            poster = mt.get('url', '')
        if not poster:
            mc = item_el.find('media:content', NS)
            if mc is not None:
                poster = mc.get('url', '')
        if not poster:
            enc = item_el.find('enclosure')
            if enc is not None:
                t = enc.get('type', '')
                if 'image' in t:
                    poster = enc.get('url', '')
        if not poster:
            desc_el = item_el.find('description')
            if desc_el is not None:
                poster = extract_img(desc_el.text or '')
        if not poster:
            # Try content:encoded
            ce = item_el.find('content:encoded', NS)
            if ce is not None:
                poster = extract_img(ce.text or '')

        # Ensure https
        if poster and poster.startswith('//'):
            poster = 'https:' + poster

        # Year
        pd_el = item_el.find('pubDate')
        year = extract_year(pd_el.text if pd_el is not None else '')

        # Rating
        rating = ''

        items.append({
            'id': slug,
            'type': itype,
            'slug': slug,
            'title': title,
            'poster': poster,
            'year': year,
            'rating': rating,
            'link': link,
        })

    return items

def main():
    print('=== KhFree Data Scraper ===', flush=True)
    result = {
        'updated': datetime.utcnow().isoformat() + 'Z',
        'tabs': {}
    }

    for tab, feed_url in FEEDS.items():
        print(f'\n[{tab}] Fetching: {feed_url}', flush=True)
        xml = fetch_url(feed_url)
        if not xml:
            print(f'  FAILED to fetch {tab}', file=sys.stderr)
            result['tabs'][tab] = []
            continue

        items = parse_feed(xml, tab)
        print(f'  Parsed {len(items)} items', flush=True)
        result['tabs'][tab] = items
        time.sleep(1.5)  # Be polite

    # Add 'all' = movies + tvshows merged, deduplicated by slug
    seen = set()
    all_items = []
    for tab in ('movies', 'tvshows'):
        for item in result['tabs'].get(tab, []):
            if item['slug'] not in seen:
                seen.add(item['slug'])
                all_items.append(item)
    result['tabs']['all'] = all_items

    total = sum(len(v) for v in result['tabs'].values())
    print(f'\nTotal items across all tabs: {total}', flush=True)

    with open('kh_data.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print('\n[OK] kh_data.json saved!', flush=True)
    print(f'   Tabs: {list(result["tabs"].keys())}', flush=True)

if __name__ == '__main__':
    main()
