## 2026-03-15 名人抓取网络抖动

- bug描述：`crawl_famous_people.py` 在连续请求 Wikidata 时会间歇出现 `NameResolutionError`、`SSLEOFError`、`504 Gateway Timeout`
- 复现方式：运行 `python3 bazichart-engine/scripts/crawl_famous_people.py --mode smoke`
- 修复方案：先增加批跑脚本观察波动，后续在抓取脚本中补 SPARQL 重试和失败页补跑
