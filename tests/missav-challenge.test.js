const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const script = fs.readFileSync(path.join(__dirname, '../vendor/cluntop/js/missav.user.js'), 'utf8');
const site = JSON.parse(fs.readFileSync(path.join(__dirname, '../box.json'), 'utf8'))
    .sites.find(item => item.key === 'MissAV');

test('configuration uses missav.ai for every page', () => {
    for (const entry of Object.values(site.ext.spider)) {
        assert.match(entry.loadUrl, /^https:\/\/missav\.ai\/cn\//);
    }
});

function runPage(title, html, selectorMatch = false, bodyText = '', method = 'categoryContent') {
    let response;
    const document = {
        title,
        documentElement: {outerHTML: html},
        body: {innerText: bodyText},
        querySelector: () => selectorMatch ? {} : null,
    };
    const $ = target => target === document ? {ready: fn => fn()} : {
        text: () => '',
        each: () => {},
    };
    vm.runInNewContext(script, {
        GM_info: {},
        GmSpiderInject: {
            GetSpiderArgs: () => JSON.stringify([method, 'new', 1, true, {}]),
            SetSpiderResult: json => { response = JSON.parse(json); },
        },
        document,
        location: {href: 'https://missav.ai/cn/new?page=1'},
        window: {},
        $,
        console: {log: () => {}},
    });
    return response;
}

test('challenge page returns URL for verification', () => {
    assert.equal(runPage('Just a moment...', '<html></html>')['__tvbox_challenge_url'],
        'https://missav.ai/cn/new?page=1');
    assert.equal(runPage('Verify you are human', '<html></html>')['__tvbox_challenge_url'],
        'https://missav.ai/cn/new?page=1');
    assert.equal(runPage('MissAV', '<html></html>', true)['__tvbox_challenge_url'],
        'https://missav.ai/cn/new?page=1');
    assert.equal(runPage('Just a moment...', '<html></html>', false, '', 'homeContent')['__tvbox_challenge_url'],
        'https://missav.ai/cn/new?page=1');
    assert.equal(runPage('MissAV', '<script src="/cdn-cgi/challenge-platform/a"></script>', false,
        'Checking if the site connection is secure')['__tvbox_challenge_url'],
        'https://missav.ai/cn/new?page=1');
});

test('ordinary page does not request verification', () => {
    const result = runPage('MissAV', '<script src="https://challenges.cloudflare.com/turnstile/v0/api.js"></script>');
    assert.equal(result['__tvbox_challenge_url'], undefined);
    assert.deepEqual(result.list, []);
    const withWidget = runPage('MissAV', '<script src="/cdn-cgi/challenge-platform/a"></script><div>turnstile</div>');
    assert.equal(withWidget['__tvbox_challenge_url'], undefined);
});
