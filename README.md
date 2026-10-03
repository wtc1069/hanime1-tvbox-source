# TVBox 站点

适用于支持 Python 和第三方 JAR 站点的 TVBox 版本（如本项目使用的定制 `python32`）。配置地址：

```text
https://raw.githubusercontent.com/wtc1069/hanime1-tvbox-source/main/box.json
```

本规则只请求 `https://hanime1.me`，不使用镜像或回退地址。原站从验证环境返回 HTTP 403，因此目前**无法验证原站的列表、详情和播放**；如果你的设备也被拦截，分类仍会为空。视频地址可能由站点签名且会过期，播放失败时请重新打开详情页获取新地址。请仅在有权访问相关内容的情况下使用。

`Hanime1 原站 (JS)` 使用 GM/WebView 版规则，适合有 Cloudflare 验证的设备环境。它与 Python 版并存，复用 App 的通用验证机制：遇到验证页会打开同域网页，验证完成后重试原请求。播放页由 GM 捕获网页播放器已解析的真实媒体请求；扩展会保留 Cookie、Referer 和 User-Agent，但删除 `Range`/`If-Range`，避免外部播放器从 MP4 中段开始解析。这个修复适用于所有采用 GM 网络匹配播放的站点，并不依赖跨域 `PerformanceResourceTiming`。它只请求 `hanime1.me`，不使用镜像。需要使用包含通用验证功能的定制 TVBox；旧版 App 无法处理验证标记。

MissAV 基于 [cluntop/tvbox 的 GM/WebView 规则](https://github.com/cluntop/tvbox)；本站只访问 `https://missav.ws/`。`vendor/cluntop/` 保存上游 MIT 许可的 `gm.jar` 和修改后的 `missav.user.js`，并托管 jQuery 3.7.1 slim 及其 MIT 许可文件；配置不再依赖 clun.top 的运行文件。上游版本为 `f94c8994b0ce0b6bdad8cd1d2a9b5ac54f677f87`。定制脚本兼容旧版 WebView（不用 `Array.at()`），详情页等待播放器提供 HLS 地址，超时不返回预告链接。JAR 是会在 App 内执行的第三方代码；旧的 `missav_direct.py` 仅保留供回退。MissAV 的实际播放仍需设备实测。

MissAV 分类或详情碰到 Cloudflare 验证时，脚本会返回验证标记。配套的 [定制 TVBox](https://github.com/wtc1069/TVBoxOSC-Hanime1) 会打开同域网页供用户验证，然后重新请求一次；旧版 App 无法处理此标记。清空 App 数据也会清空站点验证状态，首次访问需要重新验证。验证能否通过取决于设备网络和站点策略。

123AV 使用 [cluntop/tvbox 的 GM 规则](https://github.com/cluntop/tvbox/blob/main/js/123av.user.js)，复用上述 `gm.jar` 和本仓库的 jQuery。`vendor/cluntop/js/123av.user.js` 基于上游 `df5c43052a9936b44222f93e9cc1893026b0cca0`，已按目前站点的 `/en/` 路由、列表卡片和详情字段更新，兼容旧版 WebView，并对验证页返回同一通用标记。播放沿用上游 WebView 匹配方式；实际播放效果仍需设备验证。

详情页的选集按原站播放清单显示视频标题，不再列出画质。当前视频由网页播放器请求真实媒体地址；其他选集在点击时重新打开对应页面并捕获各自的媒体请求。清单不存在时仅显示当前视频。点选其他选集仍需访问 `hanime1.me`，如果验证状态未复用或原站拦截，请求可能失败或较慢。

分类页支持排序筛选，并兼容原站 `video-item-container` 卡片的标题和时长字段；排行榜不附加分类参数。

在 TVBox 中重新加载上述配置，选择所需的站点。Hanime1 当前搜索使用 `裏番` 分类；若仍显示旧站点列表，可清除该配置缓存后再次导入。

Hanime1 规则参考了 [cluntop/tvbox 的 Hanime Python 实现](https://github.com/cluntop/tvbox/blob/main/py/Hanime.py)和 [bizhangjie/CatVodSpider](https://github.com/bizhangjie/CatVodSpider/blob/main/app/src/main/java/com/github/catvod/spider/Hanime.java) 的分类方式；Hanime1 不依赖其他站点的 JAR 或播放前缀。
