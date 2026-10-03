// ==UserScript==
// @name         123av
// @namespace    gmspider
// @version      2024.12.03-tvbox.2
// @description  123av GMSpider
// @author       Luomo
// @match        https://*.123av.com/*
// @match        https://123av.com/*
// @require      https://raw.githubusercontent.com/wtc1069/hanime1-tvbox-source/main/vendor/cluntop/js/jquery-3.7.1.slim.min.js
// @grant        unsafeWindow
// ==/UserScript==
console.log(JSON.stringify(GM_info));
(function () {
    const GMSpiderArgs = {};
    if (typeof GmSpiderInject !== 'undefined') {
        let args = JSON.parse(GmSpiderInject.GetSpiderArgs());
        GMSpiderArgs.fName = args.shift();
        GMSpiderArgs.fArgs = args;
    } else {
        GMSpiderArgs.fName = "homeContent";
        GMSpiderArgs.fArgs = ["tags"];
    }
    Object.freeze(GMSpiderArgs);
    const GmSpider = (function () {
        const defaultFilter = [{
            key: "sort",
            name: "排序",
            value: [
                {n: "默认", v: ""},
                {n: "今日浏览", v: "&sort=today"},
                {n: "本周浏览", v: "&sort=week"},
                {n: "本月浏览", v: "&sort=month"}
            ]
        }];

        function pageList(select) {
            let itemList = [];
            $(select).each(function (i) {
                const link = $(this).find("a.card__cover").attr("href");
                if (link && link.indexOf("/en/v/") >= 0) {
                    itemList.push({
                        vod_id: link.split("/en/v/").pop().split("?")[0],
                        vod_name: $(this).find(".card__title").text().trim(),
                        vod_pic: $(this).find("img.card__img").attr("src"),
                        vod_remarks: $(this).find(".card__dur").text().trim()
                    })
                }
            });
            return itemList;
        }

        function pageCount(pg) {
            const last = $(".pager__pages a").last().text().trim();
            const total = $(".pager__total").text().replace(/[^0-9]/g, "");
            return Math.max(Number(last) || 0, Number(total) || 0, Number(pg) || 1);
        }


        return {
            homeContent: function () {
                let result = {
                    class: [
                        {type_id: "new", type_name: "最新"},
                        {type_id: "hot", type_name: "热门"},
                        {type_id: "recent", type_name: "近期更新"},
                        {type_id: "censored", type_name: "有码"},
                        {type_id: "uncensored", type_name: "无码"},
                        {type_id: "genres", type_name: "类型"}
                    ],
                    filters: {
                        "hot": defaultFilter,
                        "censored": defaultFilter,
                        "uncensored": defaultFilter
                    },
                    list: []
                };
                let itemList = pageList(".grid .card");
                result.list = itemList.filter((item, index) => {
                    return itemList.findIndex(i => i.vod_id === item.vod_id) === index
                });
                return result;
            },
            categoryContent: function (tid, pg, filter, extend) {
                let result = {
                    list: [],
                    page: pg,
                    pagecount: 1
                };
                if (tid === "genres") {
                    $(".ggrid .gchip").each(function () {
                        const link = $(this).attr("href") || "";
                        result.list.push({
                            vod_id: link.split("/en/").pop(),
                            vod_name: $(this).find(".gchip__name").text().trim(),
                            vod_remarks: $(this).find(".gchip__count").text().trim(),
                            vod_tag: "folder",
                            style: {"type": "rect", "ratio": 2}
                        })
                    });
                } else {
                    result.list = pageList(".grid .card");
                    result.pagecount = pageCount(pg);
                }
                return result;
            },
            detailContent: function (ids) {
                const detail = {};
                $(".watch__info-row").each(function () {
                    detail[$(this).find("dt").text().trim()] = $(this).find("dd").text().trim();
                });
                const vod = {
                    vod_id: ids[0],
                    vod_name: $(".watch__title").text().trim(),
                    vod_pic: (($('.player').attr('style') || '').match(/url\(['"]?([^'"\)]+)/) || [])[1] || '',
                    vod_year: detail["Release date"] || "",
                    vod_remarks: detail["Type"] || "",
                    vod_director: detail["Maker"] || "",
                    vod_actor: detail["Cast"] || "",
                    vod_content: $(".watch__title").text().trim(),
                    vod_play_data: [{
                        from: "123AV",
                        media: [{
                            name: detail["Code"] || "播放",
                            type: "webview",
                            ext: {
                                replace: {
                                    vod_id: ids[0]
                                }
                            }
                        }]
                    }]
                };
                return {list: [vod]};
            },
            playerContent: function (flag, id, vipFlags) {
                return {
                    type: "match"
                };
            },
            searchContent: function (key, quick, pg) {
                const result = {
                    list: [],
                    page: pg,
                    pagecount: 0
                };
                result.list = pageList(".grid .card");
                result.pagecount = pageCount(pg);
                return result;
            }
        };
    })();
    function isChallengePage() {
        const title = (document.title || '').toLowerCase();
        if (/just a moment|attention required|verify you are human|checking your browser/.test(title)) return true;
        if (document.querySelector('#cf-wrapper, #cf-challenge-running, #cf-browser-verification, #challenge-form')) return true;
        if (typeof window._cf_chl_opt !== 'undefined') return true;
        const html = document.documentElement.outerHTML.toLowerCase();
        const body = document.body ? document.body.innerText.toLowerCase() : '';
        return html.indexOf('/cdn-cgi/challenge-platform/') >= 0 &&
            /verify you are human|checking your browser|checking if the site connection is secure/.test(body);
    }

    $(document).ready(function () {
        if (isChallengePage()) {
            if (typeof GmSpiderInject !== 'undefined') {
                GmSpiderInject.SetSpiderResult(JSON.stringify({__tvbox_challenge_url: location.href}));
            }
            return;
        }
        if ($("#body .btn-primary").text() === "Click here to continue") {
            window.location = $("#body .btn-primary").attr("href");
            return;
        }
        const result = GmSpider[GMSpiderArgs.fName](...GMSpiderArgs.fArgs);
        console.log(JSON.stringify(result));
        if (typeof GmSpiderInject !== 'undefined') {
            GmSpiderInject.SetSpiderResult(JSON.stringify(result));
        }
    });
})();
