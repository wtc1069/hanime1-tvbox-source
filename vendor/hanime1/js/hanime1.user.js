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

    function sourceUrl(node) {
        var value = attr(node, 'src') || attr(node, 'data-src') || attr(node, 'data-original');
        if (!value || /^blob:/i.test(value)) return '';
        if (/^\/\//.test(value)) return location.protocol + value;
        if (/^\//.test(value)) return (location.origin || 'https://hanime1.me') + value;
        return value;
    }

    function sourceQuality(node, url) {
        var value = attr(node, 'size') || attr(node, 'label') || attr(node, 'data-quality') || url;
        var match = /(?:^|[^0-9])(2160|1440|1080|720|540|480|360)(?:p)?(?:[^0-9]|$)/i.exec(value || '');
        return match ? parseInt(match[1], 10) : 0;
    }

    function preferHighestQuality() {
        var video = one(document, 'video');
        if (!video) return;
        var nodes = all(video, 'source[src], source[data-src]');
        var bestUrl = '';
        var bestQuality = -1;
        for (var i = 0; i < nodes.length; i++) {
            var url = sourceUrl(nodes[i]);
            var quality = sourceQuality(nodes[i], url);
            if (/\.(mp4|m3u8)(?:[?#]|$)/i.test(url)) quality += 1;
            if (url && quality > bestQuality) {
                bestQuality = quality;
                bestUrl = url;
            }
        }
        if (bestUrl && video.currentSrc !== bestUrl && video.src !== bestUrl) {
            video.src = bestUrl;
            if (typeof video.load === 'function') video.load();
        }
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
            // GM captures the actual request after the page player resolves it.
            // Its runtime removes range-specific headers before TVBox replays it.
            preferHighestQuality();
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
            send(spider.playerContent());
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
