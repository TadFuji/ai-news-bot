#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db_utils.py — データベース操作の共通ユーティリティ

save_to_db.py / save_global_news.py で共有される
接続・テーブル初期化・記事保存・実行ログ保存の共通関数を提供する。
"""

import os
import sqlite3
import datetime
from pathlib import Path

# ===== 設定 =====
PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "ai_news.db"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")
JST = datetime.timezone(datetime.timedelta(hours=9))

# カテゴリの日本語→英語マッピング
CATEGORY_JA_MAP = {
    "最新技術": "technology",
    "業務効率化": "business",
    "法規制・倫理": "ethics",
    "日本市場": "japan",
    "リスク管理": "ethics",
    "ライフスタイル": "business",
}

VALID_CATEGORIES = ["policy", "business", "technology", "ethics", "market"]
VALID_REGIONS = ["japan", "usa", "china", "india", "eu"]


def get_db_connection():
    """データベース接続を取得する

    Returns:
        tuple: (connection, db_type) — db_type は "sqlite" または "mysql"
    """
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


def normalize_category(category):
    """カテゴリを正規化する（日本語→英語変換含む）"""
    if category in CATEGORY_JA_MAP:
        category = CATEGORY_JA_MAP[category]
    if category not in VALID_CATEGORIES:
        category = "technology"
    return category


def normalize_region(region):
    """地域を正規化する"""
    if region not in VALID_REGIONS:
        region = "usa"
    return region


def parse_published_at(published_at_str):
    """公開日時文字列をdatetimeオブジェクトに変換する"""
    if not published_at_str:
        return None
    try:
        return datetime.datetime.fromisoformat(
            published_at_str.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return datetime.datetime.now(datetime.timezone.utc)


def save_articles(conn, db_type, articles):
    """記事をデータベースに保存する

    Args:
        conn: DB接続
        db_type: "sqlite" or "mysql"
        articles: 記事リスト

    Returns:
        tuple: (saved_count, skipped_count)
    """
    cursor = conn.cursor()
    saved = 0
    skipped = 0

    for article in articles:
        url = article.get("url", "")
        title = article.get("title", "")
        description = article.get("summary", article.get("description", ""))
        category = normalize_category(article.get("category", "technology"))
        region = normalize_region(article.get("region", "usa"))
        source = article.get("source", "")
        published_at = parse_published_at(article.get("publishedAt", ""))

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


def save_collection_run(conn, db_type, run_at, articles_collected,
                        articles_saved, articles_skipped,
                        status="success", notes=""):
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
