from datetime import timezone
import feedparser
from dateutil import parser as date_parser
from config import RSS_FEEDS

def collect_from_rss_feeds() -> list[dict]:
    """
    複数のRSSフィードからニュース記事を収集する
    
    Returns:
        記事情報のリスト（タイトル、URL、公開日時、ソース名）
    """
    articles = []
    
    for feed_info in RSS_FEEDS:
        print(f"📡 {feed_info['name']} から記事を取得中...")
        try:
            feed = feedparser.parse(feed_info["url"])
            
            for entry in feed.entries:
                # 公開日時を取得（published または updated）
                pub_date = None
                if hasattr(entry, "published"):
                    pub_date = entry.published
                elif hasattr(entry, "updated"):
                    pub_date = entry.updated
                
                # 日時をパース
                parsed_date = None
                if pub_date:
                    try:
                        parsed_date = date_parser.parse(pub_date)
                        # タイムゾーンがない場合はUTCとして扱う
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass
                
                # 概要を取得
                summary = ""
                if hasattr(entry, "summary"):
                    summary = entry.summary
                elif hasattr(entry, "description"):
                    summary = entry.description
                
                articles.append({
                    "title": entry.title if hasattr(entry, "title") else "No Title",
                    "url": entry.link if hasattr(entry, "link") else "",
                    "published": parsed_date,
                    "summary": summary[:500] if summary else "",  # 最大500文字
                    "source": feed_info["name"],
                    "region": feed_info["region"],
                })
                
        except Exception as e:
            print(f"  ⚠️ エラー: {e}")
            continue
    
    print(f"✅ 合計 {len(articles)} 件の記事を取得しました")
    return articles
