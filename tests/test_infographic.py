"""X 投稿画像の組み立てを検証する（画像生成 API は呼ばない）。"""

import io

from PIL import Image

from generators.infographic_maker import POST_SIZE, _save_for_x, build_prompt


def test_prompt_carries_all_ten_ranks():
    """10件すべてが順位付きでプロンプトに載る（1件でも欠けると画像から消える）。"""
    articles = [
        {"one_liner": f"見出し{i}", "summary_ja": f"要約{i}", "category": "研究・技術"}
        for i in range(1, 11)
    ]
    prompt = build_prompt(articles, theme="本日のテーマ", date_str="2026年08月10日")

    for i in range(1, 11):
        assert f"【{i}位】見出し{i}" in prompt
        assert f"要約{i}" in prompt
    assert "本日のテーマ" in prompt
    assert "2026年08月10日" in prompt


def test_prompt_states_the_actual_article_count():
    """記事が10件未満の日に「トップ10」と書かない（存在しない項目を描き足させないため）。"""
    prompt = build_prompt([{"one_liner": f"見出し{i}"} for i in range(3)])

    assert "トップ3" in prompt
    assert "トップ10" not in prompt


def test_prompt_accepts_both_field_namings():
    """公開JSON(title/summary)と配信JSON(title_ja/summary_ja)のどちらでも見出しを拾う。"""
    prompt = build_prompt([{"title": "公開側の見出し"}, {"title_ja": "配信側の見出し"}])

    assert "公開側の見出し" in prompt
    assert "配信側の見出し" in prompt


def test_ogp_image_reuses_the_generated_card(tmp_path, monkeypatch):
    """サイト用カード画像は X 投稿用の画像を縮小して流用する（二重生成すると費用が倍になる）。"""
    import build_pages
    from generators.infographic_maker import CARD_FILENAME

    monkeypatch.setattr(build_pages, "output_dir_path", str(tmp_path))
    Image.new("RGB", POST_SIZE, "navy").save(tmp_path / CARD_FILENAME)
    docs = tmp_path / "docs"
    docs.mkdir()

    build_pages.generate_ogp_image(docs)

    assert Image.open(docs / build_pages.OGP_FILENAME).size == build_pages.OGP_SIZE


def test_ogp_filename_matches_the_meta_tags(tmp_path):
    """HTML のメタタグが指す画像名と、実際に書き出す画像名が一致していること。"""
    import build_pages

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "latest.json").write_text('{"theme": "T", "articles": []}', encoding="utf-8")
    (docs / "index.html").write_text(
        "<html><head><!-- OGP_START --><!-- OGP_END --></head></html>", encoding="utf-8"
    )

    build_pages.inject_ogp_and_prerender(docs)
    page = (docs / "index.html").read_text(encoding="utf-8")

    assert f'og:image" content="{build_pages.WEB_BASE}{build_pages.OGP_FILENAME}"' in page
    assert "ogp_latest.png" not in page


def test_ogp_image_kept_when_card_missing(tmp_path, monkeypatch):
    """画像生成に失敗した日は、前回のカード画像を消さずに残す。"""
    import build_pages

    monkeypatch.setattr(build_pages, "output_dir_path", str(tmp_path))
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / build_pages.OGP_FILENAME).write_bytes(b"previous")

    build_pages.generate_ogp_image(docs)

    assert (docs / build_pages.OGP_FILENAME).read_bytes() == b"previous"


def test_saved_image_matches_x_recommended_size(tmp_path):
    """保存後の画像は X 推奨の 1600x900 で、5MB 上限内に収まる。"""
    buf = io.BytesIO()
    Image.new("RGB", (2560, 1440), "navy").save(buf, format="PNG")

    out = _save_for_x(buf.getvalue(), str(tmp_path / "card.png"))

    assert Image.open(out).size == POST_SIZE
