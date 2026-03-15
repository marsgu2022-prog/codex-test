## 2026-03-15 名人抓取网络抖动

- bug描述：`crawl_famous_people.py` 在连续请求 Wikidata 时会间歇出现 `NameResolutionError`、`SSLEOFError`、`504 Gateway Timeout`
- 复现方式：运行 `python3 bazichart-engine/scripts/crawl_famous_people.py --mode smoke`
- 修复方案：先增加批跑脚本观察波动，后续在抓取脚本中补 SPARQL 重试和失败页补跑

## 2026-03-15 玄学资料抓取限流导致整批失败

- bug描述：`crawl_mysticism_library.py --include-categories` 在 Wikipedia 返回 `429` 或单页超时时，会导致整批任务中断且无法落盘部分结果
- 复现方式：运行 `python3 bazichart-engine/scripts/crawl_mysticism_library.py --include-categories`
- 修复方案：保留退避重试，同时改为单分类/单主题局部失败记录到报告，其余成功主题继续落盘
