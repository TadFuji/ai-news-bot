import os
from datetime import datetime, timedelta, timezone
from config import JST

def output_markdown(articles: list[dict]) -> str:
    """
    記事リストをMarkdown形式で出力する
    
    Args:
        articles: 処理済み記事リスト
    
    Returns:
        Markdown形式の文字列
    """
    now = datetime.now(JST)  # JST
    
    md = f"""# AI関連ニュース TOP10

**更新日時**: {now.strftime('%Y年%m月%d日 %H:%M')} (JST)

過去24時間以内に公開された、最も重要なAI関連ニュースを厳選してお届けします。

---

"""
    
    for i, article in enumerate(articles, 1):
        title = article.get("title_ja", article["title"])
        summary = article.get("summary_ja", article.get("summary", "要約なし"))
        url = article["url"]
        source = article["source"]
        
        md += f"""## {i}. {title}

{summary}

- **出典**: {source}
- **URL**: {url}

---

"""
    
    if not articles:
        md += "該当するAI関連ニュースは過去24時間以内に見つかりませんでした。\n"
    
    return md


def save_output(content: str, filepath: str) -> None:
    """
    コンテンツをファイルに保存する
    
    Args:
        content: 保存する内容
        filepath: 保存先ファイルパス
    """
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"💾 保存完了: {filepath}")
