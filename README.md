# Hanime1 TVBox 单站点配置

配置地址：

```text
https://raw.githubusercontent.com/wtc1069/hanime1-tvbox-source/main/box.json
```

在支持 TVBox 配置及 `csp_XYQHiker` 的应用中，将该地址填入配置地址栏。本仓库只提供一个站点配置，规则和 JAR 分别来自 [wanganni/yinshiyuan 的 Hanime1 规则](https://github.com/wanganni/yinshiyuan/blob/main/tv/XYQHiker/hanime1.json)及其配套 JAR；这些文件不由本仓库维护。

配置文件可以解析，依赖地址在发布时可访问。由于 `hanime1.me` 从验证环境返回 HTTP 403，未验证搜索、详情和播放功能。上游规则还包含与目标站点不一致的播放前缀，因此不能保证实际播放成功。请勿在配置地址中加入 GitHub 私人令牌。
