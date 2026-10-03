# -*- coding: utf-8 -*-
import html
from html.parser import HTMLParser
import json
import re
import sys
from urllib.parse import quote, urljoin, urlparse

sys.path.append('..')
from base.spider import Spider as BaseSpider

try:
    from com.undcover.freedom.pyramid import PythonHttp
except ImportError:
    PythonHttp = None


HOST = 'https://missav.ws'
USER_AGENT = ('Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36')
CHANNELS = (
    ('new', '最近更新'), ('release', '新作上市'),
    ('chinese-subtitle', '中文字幕'), ('uncensored-leak', '无码流出'),
    ('fc2', 'FC2'), ('genres/VR', 'VR'),
)
SLUG = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{2,}\Z')
MEDIA = re.compile(r'https?://[^\s"\'<>]+?\.(?:m3u8|mp4)(?:\?[^\s"\'<>]*)?', re.I)
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', re.I)
NON_VIDEOS = {'new', 'release', 'search', 'genres', 'actresses', 'actors',
              'makers', 'directors', 'labels', 'fc2', 'today-hot', 'weekly-hot',
              'monthly-hot', 'chinese-subtitle', 'uncensored-leak'}


def video_id(href):
    parsed = urlparse(href)
    if parsed.netloc and parsed.netloc.lower() != 'missav.ws':
        return ''
    parts = parsed.path.strip('/').split('/')
    return (parts[1] if len(parts) == 2 and parts[0] == 'cn'
            and SLUG.fullmatch(parts[1]) and parts[1].lower() not in NON_VIDEOS else '')


class MissavParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.videos = []
        self.metadata = {}
        self.sources = []
        self.next_page = False
        self.depth = 0
        self.card_depth = None
        self.card = None
        self.capture = None
        self.capture_tag = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get('class', '').split()
        if tag == 'div':
            self.depth += 1
            if self.card is None and ('item-wrapper' in classes or 'thumbnail' in classes):
                self.card_depth = self.depth
                self.card = {'vod_id': '', 'vod_name': '', 'vod_pic': '',
                             'vod_remarks': '', 'fallback': ''}
        if tag == 'meta' and attrs.get('property') in ('og:title', 'og:image', 'og:description'):
            self.metadata[attrs['property']] = attrs.get('content', '')
        if tag in ('source', 'video') and attrs.get('src'):
            self.sources.append(attrs['src'])
        if tag == 'a' and attrs.get('rel') == 'next':
            self.next_page = True
        if self.card is None:
            return
        if tag == 'a':
            self.card['vod_id'] = self.card['vod_id'] or video_id(attrs.get('href', ''))
        if 'truncate' in classes and self.capture is None:
            self.capture, self.capture_tag = 'vod_name', tag
        if tag == 'img':
            pic = attrs.get('data-src') or attrs.get('data-original') or attrs.get('src') or ''
            if pic and not pic.startswith('data:') and 'loading' not in pic:
                self.card['vod_pic'] = self.card['vod_pic'] or urljoin(HOST, pic)
            self.card['fallback'] = self.card['fallback'] or attrs.get('alt', '')
        if tag == 'span' and 'absolute' in classes:
            self.capture, self.capture_tag = 'vod_remarks', tag

    def handle_data(self, data):
        if self.card is not None and self.capture:
            self.card[self.capture] += data

    def handle_endtag(self, tag):
        if self.card is not None and tag == self.capture_tag:
            self.capture = self.capture_tag = None
        if tag == 'div':
            if self.card is not None and self.depth == self.card_depth:
                self.card['vod_name'] = (self.card['vod_name'].strip()
                                         or self.card['fallback'].strip() or self.card['vod_id'])
                self.card['vod_remarks'] = self.card['vod_remarks'].strip()
                if self.card['vod_id']:
                    self.card.pop('fallback')
                    self.videos.append(self.card)
                self.card = None
                self.card_depth = None
                self.capture = self.capture_tag = None
            self.depth = max(0, self.depth - 1)


def video_source(page, sources):
    text = html.unescape(page).replace('\\/', '/')
    for source in sources + MEDIA.findall(text):
        url = urljoin(HOST, html.unescape(source).replace('\\/', '/'))
        if urlparse(url).scheme == 'https' and MEDIA.match(url):
            return url
    match = re.search(r'surrit\.com/(' + UUID.pattern + r')', text, re.I)
    if match:
        return 'https://surrit.com/{}/playlist.m3u8'.format(match.group(1))
    match = re.search(r'["\']uuid["\']\s*[:=]\s*["\'](' + UUID.pattern + r')["\']', text, re.I)
    return ('https://surrit.com/{}/playlist.m3u8'.format(match.group(1)) if match else '')


class Spider(BaseSpider):
    def init(self, extend=''):
        self.headers = {'User-Agent': USER_AGENT, 'Referer': HOST + '/'}

    def getName(self):
        return 'MissAV'

    def _page(self, path):
        try:
            url = HOST + path
            if PythonHttp is not None:
                result = json.loads(str(PythonHttp.request(
                    'GET', url, json.dumps(self.headers), '', True)))
                if result.get('error'):
                    raise RuntimeError(result['error'])
                if result.get('status_code') != 200:
                    raise RuntimeError('HTTP {}'.format(result.get('status_code')))
                page = result.get('text', '')
            else:
                response = self.fetch(url, headers=self.headers, timeout=20)
                response.raise_for_status()
                page = response.text
        except Exception as exc:
            print('MissAV request failed for {}: {}'.format(path, exc), file=sys.stderr)
            page = ''
        parser = MissavParser()
        parser.feed(page)
        return parser, page

    def homeContent(self, filter):
        return {'class': [{'type_id': key, 'type_name': name} for key, name in CHANNELS]}

    def homeVideoContent(self):
        return {'list': self._page('/cn/new')[0].videos[:24]}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or 1))
        if tid not in dict(CHANNELS):
            return {'list': [], 'page': page, 'pagecount': page}
        path = '/cn/' + tid + ('?page={}'.format(page) if page > 1 else '')
        result, _ = self._page(path)
        return {'list': result.videos, 'page': page,
                'pagecount': page + int(result.next_page or len(result.videos) >= 12)}

    def searchContent(self, key, quick, pg='1', extend=None):
        page = max(1, int(pg or 1))
        path = '/cn/search/' + quote(str(key), safe='')
        if page > 1:
            path += '?page={}'.format(page)
        result, _ = self._page(path)
        return {'list': result.videos, 'page': page,
                'pagecount': page + int(result.next_page or len(result.videos) >= 12)}

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ''
        if not SLUG.fullmatch(vid) or vid.lower() in NON_VIDEOS:
            return {'list': []}
        result, page = self._page('/cn/' + quote(vid, safe=''))
        if not page or 'cf-challenge' in page or '_cf_chl_opt' in page:
            return {'list': []}
        title = result.metadata.get('og:title', '') or vid
        return {'list': [{
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': (urljoin(HOST, result.metadata['og:image'])
                        if result.metadata.get('og:image') else ''),
            'vod_content': result.metadata.get('og:description', ''),
            'vod_play_from': 'MissAV',
            'vod_play_url': '正片$missav:' + vid,
        }]}

    def playerContent(self, flag, id, vipFlags):
        vid = str(id)
        if vid.startswith('missav:'):
            vid = vid[len('missav:'):]
        if not SLUG.fullmatch(vid) or vid.lower() in NON_VIDEOS:
            return {'parse': 0, 'url': ''}
        parser, page = self._page('/cn/' + quote(vid, safe=''))
        url = video_source(page, parser.sources) if page and '_cf_chl_opt' not in page else ''
        return {'parse': 0, 'url': url,
                'header': {'User-Agent': USER_AGENT, 'Referer': HOST + '/cn/' + vid}}
