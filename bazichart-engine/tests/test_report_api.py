from routes.report_utils import parse_tags, sanitize_filename


def test_parse_tags_supports_csv_and_json():
    assert parse_tags("产业园区, 写字楼") == ["产业园区", "写字楼"]
    assert parse_tags('["上海", "大湾区"]') == ["上海", "大湾区"]


def test_sanitize_filename_removes_unsafe_chars():
    cleaned = sanitize_filename("../Q4 上海写字楼@季报?.pdf")
    assert ".." not in cleaned
    assert "/" not in cleaned
    assert cleaned.endswith(".pdf")
