import sys
import types
import unittest
from urllib.parse import parse_qs, urlparse

base = types.ModuleType('base')
base.spider = types.ModuleType('base.spider')
base.spider.Spider = type('Spider', (), {})
sys.modules.setdefault('base', base)
sys.modules.setdefault('base.spider', base.spider)

from hanime1 import HOST, Spider


LIST_HTML = '''
<a href="?genre=x&amp;page=2" rel="next">Next</a>
<div class="home-rows-videos-wrapper">
<a href="https://www.hanime163.com/watch?v=123">
  <img src="https://example.com/cover.jpg">
  <div class="home-rows-videos-title">Example &amp; more</div>
</a>
</div>
'''
DETAIL_HTML = '''
<meta property="og:title" content="Example">
<meta property="og:image" content="https://example.com/cover.jpg">
<meta property="og:description" content="Description">
<video><source src="https://www.hanime163.com/jmpres/123-480.mp4?key=abc" type="video/mp4" size="480">
<source src="https://www.hanime163.com/jmpres/123-720.mp4?key=abc" type="video/mp4" size="720"></video>
'''


class SpiderTests(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()
        self.urls = []

        def fetch(url, headers):
            self.urls.append(url)
            return types.SimpleNamespace(text=DETAIL_HTML if '/watch?' in url else LIST_HTML)

        self.spider.fetch = fetch

    def test_category_and_home(self):
        data = self.spider.categoryContent('裏番', '1', False, {})
        self.assertEqual(data['list'][0]['vod_id'], '123')
        self.assertEqual(data['list'][0]['vod_name'], 'Example & more')
        self.assertEqual(data['pagecount'], 2)
        self.assertEqual(parse_qs(urlparse(self.urls[-1]).query)['genre'], ['裏番'])
        self.assertEqual(len(self.spider.homeVideoContent()['list']), 1)

    def test_search_requires_genre(self):
        data = self.spider.searchContent('example', False)
        self.assertEqual(len(data['list']), 1)
        params = parse_qs(urlparse(self.urls[-1]).query)
        self.assertEqual(params['genre'], ['裏番'])
        self.assertEqual(params['query'], ['example'])

    def test_detail_and_player(self):
        vod = self.spider.detailContent(['123'])['list'][0]
        self.assertEqual(vod['vod_name'], 'Example')
        self.assertTrue(vod['vod_play_url'].startswith('720P$'))
        self.assertEqual(len(vod['vod_play_url'].split('#')), 2)
        url = vod['vod_play_url'].split('$', 1)[1].split('#')[0]
        play = self.spider.playerContent('Hanime1', url, [])
        self.assertEqual(play['parse'], 0)
        self.assertEqual(play['header']['Referer'], HOST + '/')

    def test_rejects_invalid_detail_id(self):
        self.assertEqual(self.spider.detailContent(['not-an-id']), {'list': []})
        self.assertEqual(self.urls, [])


if __name__ == '__main__':
    unittest.main()
