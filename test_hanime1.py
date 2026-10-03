import sys
import types
import unittest
import json
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

base = types.ModuleType('base')
base.spider = types.ModuleType('base.spider')
base.spider.Spider = type('Spider', (), {})
sys.modules.setdefault('base', base)
sys.modules.setdefault('base.spider', base.spider)

from hanime1_direct import HOST, PageParser, Spider


LIST_HTML = '''
<a href="?genre=x&amp;page=2" rel="next">Next</a>
<div class="home-rows-videos-wrapper">
<a href="https://hanime1.me/watch?v=123">
  <img src="https://example.com/cover.jpg">
  <div class="home-rows-videos-title">Example &amp; more</div>
</a>
</div>
'''
DETAIL_HTML = '''
<meta property="og:title" content="Example">
<meta property="og:image" content="https://example.com/cover.jpg">
<meta property="og:description" content="Description">
<video><source src="https://hanime1.me/videos/123-480.mp4?key=abc" type="video/mp4" size="480">
<source src="https://hanime1.me/videos/123-720.mp4?key=abc" type="video/mp4" size="720"></video>
<div id="video-playlist-wrapper">
  <h4><a href="/playlist?v=42">清單 Example</a></h4>
  <div class="playlist-video-card"><a href="/watch?v=456"><img alt="Second"></a>
    <h4 class="video-title">Second episode</h4></div>
  <div class="playlist-video-card"><a href="/watch?v=123"><img alt="First"></a>
    <h4 class="video-title">First episode</h4></div>
  <div class="playlist-video-card"><a href="/watch?v=456"><img alt="Duplicate"></a></div>
</div>
'''
SECOND_HTML = '''<video><source src="https://hanime1.me/videos/456-480.mp4" type="video/mp4" size="480">
<source src="https://hanime1.me/videos/456-1080.mp4" type="video/mp4" size="1080"></video>'''


class SpiderTests(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()
        self.urls = []

        def fetch(url, headers):
            self.urls.append(url)
            if parse_qs(urlparse(url).query).get('v') == ['456']:
                return types.SimpleNamespace(text=SECOND_HTML)
            return types.SimpleNamespace(text=DETAIL_HTML if '/watch?' in url else LIST_HTML)

        self.spider.fetch = fetch

    def test_category_and_home(self):
        home = self.spider.homeContent(True)
        self.assertIn('AI生成', [item['type_id'] for item in home['class']])
        self.assertIn('最新上傳', [item['v'] for item in home['filters']['裏番'][0]['value']])
        data = self.spider.categoryContent('裏番', '1', False, {})
        self.assertEqual(data['list'][0]['vod_id'], '123')
        self.assertEqual(data['list'][0]['vod_name'], 'Example & more')
        self.assertEqual(data['pagecount'], 2)
        self.assertEqual(urlparse(self.urls[-1]).netloc, 'hanime1.me')
        self.assertEqual(parse_qs(urlparse(self.urls[-1]).query)['genre'], ['裏番'])
        self.assertEqual(len(self.spider.homeVideoContent()['list']), 1)

    def test_sort_filter_and_rank_without_genre(self):
        self.spider.categoryContent('裏番', '2', True, {'sort': '觀看次數'})
        params = parse_qs(urlparse(self.urls[-1]).query)
        self.assertEqual(params['sort'], ['觀看次數'])
        self.assertEqual(params['page'], ['2'])
        self.spider.categoryContent('weekly', '1', True, {'sort': '觀看次數'})
        params = parse_qs(urlparse(self.urls[-1]).query)
        self.assertEqual(params['sort'], ['本週排行'])
        self.assertNotIn('genre', params)

    def test_video_item_card_title_and_duration(self):
        parser = PageParser()
        parser.feed('''<div class="video-item-container"><a href="/watch?v=789">
        <img data-src="https://example.com/pic.jpg"></a><span class="duration">16:22</span>
        <div class="title">Episode &amp; More</div></div>''')
        self.assertEqual(parser.videos, [{
            'vod_id': '789', 'vod_name': 'Episode & More',
            'vod_pic': 'https://example.com/pic.jpg', 'vod_remarks': '16:22'
        }])

    def test_search_requires_genre(self):
        data = self.spider.searchContent('example', False)
        self.assertEqual(len(data['list']), 1)
        params = parse_qs(urlparse(self.urls[-1]).query)
        self.assertEqual(params['genre'], ['裏番'])
        self.assertEqual(params['query'], ['example'])

    def test_detail_and_player(self):
        vod = self.spider.detailContent(['123'])['list'][0]
        self.assertEqual(vod['vod_name'], 'Example')
        self.assertTrue(vod['vod_play_url'].startswith('Second episode$hanime1:456#First episode$'))
        self.assertEqual(len(vod['vod_play_url'].split('#')), 2)
        self.assertIn('First episode$hanime1:123', vod['vod_play_url'])
        self.assertEqual(len(self.urls), 1)
        current = self.spider.playerContent('Hanime1', 'hanime1:123', [])
        self.assertIn('123-720.mp4', current['url'])
        self.assertEqual(len(self.urls), 1)
        play = self.spider.playerContent('Hanime1', 'hanime1:456', [])
        self.assertEqual(play['parse'], 0)
        self.assertIn('456-1080.mp4', play['url'])
        self.assertEqual(play['header']['Referer'], 'https://hanime1.me/')
        self.assertEqual(len(self.urls), 2)

    def test_without_playlist_uses_current_video_only(self):
        self.spider.fetch = lambda url, headers: types.SimpleNamespace(text='''
        <meta property="og:title" content="Solo">
        <a href="/watch?v=999">Related video</a>
        <source src="https://hanime1.me/videos/123-480.mp4" type="video/mp4" size="480">
        ''')
        vod = self.spider.detailContent(['123'])['list'][0]
        self.assertEqual(vod['vod_play_url'], 'Solo$hanime1:123')

    def test_legacy_playlist_and_missing_stream(self):
        self.spider.fetch = lambda url, headers: types.SimpleNamespace(text='''
        <meta property="og:title" content="Current">
        <div class="video-playlist-wrapper"><div class="related-watch-wrap">
          <a href="/watch?v=456"><img alt="Legacy episode"></a>
        </div></div>
        ''')
        vod = self.spider.detailContent(['123'])['list'][0]
        self.assertEqual(vod['vod_play_url'], 'Legacy episode$hanime1:456#Current$hanime1:123')
        self.assertEqual(self.spider.playerContent('Hanime1', 'hanime1:456', [])['url'], '')

    def test_rejects_invalid_detail_id(self):
        self.assertEqual(self.spider.detailContent(['not-an-id']), {'list': []})
        self.assertEqual(self.urls, [])
        self.assertEqual(self.spider.playerContent('Hanime1', 'http://example.com/video.mp4', [])['url'], '')
        self.assertEqual(self.spider.playerContent('Hanime1', 'hanime1:abc', [])['url'], '')

    def test_card_title_falls_back_to_image_alt(self):
        parser = PageParser()
        parser.feed('<a href="/watch?v=456"><img data-src="/cover.jpg" alt="Fallback title"></a>')
        self.assertEqual(parser.videos, [{
            'vod_id': '456', 'vod_name': 'Fallback title', 'vod_pic': '/cover.jpg', 'vod_remarks': ''
        }])

    def test_first_page_reuses_parsed_home_result(self):
        self.spider.homeVideoContent()
        self.spider.categoryContent('裏番', '1', False, {})
        self.assertEqual(len(self.urls), 1)

    def test_config_busts_cached_python_script(self):
        sites = json.loads(Path(__file__).with_name('box.json').read_text(encoding='utf-8'))['sites']
        python_site = next(site for site in sites if site['key'] == 'hanime1_direct.py')
        self.assertIn('/hanime1_direct.py?v=', python_site['api'])

    def test_watch_cache_expires_and_does_not_store_challenge(self):
        with patch('hanime1_direct.monotonic', return_value=100):
            self.spider.detailContent(['123'])
            self.spider.detailContent(['123'])
        self.assertEqual(len(self.urls), 1)
        with patch('hanime1_direct.monotonic', return_value=121):
            self.spider.detailContent(['123'])
        self.assertEqual(len(self.urls), 2)

        self.spider.fetch = lambda url, headers: types.SimpleNamespace(text='''
            <title>Just a moment...</title><div id="cf-challenge-running"></div>
        ''')
        self.spider.detailContent(['456'])
        self.spider.detailContent(['456'])
        self.assertNotIn(('/watch', (('v', '456'),)), self.spider._pages)


if __name__ == '__main__':
    unittest.main()
