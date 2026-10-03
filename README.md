# Hanime1 TVBox Python 站点

适用于支持 Python 站点规则的 TVBox 版本（如 `python32`）。配置地址：

```text
https://raw.githubusercontent.com/wtc1069/hanime1-tvbox-source/main/box.json
```

本规则只请求 `https://hanime1.me`，不使用镜像或回退地址。原站从验证环境返回 HTTP 403，因此目前**无法验证原站的列表、详情和播放**；如果你的设备也被拦截，分类仍会为空。视频地址可能由站点签名且会过期，播放失败时请重新打开详情页获取新地址。请仅在有权访问相关内容的情况下使用。

详情页的选集按原站播放清单显示视频标题，不再列出画质。当前视频使用页面中最高画质的播放地址；其他选集在点击时读取对应页面，选择最高画质。清单不存在时仅显示当前视频。点选其他选集仍需访问 `hanime1.me`，如果验证状态未复用或原站拦截，请求可能失败或较慢。

分类页支持排序筛选，并兼容原站 `video-item-container` 卡片的标题和时长字段；排行榜不附加分类参数。

在 TVBox 中重新加载上述配置，选择 `Hanime1 原站 (Python)` 站点。当前搜索使用 `裏番` 分类；若仍显示旧的 `Hanime1` 站点，可清除该配置缓存后再次导入。

规则参考了 [cluntop/tvbox 的 Hanime Python 实现](https://github.com/cluntop/tvbox/blob/main/py/Hanime.py)和 [bizhangjie/CatVodSpider](https://github.com/bizhangjie/CatVodSpider/blob/main/app/src/main/java/com/github/catvod/spider/Hanime.java) 的分类方式；不依赖其他站点的 JAR 或播放前缀。
