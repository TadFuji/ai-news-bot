#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
グローバルAIニュースをデータベースに保存するスクリプト
global_YYYY-MM-DD.json から読み込み、news_articlesとnews_collection_runsテーブルに保存する。
DATABASE_URLが設定されていない場合はSQLiteを使用する。
"""
import os
import json
import sqlite3
import datetime
from pathlib import Path

# ===== 設定 =====
PROJECT_ROOT = Path(__file__).parent
DOCS_DIR = PROJECT_ROOT / "docs"
DB_PATH = PROJECT_ROOT / "ai_news.db"

# データベースURL（環境変数から取得、なければSQLiteを使用）
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
JST = datetime.timezone(datetime.timedelta(hours=9))


def get_db_connection():
    """データベース接続を取得する"""
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"
    else:
        try:
            import pymysql
            from urllib.parse import urlparse
            parsed = urlparse(DATABASE_URL)
            conn = pymysql.connect(
                host=parsed.hostname,
                user=parsed.username,
                password=parsed.password,
                database=parsed.path.lstrip("/"),
                port=parsed.port or 3306,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor
            )
            return conn, "mysql"
        except ImportError:
            print("pymysqlが見つかりません。SQLiteにフォールバックします。")
            conn = sqlite3.connect(str(DB_PATH))
            conn.row_factory = sqlite3.Row
            return conn, "sqlite"


def init_db(conn, db_type):
    """データベーステーブルを初期化する"""
    cursor = conn.cursor()

    if db_type == "sqlite":
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT CHECK(category IN ('policy', 'business', 'technology', 'ethics', 'market')),
                region TEXT CHECK(region IN ('japan', 'usa', 'china', 'india', 'eu')),
                url VARCHAR(1024) UNIQUE,
                source VARCHAR(256),
                publishedAt TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_collection_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TIMESTAMP NOT NULL,
                articles_collected INTEGER DEFAULT 0,
                articles_saved INTEGER DEFAULT 0,
                articles_skipped INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_articles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category ENUM('policy', 'business', 'technology', 'ethics', 'market'),
                region ENUM('japan', 'usa', 'china', 'india', 'eu'),
                url VARCHAR(1024) UNIQUE,
                source VARCHAR(256),
                publishedAt TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_collection_runs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                run_at TIMESTAMP NOT NULL,
                articles_collected INT DEFAULT 0,
                articles_saved INT DEFAULT 0,
                articles_skipped INT DEFAULT 0,
                status VARCHAR(50) DEFAULT 'success',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4
        """)

    conn.commit()
    print("✅ テーブルを初期化しました")


def load_global_news():
    """今日のグローバルニュースJSONを読み込む"""
    now_jst = datetime.datetime.now(JST)
    today_str = now_jst.strftime("%Y-%m-%d")

    json_path = DOCS_DIR / f"global_{today_str}.json"

    if not json_path.exists():
        yesterday = now_jst - datetime.timedelta(days=1)
        json_path = DOCS_DIR / f"global_{yesterday.strftime('%Y-%m-%d')}.json"

    if not json_path.exists():
        print(f"❌ グローバルニュースファイルが見つかりません: {json_path}")
        return None

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ ニュースファイルを読み込みました: {json_path}")
    return data


def save_articles(conn, db_type, articles):
    """記事をデータベースに保存する"""
    cursor = conn.cursor()
    saved = 0
    skipped = 0

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")
        description = article.get("summary", article.get("description", ""))
        category = article.get("category", "technology")
        region = article.get("region", "usa")
        source = article.get("source", "")
        published_at_str = article.get("publishedAt", "")

        # カテゴリの正規化
        valid_categories = ["policy", "business", "technology", "ethics", "market"]
        if category not in valid_categories:
            category = "technology"

        # 地域の正規化
        valid_regions = ["japan", "usa", "china", "india", "eu"]
        if region not in valid_regions:
            region = "usa"

        # 公開日時のパース
        published_at = None
        if published_at_str:
            try:
                published_at = datetime.datetime.fromisoformat(
                    published_at_str.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                published_at = datetime.datetime.now(datetime.timezone.utc)

        try:
            if db_type == "sqlite":
                cursor.execute("""
                    INSERT OR IGNORE INTO news_articles
                    (title, description, category, region, url, source, publishedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    title, description, category, region, url, source,
                    published_at.isoformat() if published_at else None
                ))
                if cursor.rowcount > 0:
                    saved += 1
                    print(f"  ✅ 保存: {title[:60]}...")
                else:
                    skipped += 1
                    print(f"  ⏭️  スキップ（重複）: {title[:60]}...")
            else:
                cursor.execute("""
                    INSERT IGNORE INTO news_articles
                    (title, description, category, region, url, source, publishedAt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    title, description, category, region, url, source,
                    published_at
                ))
                if cursor.rowcount > 0:
                    saved += 1
                    print(f"  ✅ 保存: {title[:60]}...")
                else:
                    skipped += 1
                    print(f"  ⏭️  スキップ（重複）: {title[:60]}...")
        except Exception as e:
            print(f"  ❌ エラー: {title[:60]}... - {e}")
            skipped += 1

    conn.commit()
    return saved, skipped


def save_collection_run(conn, db_type, run_at, articles_collected, articles_saved, articles_skipped, status="success", notes=""):
    """実行ログをデータベースに保存する"""
    cursor = conn.cursor()

    if db_type == "sqlite":
        cursor.execute("""
            INSERT INTO news_collection_runs
            (run_at, articles_collected, articles_saved, articles_skipped, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            run_at.isoformat(),
            articles_collected,
            articles_saved,
            articles_skipped,
            status,
            notes
        ))
    else:
        cursor.execute("""
            INSERT INTO news_collection_runs
            (run_at, articles_collected, articles_saved, articles_skipped, status, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            run_at,
            articles_collected,
            articles_saved,
            articles_skipped,
            status,
            notes
        ))

    conn.commit()
    print("✅ 実行ログを保存しました")


def main():
    print("=" * 60)
    print("🗄️  グローバルAIニュース データベース保存スクリプト")
    print("=" * 60)
    db_display = DATABASE_URL[:50] if len(DATABASE_URL) > 50 else DATABASE_URL
    print(f"DATABASE_URL: {db_display}...")

    run_at = datetime.datetime.now(JST)

    # 1. データベース接続
    print("\n📡 データベースに接続中...")
    conn, db_type = get_db_connection()
    print(f"✅ 接続成功 (タイプ: {db_type})")

    # 2. テーブル初期化
    print("\n🔧 テーブルを初期化中...")
    init_db(conn, db_type)

    # 3. ニュースデータ読み込み
    print("\n📰 グローバルニュースデータを読み込み中...")
    data = load_global_news()

    if not data:
        save_collection_run(conn, db_type, run_at, 0, 0, 0, "error", "グローバルニュースファイルが見つかりません")
        conn.close()
        return

    articles = data.get("articles", [])
    print(f"   {len(articles)} 件の記事を読み込みました")

    # 4. 記事を保存
    print("\n💾 記事をデータベースに保存中...")
    saved, skipped = save_articles(conn, db_type, articles)

    print(f"\n📊 保存結果:")
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
        notes=f"グローバルニュース収集 | テーマ: {data.get('theme', '')}"
    )

    conn.close()

    print("\n" + "=" * 60)
    print("✅ データベース保存完了！")
    print("=" * 60)

    return saved, skipped


if __name__ == "__main__":
    main()
