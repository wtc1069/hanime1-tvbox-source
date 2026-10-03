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


def watch_id(href):
    parsed = urlparse(href)
    if parsed.netloc and parsed.netloc != 'hanime1.me':
        return ''
    vid = parse_qs(parsed.query).get('v', [''])[0]
    return vid if parsed.path == '/watch' and vid.isdigit() else ''


class PlaylistParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.div_depth = 0
        self.wrapper_depth = None
        self.card_depth = None
        self.card = None
        self.title_tag = None
        self.anchor_text = ''
        self.in_anchor = False

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get('class', '').split()
        if tag == 'div':
            self.div_depth += 1
            if self.wrapper_depth is None and (
                attrs.get('id') == 'video-playlist-wrapper' or 'video-playlist-wrapper' in classes
            ):
                self.wrapper_depth = self.div_depth
            elif self.wrapper_depth is not None and self.card is None and (
                'playlist-video-card' in classes or 'video-item-container' in classes
                or 'related-watch-wrap' in classes
            ):
                self.card_depth = self.div_depth
                self.card = {'id': '', 'title': '', 'fallback': ''}
        if self.card is None:
            return
        if tag == 'a':
            vid = watch_id(attrs.get('href', ''))
            if vid:
                self.card['id'] = vid
                self.card['fallback'] = self.card['fallback'] or attrs.get('title', '')
                self.in_anchor = True
                self.anchor_text = ''
        if tag == 'img':
            self.card['fallback'] = self.card['fallback'] or attrs.get('alt', '')
        if (tag == 'h4' and 'video-title' in classes) or ('card-mobile-title' in classes):
            self.title_tag = tag

    def handle_data(self, data):
        if self.card is not None:
            if self.title_tag:
                self.card['title'] += data
            if self.in_anchor:
                self.anchor_text += data

    def handle_endtag(self, tag):
        if self.card is not None:
            if tag == self.title_tag:
                self.title_tag = None
            if tag == 'a' and self.in_anchor:
                self.card['fallback'] = self.card['fallback'] or self.anchor_text.strip()
                self.in_anchor = False
        if tag == 'div':
            if self.card_depth == self.div_depth:
                if self.card['id']:
                    title = self.card['title'].strip() or self.card['fallback'].strip() or self.card['id']
                    self.entries.append((self.card['id'], title))
                self.card = None
                self.card_depth = None
                self.title_tag = None
            if self.wrapper_depth == self.div_depth:
                self.wrapper_depth = None
            self.div_depth = max(0, self.div_depth - 1)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.videos = []
        self.sources = []
        self.metadata = {}
        self.next_page = False
        self.playlist = []
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
        if path == '/watch':
            playlist = PlaylistParser()
            playlist.feed(response.text)
            parser.playlist = playlist.entries
        return parser

    @staticmethod
    def _best_source(sources):
        valid = [(size, url) for size, url in sources if urlparse(url).scheme == 'https']
        return max(valid, key=lambda item: int(item[0]) if item[0].isdigit() else 0)[1] if valid else ''

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
        entries = result.playlist or [(vid, result.metadata.get('og:title', '') or vid)]
        if vid not in {item_id for item_id, _ in entries}:
            entries.append((vid, result.metadata.get('og:title', '') or vid))
        seen = set()
        play = []
        for item_id, title in entries:
            if item_id in seen:
                continue
            seen.add(item_id)
            name = title.replace('#', ' ').replace('$', ' ').strip() or item_id
            target = self._best_source(result.sources) if item_id == vid else ''
            play.append(f'{name}${target or "hanime1:" + item_id}')
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
        if id.startswith('hanime1:'):
            vid = id[len('hanime1:'):]
            if not vid.isdigit():
                return {'parse': 0, 'url': ''}
            result = self._page('/watch', {'v': vid})
            id = self._best_source(result.sources)
        if urlparse(id).scheme != 'https':
            return {'parse': 0, 'url': ''}
        return {'parse': 0, 'url': id, 'header': self.headers}
