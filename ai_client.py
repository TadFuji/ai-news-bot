import os
import json
import time
import datetime
from google import genai
from google.genai import types
from config import GEMINI_MODEL


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
    articles_sorted = sorted(
        articles,
        key=lambda x: x.get('published', datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        reverse=True,
    )

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
あなたは、日本市場のビジネスパーソンや一般消費者の動向に精通した「AIトレンドアナリスト」です。世界中の膨大なニュースの中から、日本のビジネスパーソンにとって真に価値のあるAI関連情報をキュレーションする専門家として振る舞ってください。

# Task
提供されたニュースリストから、以下の手順で情報を処理し、出力形式に従ってJSONを出力してください。

## Step 1: Strict Filtering (AI-Only Scope)
ニュースの内容が「人工知能（AI）」に直接関連しているものだけを抽出してください。
- **対象:** 生成AI（LLM, 画像生成）、機械学習、AI搭載ハードウェア、AIに関する法規制・倫理・セキュリティ。
- **除外:** AI機能がメインではない単なる新製品（スマホ、PC等）、AIと関係のないIT業界のM&Aや決算情報。
- **注意:** 「日本人に関連するから」という理由だけで、AI以外のニュース（政治、経済、芸能など）を絶対に含めないでください。

## Step 2: Importance Scoring (Target Audience: Japanese Business Professionals)
抽出したAIニュースを、以下のペルソナに基づいて評価し、1-10の重要度（importance_score）を算出してください。

### 👤 Target Persona Profile
- **属性:** 日本在住のビジネスパーソン。働き盛りの中間管理職、または専門職。家庭を持つ層も多い。
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
重要度スコアに基づき、**必ず10件** を以下のJSON配列で出力してください。
候補が10件以上ある場合は厳選し、10件未満の場合は候補の全件を採用してください。
**重要: 配列には必ず10件（候補が10件未満なら全件）を含めてください。5件や7件では不十分です。**

## 出力ルール（厳守）
- 出力テキスト（summary_ja, reason, why_important 等）に**特定の年齢層（「40代」「30代」等）を絶対に記載しないでください**。読者層を限定する表現は不要です。
- 「ビジネスパーソン」「エンジニア」「管理職」など役割ベースの表現は許可します。

---
記事リスト:
{articles_text}
---

重要: JSON配列のみを出力してください。マークダウンのコードブロックなどは不要です。
"""

    # Gemini 構造化出力用のスキーマ定義
    article_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "index": types.Schema(type=types.Type.INTEGER, description="元の記事番号"),
            "title_ja": types.Schema(type=types.Type.STRING, description="日本語タイトル"),
            "summary_ja": types.Schema(
                type=types.Type.STRING,
                description="詳細な日本語要約。ビジネスパーソンに具体的にどう影響するかを含め、情報を網羅して記述",
            ),
            "one_liner": types.Schema(
                type=types.Type.STRING,
                description="20文字以内の核心（例: 'AI議事録が全社標準へ'）",
            ),
            "why_important": types.Schema(
                type=types.Type.STRING,
                description="来週の仕事への具体的影響を1文で",
            ),
            "action_item": types.Schema(
                type=types.Type.STRING,
                description="今日すぐできる1つの行動",
            ),
            "category": types.Schema(
                type=types.Type.STRING,
                description="カテゴリ: 業務効率化, リスク管理, 日本市場, 最新技術, 法規制・倫理, ライフスタイル のいずれか",
            ),
            "importance_score": types.Schema(
                type=types.Type.INTEGER,
                description="重要度スコア 1-10",
            ),
            "reason": types.Schema(
                type=types.Type.STRING,
                description="選定理由（なぜ日本のビジネスパーソンにとって重要なのか記述）",
            ),
        },
        required=[
            "index", "title_ja", "summary_ja", "one_liner",
            "why_important", "action_item", "category",
            "importance_score", "reason",
        ],
    )

    response_schema = types.Schema(
        type=types.Type.ARRAY,
        items=article_schema,
    )

    print("🧠 Gemini 3 Flash Preview で処理中...")
    start = time.time()

    max_retries = 2
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                wait_sec = 2 ** attempt
                print(f"   🔄 リトライ {attempt}/{max_retries}（{wait_sec}秒待機）...")
                time.sleep(wait_sec)

            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            response_text = response.text.strip()
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
                else:
                    print(f"   ⚠️ index {idx + 1} が範囲外（記事数: {len(articles_sorted)}）— スキップ")

            # スコアで降順ソート
            processed.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

            elapsed = time.time() - start
            print(f"✅ Gemini 処理完了: {len(processed)} 件（{elapsed:.1f}秒）")
            return processed[:max_articles]

        except Exception as e:
            last_error = e
            print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
            # INVALID_ARGUMENT (API key issue) はリトライしても無駄
            if "INVALID_ARGUMENT" in str(e) or "API Key" in str(e):
                print("   🛑 APIキーエラーのためリトライ中止")
                break

    # 全リトライ失敗時のフォールバック
    elapsed = time.time() - start
    print(f"❌ Gemini API エラー（全{max_retries + 1}回, {elapsed:.1f}秒）: {last_error}")
    fallback = []
    for a in articles_sorted[:max_articles]:
        ac = a.copy()
        if isinstance(ac.get('published'), datetime.datetime):
            ac['published'] = ac['published'].isoformat()
        # 翻訳済みフィールドが存在する場合はtitle/summaryに転写
        if ac.get('title_ja'):
            ac['title'] = ac['title_ja']
        if ac.get('summary_ja'):
            ac['summary'] = ac['summary_ja']
        fallback.append(ac)
    return fallback
