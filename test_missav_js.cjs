const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const script = fs.readFileSync('vendor/cluntop/js/missav.user.js', 'utf8');

function runDetail(readyAfter) {
    const calls = [];
    const timers = [];
    const document = {
        title: 'MissAV',
        querySelector: () => null,
        documentElement: {outerHTML: '<html></html>'},
        body: {innerText: ''}
    };
    const jquery = value => ({
        length: 0,
        ready(callback) { callback(); },
        each() { return this; },
        text() { return ''; },
        attr() { return ''; },
        find() { return this; }
    });
    const player = {};
    const context = vm.createContext({
        console: {log() {}, warn() {}},
        GM_info: {},
        GmSpiderInject: {
            GetSpiderArgs: () => JSON.stringify(['detailContent', ['abc-123']]),
            SetSpiderResult: value => calls.push(JSON.parse(value))
        },
        unsafeWindow: {hls: player},
        document,
        window: {},
        $: jquery,
        setTimeout: callback => timers.push(callback)
    });
    vm.runInContext('Array.prototype.at = undefined', context);
    vm.runInContext(script, context);
    for (let tick = 0; timers.length && tick < 60; tick++) {
        if (tick === readyAfter) player.url = 'https://surrit.com/abc/playlist.m3u8';
        timers.shift()();
    }
    return calls;
}

assert.equal(runDetail(2)[0].list[0].vod_play_url,
    '多视轨$https://surrit.com/abc/playlist.m3u8');
assert.equal(runDetail(Infinity)[0].list.length, 0);
assert.equal(runDetail(Infinity).length, 1);
console.log('MissAV JS detail tests passed');
