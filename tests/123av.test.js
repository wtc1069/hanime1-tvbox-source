const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'vendor/cluntop/js/123av.user.js'), 'utf8');
const site = JSON.parse(fs.readFileSync(path.join(root, 'box.json'), 'utf8'))
    .sites.find(item => item.key === '123av');

function runPage(title, html = '<html></html>') {
    let response;
    const document = {
        title,
        documentElement: {outerHTML: html},
        body: {innerText: ''},
        querySelector: () => null,
    };
    const $ = target => target === document ? {ready: callback => callback()} : {
        text: () => '',
        each: () => {},
    };
    const context = vm.createContext({
        GM_info: {},
        GmSpiderInject: {
            GetSpiderArgs: () => JSON.stringify(['homeContent', true]),
            SetSpiderResult: value => { response = JSON.parse(value); },
        },
        document,
        location: {href: 'https://123av.com/en/new'},
        window: {},
        $,
        console: {log: () => {}},
    });
    vm.runInContext('Array.prototype.at = undefined', context);
    vm.runInContext(script, context);
    return response;
}

test('configuration uses the vendored GM runtime and original host', () => {
    assert.equal(site.api, 'csp_GM');
    assert.match(site.jar, /\/vendor\/cluntop\/jar\/gm\.jar\?v=[a-f0-9]+$/);
    assert.match(site.ext.userScript, /\/vendor\/cluntop\/js\/123av\.user\.js$/);
    for (const entry of Object.values(site.ext.spider)) {
        assert.match(entry.loadUrl, /^https:\/\/123av\.com\/en\//);
    }
    assert.match(script, /@require\s+https:\/\/raw\.githubusercontent\.com\/wtc1069\/hanime1-tvbox-source\/main\/vendor\/cluntop\/js\/jquery-3\.7\.1\.slim\.min\.js/);
    assert.doesNotMatch(script, /\.at\(/);
});

test('challenge page returns the URL for generic App verification', () => {
    assert.equal(runPage('Just a moment...').__tvbox_challenge_url,
        'https://123av.com/en/new');
    assert.equal(runPage('123AV', '<script src="/cdn-cgi/challenge-platform/a"></script>').__tvbox_challenge_url,
        undefined);
});

test('ordinary homepage produces categories', () => {
    assert.equal(runPage('123AV').class.length, 6);
});
