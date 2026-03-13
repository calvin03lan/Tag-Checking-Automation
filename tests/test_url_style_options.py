"""Unit tests for utils/url_style_options.py"""
from models.session import UrlItem
from utils.url_style_options import (
    DEFAULT_URL_STYLE_OPTIONS,
    apply_style_to_url_items,
    build_url_from_path,
    load_url_style_options,
    save_url_style_options,
)


class TestUrlStyleOptionsStore:
    def test_load_defaults_when_file_missing(self, tmp_path):
        p = tmp_path / "missing.json"
        data = load_url_style_options(path=p)
        assert data["selected"]["titles"]["pws"] == "https://www.hangseng.com"
        assert data["selected"]["langs"]["cms"]["en"] == "/eng"

    def test_save_then_load_round_trip(self, tmp_path):
        p = tmp_path / "style.json"
        data = load_url_style_options(path=p)
        data["titles"]["pws"].append("https://uat.hangseng.com")
        data["selected"]["titles"]["pws"] = "https://uat.hangseng.com"
        save_url_style_options(data, path=p)

        loaded = load_url_style_options(path=p)
        assert "https://uat.hangseng.com" in loaded["titles"]["pws"]
        assert loaded["selected"]["titles"]["pws"] == "https://uat.hangseng.com"


class TestUrlStyleBuild:
    def test_build_pws_url(self, tmp_path):
        options = load_url_style_options(path=tmp_path / "style.json")
        url = build_url_from_path("/promo/a", "sc", "pws", options=options)
        assert url == "https://www.hangseng.com/zh-cn/promo/a"

    def test_build_cms_url(self, tmp_path):
        options = load_url_style_options(path=tmp_path / "style.json")
        url = build_url_from_path("/cms/news/a", "tc", "cms", options=options)
        assert url == "https://cms.hangseng.com/cms/news/a/chi/index.html"

    def test_build_uses_custom_selected_values(self, tmp_path):
        options = load_url_style_options(path=tmp_path / "style.json")
        options["titles"]["pws"].append("https://uat-pws.hangseng.com")
        options["selected"]["titles"]["pws"] = "https://uat-pws.hangseng.com"
        options["langs"]["pws"]["en"].append("/en-test")
        options["selected"]["langs"]["pws"]["en"] = "/en-test"

        url = build_url_from_path("promo/a", "en", "pws", options=options)
        assert url == "https://uat-pws.hangseng.com/en-test/promo/a"


class TestApplyStyleToUrlItems:
    def test_rebuilds_only_pws_and_cms_items(self):
        options = DEFAULT_URL_STYLE_OPTIONS
        items = [
            UrlItem(
                url="https://old/a",
                lang="tc",
                num=1,
                url_path="/promo/a",
                url_kind="pws",
            ),
            UrlItem(
                url="https://old/b",
                lang="en",
                num=2,
                url_path="/cms/news/b",
                url_kind="cms",
            ),
            UrlItem(
                url="https://legacy.example.com",
                lang="en",
                num=3,
                url_kind="legacy",
            ),
        ]

        rebuilt = apply_style_to_url_items(items, options=options)

        assert rebuilt[0].url == "https://www.hangseng.com/zh-hk/promo/a"
        assert rebuilt[1].url == "https://cms.hangseng.com/cms/news/b/eng/index.html"
        assert rebuilt[2].url == "https://legacy.example.com"
        assert rebuilt[0].num == 1 and rebuilt[1].num == 2 and rebuilt[2].num == 3
