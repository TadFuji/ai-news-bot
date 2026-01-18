from datetime import datetime, timedelta, timezone
from config import AI_KEYWORDS

def filter_by_time(articles: list[dict]) -> list[dict]:
    """
    前日7時〜当日7時（JST）に公開された記事のみを抽出する
    
    Args:
        articles: 記事リスト
    
    Returns:
        フィルタリングされた記事リスト
    """
    # JST (UTC+9) で現在時刻を取得
    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)
    
    # 実行時点から過去48時間を対象にする（週末などでニュースが少ない場合もカバー）
    end_time = now_jst
    start_time = end_time - timedelta(hours=48)
    
    # UTC に変換して比較
    start_time_utc = start_time.astimezone(timezone.utc)
    end_time_utc = end_time.astimezone(timezone.utc)
    
    filtered = []
    for article in articles:
        if article["published"]:
            pub_time = article["published"]
            if start_time_utc <= pub_time < end_time_utc:
                filtered.append(article)
    
    start_str = start_time.strftime('%m/%d %H:%M')
    end_str = end_time.strftime('%m/%d %H:%M')
    print(f"📅 {start_str} 〜 {end_str} (JST) の記事: {len(filtered)} 件")
    return filtered


def filter_by_ai_keywords(articles: list[dict]) -> list[dict]:
    """
    AI関連のキーワードを含む記事のみを抽出する
    
    Args:
        articles: 記事リスト
    
    Returns:
        AI関連の記事リスト
    """
    filtered = []
    for article in articles:
        text = f"{article['title']} {article['summary']}".lower()
        for keyword in AI_KEYWORDS:
            if keyword.lower() in text:
                filtered.append(article)
                break
    
    print(f"🤖 AI関連の記事: {len(filtered)} 件")
    return filtered


def remove_duplicates(articles: list[dict]) -> list[dict]:
    """
    重複する記事を削除する（タイトルの類似度でチェック）
    
    Args:
        articles: 記事リスト
    
    Returns:
        重複を除去した記事リスト
    """
    seen_titles = set()
    unique = []
    
    for article in articles:
        # タイトルを正規化（小文字化、空白除去）
        normalized = article["title"].lower().strip()
        
        # 既に同じタイトルがあればスキップ
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique.append(article)
    
    print(f"📋 重複除去後: {len(unique)} 件")
    return unique
