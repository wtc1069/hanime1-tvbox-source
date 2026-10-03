# Hanime1 TVBox Python 站点

适用于支持 Python 站点规则的 TVBox 版本（如 `python32`）。配置地址：

```text
https://raw.githubusercontent.com/wtc1069/hanime1-tvbox-source/main/box.json
```

本规则使用 `hanime163.com` 镜像：目标 `hanime1.me` 从验证环境返回 HTTP 403。已检查镜像分类页、详情页和媒体地址在验证环境中可访问，但尚未在电视端验收；不同地区网络可能仍有差异。视频地址由目标站点签名且会过期，播放失败时请重新打开详情页获取新地址。请仅在有权访问相关内容的情况下使用。

在 TVBox 中重新加载上述配置，选择 `Hanime1 (Python)` 站点。当前搜索使用 `裏番` 分类，因为镜像在省略分类时返回空列表。若仍显示旧的 `Hanime1` 站点，可清除该配置缓存后再次导入。

规则参考了 [cluntop/tvbox 的 Hanime Python 实现](https://github.com/cluntop/tvbox/blob/main/py/Hanime.py)和 [bizhangjie/CatVodSpider](https://github.com/bizhangjie/CatVodSpider/blob/main/app/src/main/java/com/github/catvod/spider/Hanime.java) 的分类方式；本站规则独立解析当前镜像页面，不依赖其他站点的 JAR 或播放前缀。
