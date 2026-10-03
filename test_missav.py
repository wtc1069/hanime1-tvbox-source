import sys
import types
import unittest

base = types.ModuleType('base')
base.spider = types.ModuleType('base.spider')
base.spider.Spider = type('Spider', (), {})
sys.modules.setdefault('base', base)
sys.modules.setdefault('base.spider', base.spider)

from missav_direct import HOST, MissavParser, Spider, video_id, video_source


LIST_HTML = '''
<div class="thumbnail group"><div class="relative"><a href="https://missav.ws/cn/abc-123">
  <video data-src="https://media.example/preview.mp4"></video>
  <img data-src="/cover.jpg" alt="Fallback"></a>
  <a href="/cn/abc-123"><span class="absolute bottom-1">1:01:55</span></a></div>
  <div class="my-2 truncate"><a href="/cn/abc-123">Sample &amp; title</a></div></div>
<div class="item-wrapper"><a href="/cn/new"><img src="/category.jpg"></a></div>
<a rel="next" href="?page=2">Next</a>
'''
DETAIL_HTML = '''
<meta property="og:title" content="Sample">
<meta property="og:image" content="/poster.jpg">
<meta property="og:description" content="Description">
<video><source src="https://media.example/abc-123/playlist.m3u8?token=a&amp;b=2"></video>
'''


class MissavTests(unittest.TestCase):
    def setUp(self):
        self.spider = Spider()
        self.spider.init()
        self.urls = []

        def fetch(url, **kwargs):
            self.urls.append(url)
            return types.SimpleNamespace(
                text=DETAIL_HTML if url.endswith('/abc-123') else LIST_HTML,
                raise_for_status=lambda: None)

        self.spider.fetch = fetch

    def test_list_and_categories(self):
        self.assertEqual(video_id('https://other.example/cn/abc-123'), '')
        self.assertEqual(video_id('/cn/new'), '')
        result = self.spider.categoryContent('new', '2', False, {})
        self.assertEqual(self.urls[-1], HOST + '/cn/new?page=2')
        self.assertEqual(result['list'][0], {
            'vod_id': 'abc-123', 'vod_name': 'Sample & title',
            'vod_pic': HOST + '/cover.jpg', 'vod_remarks': '1:01:55',
        })
        self.assertEqual(result['pagecount'], 3)
        self.assertEqual(self.spider.categoryContent('../bad', '1', False, {})['list'], [])

    def test_search_and_detail(self):
        self.spider.searchContent('abc test', False)
        self.assertEqual(self.urls[-1], HOST + '/cn/search/abc%20test')
        detail = self.spider.detailContent(['abc-123'])['list'][0]
        self.assertEqual(detail['vod_name'], 'Sample')
        self.assertEqual(detail['vod_pic'], HOST + '/poster.jpg')
        self.assertEqual(detail['vod_play_url'], '正片$missav:abc-123')
        self.assertEqual(self.spider.detailContent(['../new']), {'list': []})

    def test_direct_playback(self):
        play = self.spider.playerContent('MissAV', 'missav:abc-123', [])
        self.assertEqual(play['parse'], 0)
        self.assertEqual(play['url'], 'https://media.example/abc-123/playlist.m3u8?token=a&b=2')
        self.assertEqual(self.spider.playerContent('MissAV', 'missav:../../bad', [])['url'], '')

    def test_uuid_playback_and_no_stream(self):
        uuid = '12345678-1234-1234-1234-123456789abc'
        self.assertEqual(video_source('<script>"uuid":"{}"</script>'.format(uuid), []),
                         'https://surrit.com/{}/playlist.m3u8'.format(uuid))
        self.assertEqual(video_source('<p>No video</p>', []), '')

    def test_parser_ignores_challenge_page(self):
        parser = MissavParser()
        parser.feed('<title>Just a moment...</title><div>Cloudflare</div>')
        self.assertEqual(parser.videos, [])
        self.spider.fetch = lambda url, **kwargs: types.SimpleNamespace(
            text='', raise_for_status=lambda: None)
        self.assertEqual(self.spider.detailContent(['abc-123']), {'list': []})

    def test_legacy_card_and_http_failure(self):
        parser = MissavParser()
        parser.feed('<div class="item-wrapper"><a href="/cn/old-123">'
                    '<img src="/old.jpg" alt="Old"></a></div>')
        self.assertEqual(parser.videos[0]['vod_id'], 'old-123')

        def rejected(url, **kwargs):
            return types.SimpleNamespace(text=LIST_HTML,
                                         raise_for_status=lambda: (_ for _ in ()).throw(Exception('403')))

        self.spider.fetch = rejected
        self.assertEqual(self.spider.homeVideoContent(), {'list': []})


if __name__ == '__main__':
    unittest.main()
