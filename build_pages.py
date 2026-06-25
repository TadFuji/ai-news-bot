#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pages ビルドスクリプト

output/ 内の Markdown ファイルを解析し、
GitHub Pages 用の JSON データを生成します。
"""

import re
import json
import html
import shutil
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape
from config import NEWS_BOT_OUTPUT_DIR as output_dir_path

# 公開ポータルのベースURL
WEB_BASE = "https://tadfuji.github.io/ai-news-bot/"


def parse_markdown_news(content: str) -> dict:
    """
    Markdown ファイルからニュース記事を抽出する
    
    Args:
        content: Markdown ファイルの内容
    
    Returns:
        パース結果（更新日時、記事リスト）
    """
    result = {
        "updated": "",
        "articles": []
    }
    
    # 更新日時を抽出
    date_match = re.search(r'\*\*更新日時\*\*:\s*(.+?)(?:\s*\(JST\))?$', content, re.MULTILINE)
    if date_match:
        result["updated"] = date_match.group(1).strip()
    
    # 記事を抽出（## 1. タイトル 形式 + **カテゴリ**: ...）
    article_pattern = re.compile(
        r'##\s*\d+\.\s*(.+?)\n\n\*\*カテゴリ\*\*:\s*(.+?)\n\n(.+?)\n\n-\s*\*\*出典\*\*:\s*(.+?)\n-\s*\*\*URL\*\*:\s*(.+?)(?:\n|$)',
        re.DOTALL
    )
    
    for match in article_pattern.finditer(content):
        result["articles"].append({
            "title": match.group(1).strip(),
            "category": match.group(2).strip(),
            "summary": match.group(3).strip(),
            "source": match.group(4).strip(),
            "url": match.group(5).strip()
        })
    
    return result


def _read_latest(docs_dir: Path):
    """docs/latest.json を読み込む（無ければ None）。"""
    p = docs_dir / "latest.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _between_markers(text: str, start: str, end: str, replacement: str) -> str:
    """start..end マーカー間を replacement で冪等に差し替える（マーカー自体は保持）。"""
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    new_block = start + replacement + end
    if pattern.search(text):
        return pattern.sub(lambda _: new_block, text)
    return text  # マーカーが無ければ何もしない（安全）


def _safe_http_url(u: str) -> str:
    """http(s) スキームのみ許可。javascript: 等のスキームは空文字に落とす（XSS対策）。

    ソースURLは外部RSS/LLM由来で信頼できないため、href に出す前に必ず通す。
    """
    u = (u or "").strip()
    return u if u.lower().startswith(("http://", "https://")) else ""


def _json_for_script(obj) -> str:
    """Embed JSON safely inside a <script> block (prevents </script> breakout).

    json.dumps does not escape < or >, so an untrusted string that closes a
    script tag could break out of the JSON-LD block. Replace < > & with their
    unicode escapes (valid inside JSON strings; JSON-LD semantics preserved).
    """
    bs = chr(92)
    out = json.dumps(obj, ensure_ascii=False)
    out = out.replace("<", bs + "u003c")
    out = out.replace(">", bs + "u003e")
    out = out.replace("&", bs + "u0026")
    return out


def generate_ogp_image(docs_dir: Path):
    """latest.json の theme/morning_comment から OGP 画像(1200x630)を生成する。"""
    data = _read_latest(docs_dir)
    if not data:
        return
    from generators.infographic_maker import create_infographic
    arts = data.get("articles", [])
    title = data.get("theme") or "AI ニュース TOP10"
    summary = data.get("morning_comment") or (arts[0].get("one_liner", "") if arts else "")
    create_infographic(title, summary, output_path=str(docs_dir / "ogp_latest.png"))
    print("✅ ogp_latest.png 生成")


def inject_ogp_and_prerender(docs_dir: Path):
    """index.html の OGP メタと記事の静的プリレンダリングを冪等に差し替える。

    - OGP/Twitterカード/meta description/JSON-LD を <head> のマーカー間に注入
    - 記事カードを #news-container 内のマーカー間に静的出力（クローラー可視化）
      JS が動く環境では fetch により上書きされるため二重表示にはならない。
    """
    data = _read_latest(docs_dir)
    if not data:
        return
    index_path = docs_dir / "index.html"
    if not index_path.exists():
        return
    page = index_path.read_text(encoding="utf-8")

    theme = data.get("theme", "")
    comment = data.get("morning_comment", "")
    arts = data.get("articles", [])
    top_oneliner = arts[0].get("one_liner", "") if arts else ""

    def attr(s):  # 属性用エスケープ（"含む）
        return html.escape(str(s or ""), quote=True)

    def txt(s):  # 要素テキスト用エスケープ
        return html.escape(str(s or ""))

    # --- OGP / Twitterカード / meta description / JSON-LD ---
    jsonld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"AI ニュース TOP10 — {theme}",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1,
             "name": x.get("title", ""), "url": _safe_http_url(x.get("url", ""))}
            for i, x in enumerate(arts)
        ],
    }
    ogp = (
        "\n"
        '<meta property="og:type" content="website">\n'
        '<meta property="og:site_name" content="AI ニュース TOP10">\n'
        f'<meta property="og:title" content="{attr(theme)} | AI ニュース TOP10">\n'
        f'<meta property="og:description" content="{attr(comment)} 本日のトップ: {attr(top_oneliner)}">\n'
        f'<meta property="og:image" content="{WEB_BASE}ogp_latest.png">\n'
        f'<meta property="og:url" content="{WEB_BASE}">\n'
        '<meta name="twitter:card" content="summary_large_image">\n'
        f'<meta name="twitter:title" content="{attr(theme)} | AI ニュース TOP10">\n'
        f'<meta name="twitter:description" content="{attr(comment)}">\n'
        f'<meta name="twitter:image" content="{WEB_BASE}ogp_latest.png">\n'
        f'<meta name="description" content="{attr(comment)} 世界のAIニュースを毎朝日本語で厳選してお届け。">\n'
        f'<script type="application/ld+json">{_json_for_script(jsonld)}</script>\n'
    )
    page = _between_markers(page, "<!-- OGP_START -->", "<!-- OGP_END -->", ogp)

    # --- 記事カードの静的プリレンダリング ---
    cards = []
    for i, x in enumerate(arts, 1):
        cat = x.get("category", "未分類")
        ol = x.get("one_liner", "")
        why = x.get("why_important", "")
        act = x.get("action_item", "")
        card = (
            f'<article class="news-card" data-category="{attr(cat)}">'
            f'<div style="display:flex;align-items:center;margin-bottom:5px;">'
            f'<span class="news-rank">{i}</span>'
            f'<span class="news-category" data-category="{attr(cat)}">{txt(cat)}</span></div>'
            + (f'<div class="news-oneliner">💡 {txt(ol)}</div>' if ol else "")
            + f'<h2 class="news-title">{txt(x.get("title", ""))}</h2>'
            f'<p class="news-summary">{txt(x.get("summary", ""))}</p>'
            + (f'<div class="news-why">📌 なぜ重要？ {txt(why)}</div>' if why else "")
            + (f'<div class="news-action">👉 今日の行動：{txt(act)}</div>' if act else "")
            + '<div class="news-meta">'
            f'<span class="news-source">📰 {txt(x.get("source", ""))}</span>'
            f'<span class="news-link"><a href="{attr(_safe_http_url(x.get("url", "")))}" target="_blank" rel="noopener">→ 元記事を読む</a></span>'
            "</div></article>"
        )
        cards.append(card)
    prerender = "\n" + "\n".join(cards) + "\n"
    page = _between_markers(page, "<!-- PRERENDER_START -->", "<!-- PRERENDER_END -->", prerender)

    index_path.write_text(page, encoding="utf-8")
    print("✅ index.html OGP/プリレンダリング更新")


def generate_sitemap(docs_dir: Path):
    """docs/ の日次データから sitemap.xml を生成する。"""
    urls = [
        (WEB_BASE, "1.0"),
        (WEB_BASE + "archive.html", "0.7"),
        (WEB_BASE + "column.html", "0.6"),
        (WEB_BASE + "global.html", "0.6"),
    ]
    for day_file in sorted(docs_dir.glob("20??-??-??.json"), reverse=True):
        if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", day_file.name):
            urls.append((WEB_BASE + "?json=" + day_file.name, "0.5"))

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, pri in urls:
        lines.append(f"  <url><loc>{xml_escape(loc)}</loc><priority>{pri}</priority></url>")
    lines.append("</urlset>")
    (docs_dir / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ sitemap.xml 更新 ({len(urls)} URL)")


def generate_feed(docs_dir: Path):
    """直近7日分の記事から RSS 2.0 フィード(feed.xml)を生成する（URL重複排除・最大50件）。"""
    seen, items = set(), []
    for day_file in sorted(docs_dir.glob("20??-??-??.json"), reverse=True)[:7]:
        if not re.match(r"^\d{4}-\d{2}-\d{2}\.json$", day_file.name):
            continue
        try:
            d = json.loads(day_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        for x in d.get("articles", []):
            url = x.get("url", "")
            if not url or url in seen:
                continue
            seen.add(url)
            items.append({
                "title": x.get("title", ""),
                "desc": x.get("one_liner", "") or x.get("summary", ""),
                "link": url,
                "category": x.get("category", ""),
            })
            if len(items) >= 50:
                break
        if len(items) >= 50:
            break

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        "<title>AI ニュース TOP10</title>",
        f"<link>{WEB_BASE}</link>",
        "<description>世界のAIニュースを毎朝日本語で厳選してお届け</description>",
        "<language>ja</language>",
    ]
    for it in items:
        parts.append(
            "<item>"
            f"<title>{xml_escape(it['title'])}</title>"
            f"<link>{xml_escape(it['link'])}</link>"
            f"<description>{xml_escape(it['desc'])}</description>"
            f"<category>{xml_escape(it['category'])}</category>"
            f'<guid isPermaLink="true">{xml_escape(it["link"])}</guid>'
            "</item>"
        )
    parts.append("</channel></rss>")
    (docs_dir / "feed.xml").write_text("\n".join(parts), encoding="utf-8")
    print(f"✅ feed.xml 更新 ({len(items)} 記事)")


def build_pages():
    """
    GitHub Pages 用のファイルを生成する
    """
    script_dir = Path(__file__).parent
    output_dir = Path(output_dir_path)
    docs_dir = script_dir / "docs"
    
    # docs ディレクトリを確保
    docs_dir.mkdir(exist_ok=True)
    
    # output 内の全 Markdown ファイルを取得（旧形式 + 新形式）
    md_files_old = sorted(output_dir.glob("ai_news_*.md"), reverse=True)
    md_files_new = sorted(output_dir.glob("morning_brief_*.md"), reverse=True)
    json_files_new = sorted(output_dir.glob("morning_brief_*.json"), reverse=True)

    # Morning Brief JSON 直接取り込み（最優先 — 構造化データがより豊富）
    archives = []
    processed_dates = set()

    for json_file in json_files_new:
        match = re.search(r'morning_brief_(\d{4})(\d{2})(\d{2})', json_file.name)
        if not match:
            continue

        year, month, day = match.groups()
        date_str = f"{year}年{month}月{day}日"
        file_date = f"{year}-{month}-{day}"

        if file_date in processed_dates:
            continue

        try:
            # 差分ビルド: 出力が既に存在し、ソースより新しければスキップ
            date_json_out = docs_dir / f"{year}-{month}-{day}.json"
            if date_json_out.exists() and date_json_out.stat().st_mtime >= json_file.stat().st_mtime:
                # アーカイブ一覧には追加（スキップしても一覧に出す必要がある）
                archives.append({
                    "date": date_str,
                    "path": f"{year}-{month}-{day}.json",
                    "count": -1,  # カウント不明（再読み込みしない）
                })
                processed_dates.add(file_date)
                print(f"⏭️  {json_file.name} → 変更なし（スキップ）")
                continue

            data = json.loads(json_file.read_text(encoding="utf-8"))
            articles = data.get("articles", [])
            if not articles:
                continue

            # JSON → Pages JSON 変換
            parsed = {
                "updated": date_str,
                "theme": data.get("theme", ""),
                "morning_comment": data.get("morning_comment", ""),
                "articles": [{
                    "title": a.get("title_ja", a.get("title", "")),
                    "category": a.get("category", "未分類"),
                    "summary": a.get("summary_ja", a.get("summary", "")),
                    "one_liner": a.get("one_liner", ""),
                    "why_important": a.get("why_important", ""),
                    "action_item": a.get("action_item", ""),
                    "source": a.get("source", ""),
                    "url": a.get("url", "")
                } for a in articles]
            }

            date_json_path = docs_dir / f"{file_date}.json"
            with open(date_json_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)

            archives.append({
                "date": date_str,
                "path": f"{file_date}.json",
                "count": len(articles)
            })
            processed_dates.add(file_date)
            print(f"✅ {json_file.name} → {file_date}.json ({len(articles)} 件)")
        except Exception as e:
            print(f"⚠️ Skip {json_file.name}: {e}")

    # 旧形式 Markdown ファイルも処理（後方互換）
    all_md_files = md_files_new + md_files_old
    
    if not all_md_files and not archives:
        print("⚠️ ニュースファイルが見つかりません")
        return
    
    for md_file in all_md_files:
        # 両方のファイル名パターンに対応
        match = re.search(r'(?:ai_news|morning_brief)_(\d{4})(\d{2})(\d{2})', md_file.name)
        if not match:
            continue
        
        year, month, day = match.groups()[:3]
        date_str = f"{year}年{month}月{day}日"
        file_date = f"{year}-{month}-{day}"

        # JSON で既に処理済みならスキップ
        if file_date in processed_dates:
            continue

        # Markdown を解析
        content = md_file.read_text(encoding="utf-8")
        parsed = parse_markdown_news(content)
        
        if not parsed["articles"]:
            continue
        
        # 日付別 JSON を保存
        date_json_path = docs_dir / f"{file_date}.json"
        with open(date_json_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        
        # アーカイブ一覧に追加
        archives.append({
            "date": date_str,
            "path": f"{file_date}.json",
            "count": len(parsed["articles"])
        })
        processed_dates.add(file_date)
        
        print(f"✅ {md_file.name} → {file_date}.json ({len(parsed['articles'])} 件)")
    
    # 最新のニュースを latest.json として保存
    if archives:
        latest_date = archives[0]["path"]
        latest_json_path = docs_dir / latest_date
        if latest_json_path.exists():
            shutil.copy(latest_json_path, docs_dir / "latest.json")
            print("✅ latest.json 更新")

    # 最新のグローバルニュースを global_latest.json として保存
    global_files = sorted(docs_dir.glob("global_20??-??-??.json"), reverse=True)
    if global_files:
        shutil.copy(global_files[0], docs_dir / "global_latest.json")
        print(f"✅ global_latest.json 更新 ← {global_files[0].name}")
    
    # アーカイブ一覧は docs/ に蓄積された日次 JSON を正典として再構築する。
    # output/ は一時フォルダで履歴が残らない（CI の毎回チェックアウトで当日分しか
    # 存在しない）ため、output/ 由来の archives を索引にすると当日 1 件で上書き
    # されてしまう。docs/YYYY-MM-DD.json（global_/latest/archive/column を除く）を
    # 走査して全期間の索引を作る。
    date_file_re = re.compile(r'^(\d{4})-(\d{2})-(\d{2})\.json$')
    unique_archives = []
    for day_file in sorted(docs_dir.glob("20??-??-??.json"), reverse=True):
        m = date_file_re.match(day_file.name)
        if not m:
            continue
        y, mo, d = m.groups()
        try:
            day_data = json.loads(day_file.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️ Skip {day_file.name}: {e}")
            continue
        unique_archives.append({
            "date": f"{y}年{mo}月{d}日",
            "path": day_file.name,
            "count": len(day_data.get("articles", [])),
        })

    archive_data = {"archives": unique_archives}
    with open(docs_dir / "archive.json", "w", encoding="utf-8") as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)

    print(f"✅ archive.json 更新 ({len(unique_archives)} 件)")

    # --- Column Processing ---
    column_dir = docs_dir / "columns"  # generate_weekly_column.py saves here

    columns_files = sorted(column_dir.glob("weekly_column_*.md"), reverse=True)
    columns_list = []

    for cfile in columns_files:
        # Patter: weekly_column_YYYYMMDD.md
        match = re.search(r'weekly_column_(\d{4})(\d{2})(\d{2})', cfile.name)
        if not match:
            continue
        
        y, m, d = match.groups()
        date_display = f"{y}年{m}月{d}日"
        
        content = cfile.read_text(encoding="utf-8")
        
        # Simple parse: Title is line 1, Body is rest
        lines = content.split('\n')
        title = lines[0].replace('# ', '').strip()
        body = "\n".join(lines[1:]).strip()
        
        # Save individual JSON
        c_json_path = docs_dir / f"column_{y}{m}{d}.json"
        with open(c_json_path, "w", encoding="utf-8") as f:
            json.dump({"title": title, "date": date_display, "body": body}, f, ensure_ascii=False, indent=2)
            
        columns_list.append({
            "date": date_display,
            "title": title,
            "path": f"column_{y}{m}{d}.json"
        })
        print(f"✅ Column Processed: {cfile.name}")

    with open(docs_dir / "columns.json", "w", encoding="utf-8") as f:
        json.dump({"columns": columns_list}, f, ensure_ascii=False, indent=2)
    print(f"✅ columns.json 更新 ({len(columns_list)} 件)")

    # --- 拡散性・発見性の拡張（Phase 2。各処理は独立し、失敗してもビルドを止めない） ---
    for label, fn in [
        ("OGP画像", generate_ogp_image),
        ("OGP/プリレンダリング", inject_ogp_and_prerender),
        ("sitemap.xml", generate_sitemap),
        ("feed.xml", generate_feed),
    ]:
        try:
            fn(docs_dir)
        except Exception as e:
            print(f"⚠️ {label} 生成スキップ: {e}")

    print("🎉 ビルド完了!")


if __name__ == "__main__":
    build_pages()
