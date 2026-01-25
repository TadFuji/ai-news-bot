import os
import json
from google import genai
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

def process_with_gemini(articles: list[dict], max_articles: int = 10) -> list[dict]:
    """
    Gemini APIを使用して記事を翻訳・要約し、重要度スコアを付与する
    
    Args:
        articles: 記事リスト
        max_articles: 処理する最大記事数
    
    Returns:
        処理済み記事リスト（日本語タイトル、日本語要約、スコア付き）
    """
    # APIキーを取得
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY 環境変数が設定されていません")
        return articles[:max_articles]
    
    # Geminiを設定
    client = genai.Client(api_key=api_key)
    
    # 記事情報をまとめてプロンプトに含める
    articles_text = ""
    for i, article in enumerate(articles[:30]):  # 最大30件を処理対象
        articles_text += f"""
---
記事{i+1}:
タイトル: {article['title']}
ソース: {article['source']} ({article['region']})
概要: {article['summary'][:300]}
URL: {article['url']}
"""
    
    prompt = f"""あなたはAI・テクノロジー分野の専門家です。
以下のニュース記事リストから、最も重要で影響力のある10件を選び、日本語で出力してください。

選定基準:
- グローバルな影響度（政策、ビジネス、技術革新）
- AI分野における重要性
- 日本のビジネスパーソンへの関連性
- 重複する内容は1つだけ選ぶ

出力形式（JSON配列）:
[
  {{
    "index": 元の記事番号,
    "title_ja": "日本語タイトル",
    "summary_ja": "2〜3文の日本語要約。ビジネス専門家向けに分かりやすく",
    "importance_score": 1-10の重要度スコア,
    "reason": "選定理由（1文）"
  }},
  ...
]

---
記事リスト:
{articles_text}
---

重要: 必ず10件選び、JSON配列のみを出力してください。マークダウンのコードブロックは不要です。
"""
    
    print("🧠 Gemini API で処理中...")
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=prompt
        )
        response_text = response.text.strip()
        
        # JSONをパース（コードブロックがある場合は除去）
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])
        
        results = json.loads(response_text)
        
        # 結果を元の記事情報とマージ
        processed = []
        for result in results:
            idx = result.get("index", 1) - 1
            if 0 <= idx < len(articles):
                article = articles[idx].copy()
                article["title_ja"] = result.get("title_ja", article["title"])
                article["summary_ja"] = result.get("summary_ja", "要約なし")
                article["importance_score"] = result.get("importance_score", 5)
                article["reason"] = result.get("reason", "")
                processed.append(article)
        
        # スコアで降順ソート
        processed.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        
        print(f"✅ Gemini 処理完了: {len(processed)} 件")
        return processed[:max_articles]
        
    except Exception as e:
        print(f"❌ Gemini API エラー: {e}")
        # フォールバック: 元の記事をそのまま返す
        return articles[:max_articles]
