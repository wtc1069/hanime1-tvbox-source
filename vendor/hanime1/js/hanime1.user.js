// ==UserScript==
// @name         Hanime1 TVBox
// @namespace    gmspider
// @version      1.0.0
// @description  Hanime1 GMSpider for TVBox
// @match        https://hanime1.me/*
// @grant        unsafeWindow
// ==/UserScript==
(function () {
    'use strict';

    var args = {name: 'homeContent', values: [true]};
    if (typeof GmSpiderInject !== 'undefined') {
        var raw = JSON.parse(GmSpiderInject.GetSpiderArgs());
        args.name = raw.shift();
        args.values = raw;
    }

    var genres = ['裏番', '泡麵番', 'Motion Anime', '3D動畫', '3DCG', '2D動畫',
        'AI生成', 'MMD', '同人作品', 'Cosplay'];
    var ranks = ['最新上市', '本日排行', '本週排行', '本月排行'];
    var sorts = ['最新上市', '最新上傳', '本日排行', '本週排行', '本月排行', '觀看次數'];
    var browserUserAgent = 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36';

    function text(node) {
        return node && node.textContent ? node.textContent.replace(/^\s+|\s+$/g, '') : '';
    }

    function attr(node, name) {
        return node && node.getAttribute ? node.getAttribute(name) || '' : '';
    }

    function one(node, selector) {
        return node && node.querySelector ? node.querySelector(selector) : null;
    }

    function all(node, selector) {
        return node && node.querySelectorAll ? node.querySelectorAll(selector) : [];
    }

    function watchId(href) {
        var match = /(?:^|[?&])v=(\d+)(?:&|$)/.exec(href || '');
        return match ? match[1] : '';
    }

    function pageNumber(value) {
        var page = parseInt(value, 10);
        return isNaN(page) || page < 1 ? 1 : page;
    }

    function cleanName(value, fallback) {
        return (value || fallback || '').replace(/[#$]/g, ' ').replace(/^\s+|\s+$/g, '');
    }

    function queryValue(name, value) {
        return name + '=' + encodeURIComponent(value);
    }

    function cardFrom(node) {
        var link = one(node, 'a[href*="/watch"]') || (attr(node, 'href').indexOf('/watch') >= 0 ? node : null);
        var id = watchId(attr(link, 'href'));
        if (!id) return null;
        var image = one(node, 'img');
        var name = text(one(node, '.home-rows-videos-title, .card-mobile-title, .video-title, .title'));
        if (!name) name = attr(link, 'title') || attr(image, 'alt');
        name = cleanName(name, id);
        if (!name) return null;
        return {
            vod_id: id,
            vod_name: name,
            vod_pic: attr(image, 'src') || attr(image, 'data-src') || attr(image, 'data-original'),
            vod_remarks: text(one(node, '.duration'))
        };
    }

    function cards() {
        var nodes = all(document, '.video-item-container');
        if (!nodes.length) nodes = all(document, '.home-rows-videos-wrapper a[href*="/watch"]');
        if (!nodes.length) nodes = all(document, 'a[href*="/watch"]');
        var result = [];
        var seen = {};
        for (var i = 0; i < nodes.length; i++) {
            var card = cardFrom(nodes[i]);
            if (card && !seen[card.vod_id]) {
                seen[card.vod_id] = true;
                result.push(card);
            }
        }
        return result;
    }

    function hasNext(pg) {
        return one(document, 'a[rel="next"]') ? pageNumber(pg) + 1 : pageNumber(pg);
    }

    function sourceUrl(node) {
        if (!node) return '';
        var value = node.currentSrc || node.src || attr(node, 'src') ||
            attr(node, 'data-src') || attr(node, 'data-original');
        if (!value || /^blob:/i.test(value)) return '';
        if (/^\/\//.test(value)) return location.protocol + value;
        if (/^\//.test(value)) {
            var origin = location.origin || (location.protocol + '//' + location.host);
            return origin + value;
        }
        return value;
    }

    function sourceQuality(node, url) {
        var textValue = [attr(node, 'size'), attr(node, 'label'), attr(node, 'data-quality'), url].join(' ');
        var matches = textValue.match(/(?:^|[^0-9])(2160|1440|1080|720|540|480|360)(?:p)?(?:[^0-9]|$)/gi) || [];
        var quality = 0;
        for (var i = 0; i < matches.length; i++) {
            var value = parseInt(matches[i].replace(/[^0-9]/g, ''), 10);
            if (!isNaN(value) && value > quality) quality = value;
        }
        var size = parseInt(attr(node, 'size'), 10);
        return (isNaN(size) ? 0 : size) * 10000 + quality;
    }

    function bestSource() {
        var nodes = [];
        var selectors = ['video', 'video source', 'source[src]', 'source[data-src]',
            'video source[src], source[type="video/mp4"][src]'];
        for (var s = 0; s < selectors.length; s++) {
            var found = all(document, selectors[s]);
            for (var f = 0; f < found.length; f++) nodes.push(found[f]);
        }
        var url = '';
        var quality = -1;
        var seen = {};
        for (var i = 0; i < nodes.length; i++) {
            var candidate = sourceUrl(nodes[i]);
            if (!/^https?:\/\//i.test(candidate) || seen[candidate]) continue;
            seen[candidate] = true;
            var value = sourceQuality(nodes[i], candidate);
            // Prefer a real media URL over a poster or tracking URL when quality is equal.
            if (/\.(mp4|m3u8)(?:[?#]|$)/i.test(candidate)) value += 1;
            if (value >= quality) {
                quality = value;
                url = candidate;
            }
        }
        return url;
    }

    function playbackHeaders() {
        var headers = {
            'User-Agent': browserUserAgent,
            Referer: 'https://hanime1.me/'
        };
        // Keep the WebView session available to the external TVBox player when the
        // media host checks the same session as the page.
        var cookies = document.cookie || '';
        if (cookies) headers.Cookie = cookies;
        return headers;
    }

    function playlist(currentId, currentName) {
        var nodes = all(document,
            '#video-playlist-wrapper .playlist-video-card, .video-playlist-wrapper .playlist-video-card, .related-watch-wrap');
        var result = [];
        var seen = {};
        for (var i = 0; i < nodes.length; i++) {
            var link = one(nodes[i], 'a[href*="/watch"]');
            var id = watchId(attr(link, 'href'));
            if (!id || seen[id]) continue;
            seen[id] = true;
            var image = one(nodes[i], 'img');
            var name = text(one(nodes[i], '.video-title, .card-mobile-title, .title'));
            result.push({id: id, name: cleanName(name, attr(image, 'alt') || attr(link, 'title') || id)});
        }
        if (!seen[currentId]) result.push({id: currentId, name: cleanName(currentName, currentId)});
        return result;
    }

    function meta(name) {
        return attr(one(document, 'meta[property="' + name + '"]'), 'content');
    }

    function isChallengePage() {
        var title = (document.title || '').toLowerCase();
        if (/just a moment|attention required|verify you are human|checking your browser/.test(title)) return true;
        if (one(document, '#cf-wrapper, #cf-challenge-running, #cf-browser-verification, #challenge-form')) return true;
        if (typeof window._cf_chl_opt !== 'undefined') return true;
        var html = document.documentElement && document.documentElement.outerHTML ?
            document.documentElement.outerHTML.toLowerCase() : '';
        var body = document.body && document.body.innerText ? document.body.innerText.toLowerCase() : '';
        return html.indexOf('/cdn-cgi/challenge-platform/') >= 0 &&
            /verify you are human|checking your browser|checking if the site connection is secure/.test(body);
    }

    var spider = {
        homeContent: function () {
            var classes = [{type_id: queryValue('sort', ranks[0]), type_name: ranks[0]}];
            var filters = {};
            for (var i = 0; i < genres.length; i++) {
                var category = queryValue('genre', genres[i]) + '&' + queryValue('sort', ranks[0]);
                classes.push({type_id: category, type_name: genres[i]});
                var values = [];
                for (var j = 0; j < sorts.length; j++) {
                    values.push({n: sorts[j], v: '&' + queryValue('sort', sorts[j])});
                }
                filters[category] = [{key: 'sort', name: '排序', value: values}];
            }
            for (var k = 1; k < ranks.length; k++) {
                classes.push({type_id: queryValue('sort', ranks[k]), type_name: ranks[k]});
            }
            return {class: classes, filters: filters, list: cards()};
        },

        categoryContent: function (tid, pg, filter, extend) {
            var page = pageNumber(pg);
            return {list: cards(), page: page, pagecount: hasNext(page)};
        },

        detailContent: function (ids) {
            var id = String(ids && ids[0] || '');
            if (!/^\d+$/.test(id)) return {list: []};
            var title = meta('og:title') || text(one(document, 'h1')) || id;
            var entries = playlist(id, title);
            var media = [];
            for (var i = 0; i < entries.length; i++) {
                media.push({
                    name: cleanName(entries[i].name, entries[i].id),
                    type: 'webview',
                    ext: {replace: {vod_id: String(entries[i].id)}}
                });
            }
            return {list: [{
                vod_id: id,
                vod_name: title,
                vod_pic: meta('og:image'),
                vod_content: meta('og:description'),
                vod_play_from: 'Hanime1',
                vod_play_data: [{from: 'Hanime1', media: media}]
            }]};
        },

        playerContent: function () {
            // The site creates the media request dynamically. Let the GM JAR
            // capture the matching request instead of reading a blob URL.
            return {type: 'match'};
        },

        searchContent: function (key, quick, pg) {
            var page = pageNumber(pg);
            return {list: cards(), page: page, pagecount: hasNext(page)};
        }
    };

    function send(value) {
        if (typeof GmSpiderInject !== 'undefined') GmSpiderInject.SetSpiderResult(JSON.stringify(value));
    }

    function run() {
        if (isChallengePage()) {
            send({__tvbox_challenge_url: location.href});
            return;
        }
        if (args.name === 'playerContent') {
            if (isChallengePage()) send({__tvbox_challenge_url: location.href});
            else send(spider[args.name].apply(null, args.values));
            return;
        }
        send(spider[args.name].apply(null, args.values));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }
})();
