import os
import json
import datetime
from google import genai

def process_with_gemini(articles: list[dict], max_articles: int = 10) -> list[dict]:
    """
    Gemini APIを使用して記事を翻訳・要約し、重要度スコアを付与する
    
    Args:
        articles: 記事リスト
        max_articles: 処理する最大記事数
    
    Returns:
        処理済み記事リスト（日本語タイトル、日本語要約、スコア付き）
    """
    # APIキーを取得 (.envから読み込まれていることを前提)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY 環境変数が設定されていません")
        return articles[:max_articles]
    
    # Geminiを設定
    client = genai.Client(api_key=api_key)
    
    # 記事情報をまとめてプロンプトに含める
    articles_text = ""
    # Limit to top 30 newest items to avoid token limits
    articles_sorted = sorted(articles, key=lambda x: x.get('published', datetime.datetime.min) or datetime.datetime.min, reverse=True)
    
    for i, article in enumerate(articles_sorted[:30]): 
        articles_text += f"""
---
記事{i+1}:
タイトル: {article['title']}
ソース: {article['source']} ({article['region']})
概要: {article['summary'][:1500]}
URL: {article['url']}
"""
    
    prompt = f"""# Role Definition
あなたは、日本市場のビジネスパーソンや一般消費者の動向に精通した「AIトレンドアナリスト」です。世界中の膨大なニュースの中から、日本の40代にとって真に価値のあるAI関連情報をキュレーションする専門家として振る舞ってください。

# Task
提供されたニュースリストから、以下の手順で情報を処理し、出力形式に従ってJSONを出力してください。

## Step 1: Strict Filtering (AI-Only Scope)
ニュースの内容が「人工知能（AI）」に直接関連しているものだけを抽出してください。
- **対象:** 生成AI（LLM, 画像生成）、機械学習、AI搭載ハードウェア、AIに関する法規制・倫理・セキュリティ。
- **除外:** AI機能がメインではない単なる新製品（スマホ、PC等）、AIと関係のないIT業界のM&Aや決算情報。
- **注意:** 「40代日本人に関連するから」という理由だけで、AI以外のニュース（政治、経済、芸能など）を絶対に含めないでください。

## Step 2: Importance Scoring (Target Audience: 40-year-old Japanese)
抽出したAIニュースを、以下の「40代の一般的な日本人」のペルソナに基づいて評価し、1-10の重要度（importance_score）を算出してください。

### 👤 Target Persona Profile
- **属性:** 日本在住、40歳前後。働き盛りの中間管理職、または専門職。家庭を持つ層も多い。
- **関心事（High Priority）:**
    1. 業務効率化・生存戦略:「自分の仕事がAIでどう楽になるか」または「AIに仕事を奪われないか」。Excel/PPT作成支援、議事録自動化、日本語対応の有無。
    2. リスク管理: 子供の教育への影響、高齢親を狙う詐欺（ディープフェイク）、セキュリティ、著作権問題。
    3. 身近な利便性: LINEやスマホなど、日常的に使うツールへのAI実装。
    4. 日本社会への影響: 日本企業（ソフトバンク、NTT等）の動向や、日本政府のAI規制。

## Step 3: "So What?" 分析（読者を動かす付加価値）
各記事に対して、以下の3つの視点を追加してください。これが読者の行動を変える核心です。
- **one_liner**: ニュースの本質を20文字以内で表現（例:「AI議事録が全社標準へ」）
- **why_important**: このニュースが読者の来週の仕事にどう影響するか、具体的に1文で（例:「月曜の会議から試せるレベルの精度です」）
- **action_item**: 読者が今日すぐできる1つの行動（例:「まず社内の定型業務リストを作ってみてください」）

## Step 4: Output Format
重要度スコアに基づき、上位最大10件を以下のJSON配列で出力してください。
該当するAIニュースが10件に満たない場合は、無理に埋めずある分だけ出力してください。

出力形式（JSON配列のみ）:
[
  {{
    "index": 元の記事番号,
    "title_ja": "日本語タイトル",
    "summary_ja": "詳細な日本語要約。40代のビジネスパーソンに具体的にどう影響するかを含め、情報を網羅して記述",
    "one_liner": "20文字以内の核心（例: 'AI議事録が全社標準へ'）",
    "why_important": "来週の仕事への具体的影響を1文で",
    "action_item": "今日すぐできる1つの行動",
    "category": "以下のいずれか（業務効率化, リスク管理, 日本市場, 最新技術, 法規制・倫理, ライフスタイル）",
    "importance_score": 1-10,
    "reason": "選定理由（なぜ40代日本人にとって重要なのか記述）"
  }},
  ...
]

---
記事リスト:
{articles_text}
---

重要: JSON配列のみを出力してください。マークダウンのコードブロックなどは不要です。
"""
    
    print("🧠 Gemini 3 Flash Preview で処理中...")
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", # User requested specific model
            contents=prompt
        )
        response_text = response.text.strip()
        
        # JSONをパース（コードブロックがある場合は除去）
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Handle ```json vs ```
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines)
        
        results = json.loads(response_text)
        
        # 結果を元の記事情報とマージ
        processed = []
        for result in results:
            idx = result.get("index", 1) - 1
            if 0 <= idx < len(articles_sorted):
                article = articles_sorted[idx].copy()
                article["title_ja"] = result.get("title_ja", article["title"])
                article["summary_ja"] = result.get("summary_ja", "要約なし")
                article["one_liner"] = result.get("one_liner", "")
                article["why_important"] = result.get("why_important", "")
                article["action_item"] = result.get("action_item", "")
                article["category"] = result.get("category", "未分類")
                article["importance_score"] = result.get("importance_score", 5)
                article["reason"] = result.get("reason", "")
                
                # Convert datetime to string for JSON serialization
                if isinstance(article.get('published'), datetime.datetime):
                    article['published'] = article['published'].isoformat()
                    
                processed.append(article)
        
        # スコアで降順ソート
        processed.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
        
        print(f"✅ Gemini 処理完了: {len(processed)} 件")
        return processed[:max_articles]
        
    except Exception as e:
        print(f"❌ Gemini API エラー: {e}")
        # フォールバック: 元の記事をそのまま返す (JSON serializable fix needed)
        fallback = []
        for a in articles_sorted[:max_articles]:
            ac = a.copy()
            if isinstance(ac.get('published'), datetime.datetime):
                ac['published'] = ac['published'].isoformat()
            fallback.append(ac)
        return fallback
