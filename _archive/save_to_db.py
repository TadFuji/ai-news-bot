#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIニュースをデータベースに保存するスクリプト
docs/YYYY-MM-DD.json から読み込み、news_articlesとnews_collection_runsテーブルに保存する。
"""

import json
import datetime
from pathlib import Path

from db_utils import (
    get_db_connection, init_db, save_articles,
    save_collection_run, JST
)

# ===== 設定 =====
PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"


def load_today_news():
    """今日のニュースJSONを読み込む"""
    now_jst = datetime.datetime.now(JST)
    today_str = now_jst.strftime("%Y-%m-%d")

    json_path = DOCS_DIR / f"{today_str}.json"

    if not json_path.exists():
        # 昨日のファイルも確認
        yesterday = now_jst - datetime.timedelta(days=1)
        json_path = DOCS_DIR / f"{yesterday.strftime('%Y-%m-%d')}.json"

    if not json_path.exists():
        print(f"❌ ニュースファイルが見つかりません: {json_path}")
        return None

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ ニュースファイルを読み込みました: {json_path}")
    return data


def main():
    print("=" * 60)
    print("🗄️  AIニュース データベース保存スクリプト")
    print("=" * 60)

    run_at = datetime.datetime.now(JST)

    # 1. データベース接続
    print("\n📡 データベースに接続中...")
    conn, db_type = get_db_connection()
    print(f"✅ 接続成功 (タイプ: {db_type})")

    # 2. テーブル初期化
    print("\n🔧 テーブルを初期化中...")
    init_db(conn, db_type)

    # 3. ニュースデータ読み込み
    print("\n📰 ニュースデータを読み込み中...")
    data = load_today_news()

    if not data:
        save_collection_run(conn, db_type, run_at, 0, 0, 0, "error", "ニュースファイルが見つかりません")
        conn.close()
        return

    articles = data.get("articles", [])
    print(f"   {len(articles)} 件の記事を読み込みました")

    # 4. 記事を保存
    print("\n💾 記事をデータベースに保存中...")
    saved, skipped = save_articles(conn, db_type, articles)

    print("\n📊 保存結果:")
    print(f"   保存成功: {saved} 件")
    print(f"   スキップ（重複）: {skipped} 件")

    # 5. 実行ログを保存
    print("\n📝 実行ログを保存中...")
    save_collection_run(
        conn, db_type, run_at,
        articles_collected=len(articles),
        articles_saved=saved,
        articles_skipped=skipped,
        status="success",
        notes=f"テーマ: {data.get('theme', '')}"
    )

    conn.close()

    print("\n" + "=" * 60)
    print("✅ データベース保存完了！")
    print("=" * 60)

    return saved, skipped


if __name__ == "__main__":
    main()
