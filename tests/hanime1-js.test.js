const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'vendor/hanime1/js/hanime1.user.js'), 'utf8');
const site = JSON.parse(fs.readFileSync(path.join(root, 'box.json'), 'utf8'))
    .sites.find(item => item.key === 'Hanime1');

function element(attributes = {}, content = '', selectors = {}) {
    return {
        textContent: content,
        getAttribute: name => attributes[name] || '',
        querySelector: selector => selectors[selector] || null,
        querySelectorAll: selector => selectors[selector] || [],
    };
}

function documentWith(selectors = {}, collections = {}, title = 'Hanime1', html = '<html></html>') {
    return {
        title,
        readyState: 'complete',
        documentElement: {outerHTML: html},
        body: {innerText: ''},
        querySelector: selector => selectors[selector] || null,
        querySelectorAll: selector => collections[selector] || [],
        addEventListener: () => {},
    };
}

function run(method, document) {
    let result;
    const context = vm.createContext({
        document,
        location: {href: 'https://hanime1.me/search?genre=%E8%A3%8F%E7%95%AA'},
        window: {},
        performance: {getEntriesByType: () => []},
        setTimeout: () => { throw new Error('unexpected wait'); },
        GmSpiderInject: {
            GetSpiderArgs: () => JSON.stringify([method, ['123']]),
            SetSpiderResult: value => { result = JSON.parse(value); },
        },
    });
    vm.runInContext('Array.prototype.at = undefined', context);
    vm.runInContext(script, context);
    return result;
}

test('configuration uses the GM runtime and only hanime1.me endpoints', () => {
    assert.equal(site.api, 'csp_GM');
    assert.match(site.jar, /\/vendor\/cluntop\/jar\/gm\.jar$/);
    assert.match(site.ext.userScript, /\/vendor\/hanime1\/js\/hanime1\.user\.js\?v=[a-f0-9]+$/);
    assert.deepEqual(site.ext.playUrlMatch, [
        'https://vdownload.hembed.com/*.mp4*',
        'https://vdownload.hembed.com/*.m3u8*',
        'https://cdn.dreamserve.dev/video/*.mp4*',
        'https://cdn.dreamserve.dev/video/*.m3u8*',
    ]);
    for (const entry of Object.values(site.ext.spider)) {
        assert.match(entry.loadUrl, /^https:\/\/hanime1\.me\//);
    }
    assert.doesNotMatch(script, /\.at\(/);
});

test('homepage emits classes and parses video cards', () => {
    const link = element({href: '/watch?v=123', title: 'Fallback'});
    const image = element({src: 'https://cdn.example/cover.jpg', alt: 'Cover'});
    const card = element({}, '', {
        'a[href*="/watch"]': link,
        img: image,
        '.home-rows-videos-title, .card-mobile-title, .video-title, .title': element({}, 'Example title'),
        '.duration': element({}, '20:00'),
    });
    const result = run('homeContent', documentWith({}, {'.video-item-container': [card]}));
    assert.match(result.class[0].type_id, /^sort=/);
    assert.equal(result.list[0].vod_id, '123');
    assert.equal(result.list[0].vod_name, 'Example title');
    assert.equal(result.list[0].vod_remarks, '20:00');
});

test('detail returns playlist identifiers and player delegates media capture to GM', () => {
    const playlistLink = element({href: '/watch?v=456'});
    const playlistCard = element({}, '', {
        'a[href*="/watch"]': playlistLink,
        img: element({alt: 'Second episode'}),
        '.video-title, .card-mobile-title, .title': element({}, 'Second episode'),
    });
    const detail = documentWith({
        'meta[property="og:title"]': element({content: 'Current episode'}),
        'meta[property="og:image"]': element({content: 'https://cdn.example/cover.jpg'}),
        'meta[property="og:description"]': element({content: 'Description'}),
        h1: element({}, 'Current episode'),
    }, {
        '#video-playlist-wrapper .playlist-video-card, .video-playlist-wrapper .playlist-video-card, .related-watch-wrap': [playlistCard],
    });
    const detailResult = run('detailContent', detail);
    const media = detailResult.list[0].vod_play_data[0].media;
    assert.equal(media.map(item => item.name).join('#'), 'Second episode#Current episode');
    assert.deepEqual(media[0], {
        name: 'Second episode', type: 'webview', ext: {replace: {vod_id: '456'}}
    });
    const playerResult = run('playerContent', detail);
    assert.deepEqual(playerResult, {type: 'match'});
});

test('detail does not wait for a dynamically loaded video source', () => {
    const detail = documentWith({
        'meta[property="og:title"]': element({content: 'Current episode'}),
        'meta[property="og:image"]': element({content: 'https://cdn.example/cover.jpg'}),
    });
    const result = run('detailContent', detail);
    assert.equal(result.list[0].vod_id, '123');
});

test('player does not depend on cross-origin performance entries', () => {
    const result = run('playerContent', documentWith());
    assert.deepEqual(result, {type: 'match'});
});

test('challenge page returns URL for the generic App verification flow', () => {
    const result = run('homeContent', documentWith({}, {}, 'Just a moment...'));
    assert.equal(result.__tvbox_challenge_url, 'https://hanime1.me/search?genre=%E8%A3%8F%E7%95%AA');
});
