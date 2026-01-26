#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Pages ビルドスクリプト

output/ 内の Markdown ファイルを解析し、
GitHub Pages 用の JSON データを生成します。
"""

import os
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
    
    # 記事を抽出（## 1. タイトル 形式）
    article_pattern = re.compile(
        r'##\s*\d+\.\s*(.+?)\n\n(.+?)\n\n-\s*\*\*出典\*\*:\s*(.+?)\n-\s*\*\*URL\*\*:\s*(.+?)(?:\n|$)',
        re.DOTALL
    )
    
    for match in article_pattern.finditer(content):
        result["articles"].append({
            "title": match.group(1).strip(),
            "summary": match.group(2).strip(),
            "source": match.group(3).strip(),
            "url": match.group(4).strip()
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
    
    # output 内の全 Markdown ファイルを取得
    md_files = sorted(output_dir.glob("ai_news_*.md"), reverse=True)
    
    if not md_files:
        print("⚠️ ニュースファイルが見つかりません")
        return
    
    archives = []
    
    for md_file in md_files:
        # ファイル名から日付を抽出（ai_news_20260116_1453.md）
        match = re.search(r'ai_news_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})', md_file.name)
        if not match:
            continue
        
        year, month, day, hour, minute = match.groups()
        date_str = f"{year}年{month}月{day}日"
        file_date = f"{year}-{month}-{day}"
        
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
        
        print(f"✅ {md_file.name} → {file_date}.json ({len(parsed['articles'])} 件)")
    
    # 最新のニュースを latest.json として保存
    if archives:
        latest_date = archives[0]["path"]
        latest_json_path = docs_dir / latest_date
        if latest_json_path.exists():
            shutil.copy(latest_json_path, docs_dir / "latest.json")
            print("✅ latest.json 更新")
    
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
    column_dir = output_dir.parent / "output" / "columns" # Correct path based on structure
    if not column_dir.exists():
        column_dir = output_dir / "columns" # Fallback check

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
