#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pages ビルドスクリプト

output/ 内の Markdown ファイルを解析し、
GitHub Pages 用の JSON データを生成します。
"""

import re
import json
import shutil
from pathlib import Path
from config import NEWS_BOT_OUTPUT_DIR as output_dir_path


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
    
    # アーカイブ一覧を日付で重複排除（同一日付は最新のもののみ保持）
    seen_dates = set()
    unique_archives = []
    for archive in archives:
        if archive["path"] not in seen_dates:
            seen_dates.add(archive["path"])
            unique_archives.append(archive)
    
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

    print("🎉 ビルド完了!")


if __name__ == "__main__":
    build_pages()
