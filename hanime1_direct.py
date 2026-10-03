# -*- coding: utf-8 -*-
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlparse
import sys

sys.path.append('..')
from base.spider import Spider as BaseSpider


HOST = 'https://hanime1.me'
GENRES = ('裏番', '泡麵番', 'Motion Anime', '3D動畫', '同人作品', 'Cosplay')
RANKS = {
    'latest': '最新上市',
    'daily': '本日排行',
    'weekly': '本週排行',
    'monthly': '本月排行',
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.videos = []
        self.sources = []
        self.metadata = {}
        self.next_page = False
        self.card = None
        self.depth = 0
        self.title_depth = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'meta' and attrs.get('property') in ('og:title', 'og:image', 'og:description'):
            self.metadata[attrs['property']] = attrs.get('content', '')
        if tag == 'source' and attrs.get('type') == 'video/mp4' and attrs.get('src'):
            self.sources.append((attrs.get('size', ''), attrs['src']))
        if tag == 'a' and attrs.get('rel') == 'next':
            self.next_page = True
        if tag == 'a' and self.card is None:
            query = parse_qs(urlparse(attrs.get('href', '')).query)
            vid = query.get('v', [''])[0]
            if '/watch' in attrs.get('href', '') and vid.isdigit():
                self.card = {'vod_id': vid, 'vod_name': '', 'vod_pic': '', 'fallback_name': attrs.get('title', '')}
                self.depth = 1
                return
        if self.card is not None:
            if tag == 'a':
                self.depth += 1
            if tag == 'img' and not self.card['vod_pic']:
                self.card['vod_pic'] = attrs.get('src', '') or attrs.get('data-src', '') or attrs.get('data-original', '')
                self.card['fallback_name'] = self.card['fallback_name'] or attrs.get('alt', '')
            if 'home-rows-videos-title' in classes or 'card-mobile-title' in classes:
                self.title_depth = 1
            elif self.title_depth is not None and tag not in ('img', 'br', 'source'):
                self.title_depth += 1

    def handle_data(self, data):
        if self.card is not None and self.title_depth is not None:
            self.card['vod_name'] += data

    def handle_endtag(self, tag):
        if self.card is None:
            return
        if self.title_depth is not None and tag not in ('img', 'br', 'source'):
            self.title_depth -= 1
            if self.title_depth == 0:
                self.title_depth = None
        if tag == 'a':
            self.depth -= 1
            if self.depth == 0:
                self.card['vod_name'] = (self.card['vod_name'].strip() or self.card['fallback_name']).strip()
                if self.card['vod_name']:
                    del self.card['fallback_name']
                    self.videos.append(self.card)
                self.card = None
                self.title_depth = None


class Spider(BaseSpider):
    def init(self, extend=''):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36',
            'Referer': HOST + '/',
        }

    def getName(self):
        return 'Hanime1'

    def _page(self, path, params=None):
        url = HOST + path
        if params:
            url += '?' + urlencode(params)
        response = self.fetch(url, headers=self.headers)
        parser = PageParser()
        parser.feed(response.text)
        return parser

    def homeContent(self, filter):
        classes = [{'type_name': name, 'type_id': name} for name in GENRES]
        classes = [{'type_name': '最新上市', 'type_id': 'latest'}] + classes
        classes += [{'type_name': label, 'type_id': key} for key, label in RANKS.items() if key != 'latest']
        return {'class': classes}

    def homeVideoContent(self):
        return {'list': self._page('/search', {'genre': GENRES[0], 'sort': RANKS['latest']}).videos}

    def categoryContent(self, tid, pg, filter, extend):
        page = max(1, int(pg or '1'))
        params = {'page': page, 'genre': GENRES[0], 'sort': RANKS['latest']}
        if tid in RANKS:
            params['sort'] = RANKS[tid]
        elif tid in GENRES:
            params['genre'] = tid
        else:
            return {'list': [], 'page': page, 'pagecount': page}
        result = self._page('/search', params)
        return {'list': result.videos, 'page': page, 'pagecount': page + int(result.next_page)}

    def detailContent(self, ids):
        vid = str(ids[0])
        if not vid.isdigit():
            return {'list': []}
        result = self._page('/watch', {'v': vid})
        sources = sorted(result.sources, key=lambda item: int(item[0]) if item[0].isdigit() else 0, reverse=True)
        play = [f'{size}P${url}' for size, url in sources if url.startswith('https://')]
        return {'list': [{
            'vod_id': vid,
            'vod_name': result.metadata.get('og:title', ''),
            'vod_pic': result.metadata.get('og:image', ''),
            'vod_content': result.metadata.get('og:description', ''),
            'vod_play_from': 'Hanime1',
            'vod_play_url': '#'.join(play),
        }]}

    def searchContent(self, key, quick, pg='1', extend=None):
        page = max(1, int(pg or '1'))
        result = self._page('/search', {'query': key, 'genre': GENRES[0], 'page': page})
        return {'list': result.videos, 'page': page, 'pagecount': page + int(result.next_page)}

    def playerContent(self, flag, id, vipFlags):
        if urlparse(id).scheme != 'https':
            return {'parse': 0, 'url': ''}
        return {'parse': 0, 'url': id, 'header': self.headers}
