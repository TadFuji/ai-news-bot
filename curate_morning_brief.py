"""
curate_morning_brief.py — Stage 2: 朝刊キュレーション

Stage 1 (03:00 JST) で収集・1次スコアリングされた候補記事を読み込み、
Gemini 2次プロンプトで「編集的キュレーション」を実行する。

出力: output/morning_brief_YYYYMMDD.json
"""

import os
import json
import glob
import sys
import time
import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv
from config import NEWS_BOT_OUTPUT_DIR, JST, GEMINI_MODEL

load_dotenv()


def load_candidates():
    """本日の候補JSONをすべて読み込み、記事を統合・重複排除する"""
    today_str = datetime.datetime.now(JST).strftime("%Y%m%d")

    # candidates_YYYYMMDD_*.json と ai_news_YYYYMMDD_*.json の両方を読む
    patterns = [
        os.path.join(NEWS_BOT_OUTPUT_DIR, f"candidates_{today_str}_*.json"),
        os.path.join(NEWS_BOT_OUTPUT_DIR, f"ai_news_{today_str}_*.json"),
    ]

    all_articles = []
    files_loaded = 0

    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                articles = data.get("articles", []) if isinstance(data, dict) else data
                all_articles.extend(articles)
                files_loaded += 1
                print(f"  📄 Loaded: {os.path.basename(filepath)} ({len(articles)} articles)")
            except Exception as e:
                print(f"  ⚠️ Skip {filepath}: {e}")

    # URL重複排除（直近のものを優先）
    seen_urls = set()
    unique = []
    for a in reversed(all_articles):  # 新しいものを優先
        url = a.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(a)

    unique.reverse()  # 元の順序に戻す

    print(f"\n📊 候補統合: {files_loaded} files → {len(all_articles)} articles → {len(unique)} unique")
    return unique


def get_delivered_urls(days=3):
    """過去N日間の morning_brief_*.json から配信済みURLを取得"""
    delivered = set()
    today = datetime.datetime.now(JST)

    for i in range(1, days + 1):
        past_date = (today - datetime.timedelta(days=i)).strftime("%Y%m%d")
        filepath = os.path.join(NEWS_BOT_OUTPUT_DIR, f"morning_brief_{past_date}.json")

        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for article in data.get("articles", []):
                    url = article.get("url", "")
                    if url:
                        delivered.add(url)
                print(f"  📋 既配信: {os.path.basename(filepath)} ({len(data.get('articles', []))} articles)")
            except Exception as e:
                print(f"  ⚠️ Skip {filepath}: {e}")

    print(f"  🔒 過去{days}日間の配信済みURL: {len(delivered)} 件")
    return delivered


def curate_with_gemini(candidates):
    """Gemini 2次プロンプトで編集的キュレーションを実行"""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY が設定されていません")
        return None

    client = genai.Client(api_key=api_key)

    # 候補記事をテキスト化
    articles_text = ""
    for i, a in enumerate(candidates[:30], 1):
        title = a.get("title_ja", a.get("title", "No Title"))
        summary = a.get("summary_ja", a.get("summary", ""))
        category = a.get("category", "未分類")
        score = a.get("importance_score", 0)
        source = a.get("source", "Unknown")
        url = a.get("url", "")

        articles_text += f"""
---
候補{i}:
タイトル: {title}
1次スコア: {score}/10
カテゴリ: {category}
ソース: {source}
要約: {summary[:500]}
URL: {url}
"""

    prompt = f"""# Role Definition
あなたは「Antigravity Morning Brief」の編集長です。
1次選別済みのAIニュース候補から、今朝の読者に届ける最終版を編集してください。

# Mission
単なるスコア順の並べ替えではなく、**今日のAI業界の空気感を伝える「朝刊1面」** を作ることが目的です。

# Instructions

## Step 1: テーマ発見
候補記事を俯瞰し、今日のニュースに通底する「テーマ」を1つ特定してください。
例: 「エージェント機能の民主化が加速している」「日本企業のAI投資が本格化」など。

## Step 2: 記事選定（必ず10件）
以下の基準で **必ず10件** を選んでください。候補が10件以上ある場合は厳選し、10件未満の場合は候補の全件を採用してください。
**重要: articlesの配列には必ず10件（候補が10件未満なら全件）を含めてください。5件や7件では不十分です。**
- テーマとの関連性（ストーリーの一貫性）
- 読者の「明日の行動」を変える力
- ソースの多様性（同じメディアに偏らない）
- 速報性（既に広く知られた情報は下位に）

## Step 3: 各記事の付加価値を追加
各記事に対して以下を日本語で追記してください：
- **one_liner**: ニュースの核心を20文字以内で表現（例: 'AI議事録が全社標準へ'）
- **why_important**: ビジネスパーソンが明日の仕事で意識すべきこと（1-2文）
- **action_item**: 読者が今日すぐできる具体的な1つの行動（例: '社内の定型業務リストを作ってみてください'）

## Step 4: 今朝の一言
読者が最初に読む「編集長コメント」を40文字以内で作成してください。
トーンは、信頼感のある落ち着いた口調で。例:「エージェント技術、ついに"使える段階"へ」

## 出力ルール（厳守）
- 出力テキストに**特定の年齢層（「40代」「30代」等）を絶対に記載しないでください**。読者層を限定する表現は不要です。
- 「ビジネスパーソン」「エンジニア」「管理職」など役割ベースの表現は許可します。

---
候補記事リスト:
{articles_text}
---

重要: JSON のみを出力してください。マークダウンのコードブロックなどは不要です。
"""

    # Gemini 構造化出力用のスキーマ定義
    curated_article_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "title_ja": types.Schema(type=types.Type.STRING, description="日本語タイトル"),
            "summary_ja": types.Schema(type=types.Type.STRING, description="日本語要約"),
            "one_liner": types.Schema(
                type=types.Type.STRING,
                description="ニュースの核心を20文字以内で（例: 'AI議事録が全社標準へ'）",
            ),
            "why_important": types.Schema(
                type=types.Type.STRING,
                description="なぜ重要か（ビジネスパーソン向け, 1-2文）",
            ),
            "action_item": types.Schema(
                type=types.Type.STRING,
                description="読者が今日すぐできる1つの行動",
            ),
            "category": types.Schema(type=types.Type.STRING, description="カテゴリ"),
            "importance_score": types.Schema(type=types.Type.INTEGER, description="重要度 1-10"),
            "source": types.Schema(type=types.Type.STRING, description="ソース名"),
            "url": types.Schema(type=types.Type.STRING, description="URL"),
        },
        required=[
            "title_ja", "summary_ja", "one_liner", "why_important",
            "action_item", "category", "importance_score", "source", "url",
        ],
    )

    response_schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "theme": types.Schema(type=types.Type.STRING, description="今日のテーマ（20文字以内）"),
            "morning_comment": types.Schema(
                type=types.Type.STRING,
                description="今朝の一言（40文字以内）",
            ),
            "articles": types.Schema(
                type=types.Type.ARRAY,
                items=curated_article_schema,
            ),
        },
        required=["theme", "morning_comment", "articles"],
    )

    print("🧠 Gemini 2次キュレーション実行中...")
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
            result = json.loads(response_text)

            curated_articles = result.get("articles", [])
            elapsed = time.time() - start
            print(f"✅ 2次キュレーション完了（{elapsed:.1f}秒）")
            print(f"   テーマ: {result.get('theme', '—')}")
            print(f"   一言: {result.get('morning_comment', '—')}")
            print(f"   Gemini 選定: {len(curated_articles)} 件")

            # ガードレール: Gemini が10件未満しか返さなかった場合、候補全体から補完する
            if len(curated_articles) < 10 and len(candidates) > len(curated_articles):
                curated_urls = {a.get("url", "") for a in curated_articles}
                remaining = [
                    a for a in candidates if a.get("url", "") not in curated_urls
                ]
                remaining.sort(
                    key=lambda x: x.get("importance_score", 0), reverse=True
                )
                needed = 10 - len(curated_articles)
                supplement = remaining[:needed]
                if supplement:
                    print(f"   📌 Gemini選定が{len(curated_articles)}件 → "
                          f"候補から{len(supplement)}件を補完して10件に調整")
                    curated_articles.extend(supplement)
                result["articles"] = curated_articles

            final_count = len(result.get('articles', []))
            if final_count < 10:
                print(f"   ⚠️ 候補不足: 最終 {final_count} 件（候補全体が{len(candidates)}件のため）")
            else:
                print(f"   ✅ 最終選定: {final_count} 件（10件保証達成）")
            return result

        except Exception as e:
            last_error = e
            print(f"   ⚠️ Attempt {attempt + 1} failed: {e}")
            # INVALID_ARGUMENT (API key issue) はリトライしても無駄
            if "INVALID_ARGUMENT" in str(e) or "API Key" in str(e):
                print("   🛑 APIキーエラーのためリトライ中止")
                break

    # 全リトライ失敗時のフォールバック
    elapsed = time.time() - start
    print(f"❌ Gemini 2次キュレーション失敗（全{max_retries + 1}回, {elapsed:.1f}秒）: {last_error}")
    # フォールバック: 1次スコア上位10件を使用（翻訳済みフィールドを優先）
    fallback_articles = sorted(
        candidates, key=lambda x: x.get("importance_score", 0), reverse=True
    )[:10]
    for a in fallback_articles:
        if a.get("title_ja"):
            a["title"] = a["title_ja"]
        if a.get("summary_ja"):
            a["summary"] = a["summary_ja"]
    return {
        "theme": "本日のAI注目ニュース",
        "morning_comment": "本日の重要ニュースをお届けします",
        "articles": fallback_articles,
        "_fallback": True,
    }


def save_morning_brief(brief):
    """Morning Brief を JSON と Markdown の両形式で保存"""
    now_jst = datetime.datetime.now(JST)
    today_str = now_jst.strftime("%Y%m%d")
    updated_str = now_jst.strftime("%Y年%m月%d日 %H:%M")

    # JSON (distribute_daily.py 互換)
    json_filename = f"morning_brief_{today_str}.json"
    json_filepath = os.path.join(NEWS_BOT_OUTPUT_DIR, json_filename)

    output_data = {
        "theme": brief.get("theme", ""),
        "morning_comment": brief.get("morning_comment", ""),
        "articles": brief.get("articles", []),
    }

    with open(json_filepath, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"✅ JSON 保存: {json_filepath}")

    # Markdown
    md_filename = f"morning_brief_{today_str}.md"
    md_filepath = os.path.join(NEWS_BOT_OUTPUT_DIR, md_filename)

    articles = brief.get("articles", [])
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write("# ☀️ Antigravity Morning Brief\n\n")
        f.write(f"**{updated_str} (JST)**\n\n")
        f.write(f"## 🎯 今日のテーマ: {brief.get('theme', '')}\n\n")
        f.write(f"> {brief.get('morning_comment', '')}\n\n")
        f.write("---\n\n")

        for i, a in enumerate(articles, 1):
            title = a.get("title_ja", "No Title")
            summary = a.get("summary_ja", "")
            one_liner = a.get("one_liner", "")
            why = a.get("why_important", "")
            action = a.get("action_item", "")
            source = a.get("source", "Unknown")
            url = a.get("url", "")
            category = a.get("category", "未分類")

            f.write(f"## {i}. {title}\n\n")
            f.write(f"**カテゴリ**: {category}\n\n")
            if one_liner:
                f.write(f"💡 **一言**: {one_liner}\n\n")
            f.write(f"{summary}\n\n")
            if why:
                f.write(f"📌 **なぜ重要？** {why}\n\n")
            if action:
                f.write(f"👉 **アクション**: {action}\n\n")
            f.write(f"- **出典**: {source}\n")
            f.write(f"- **URL**: {url}\n\n")

    print(f"✅ Markdown 保存: {md_filepath}")

    return json_filepath


def main():
    pipeline_start = time.time()
    print("=" * 50)
    print("☀️ Morning Brief — Stage 2 キュレーション開始")
    print("=" * 50)

    # 1. Stage 1 候補を読み込み
    print("\n📡 Stage 1 候補を読み込み中...")
    candidates_stage1 = load_candidates()
    stage1_count = len(candidates_stage1)

    # 2. 新鮮なRSS収集（03:00〜07:00 JST のギャップを埋める）
    print("\n📡 最新RSS収集中（03:00以降の新着をキャッチ）...")
    try:
        import collect_rss_gemini
        collect_rss_gemini.main()
    except Exception as e:
        print(f"  ⚠️ 追加RSS収集失敗（Stage 1 候補で続行）: {e}")

    # 3. Stage 1 + 新規を統合して再読み込み
    print("\n📡 全候補を統合中...")
    candidates = load_candidates()

    if not candidates:
        print("❌ 候補が見つかりません。終了します。")
        return

    new_count = len(candidates) - stage1_count
    print(f"   Stage 1 からの候補: {stage1_count} 件")
    print(f"   07:00 追加収集分: {max(0, new_count)} 件")
    print(f"   合計候補: {len(candidates)} 件")

    # 3.5. 過去3日間の配信済みURLを除外
    print("\n🔒 過去3日間の重複チェック中...")
    delivered_urls = get_delivered_urls(days=3)
    if delivered_urls:
        before = len(candidates)
        candidates = [a for a in candidates if a.get("url", "") not in delivered_urls]
        removed = before - len(candidates)
        if removed > 0:
            print(f"   ✂️ 過去に配信済みの {removed} 件を除外 → 残り {len(candidates)} 件")
        else:
            print(f"   ✅ 重複なし（全 {len(candidates)} 件が新規）")

    # 4. Gemini 2次キュレーション
    print("\n🧠 2次キュレーション実行中...")
    brief = curate_with_gemini(candidates)

    if not brief:
        print("❌ キュレーション失敗。終了します。")
        return

    # 4.5. Gemini 完全失敗時の警告
    is_degraded = brief.get("_fallback", False)
    if is_degraded:
        print("\n🚨 WARNING: Gemini API 呼び出しが全て失敗しました。")
        print("   フォールバックデータで配信を続行しますが、品質が低下しています。")
        print("   → GitHub Secrets の GOOGLE_API_KEY を確認してください。")

    # 5. 保存
    print("\n💾 Morning Brief を保存中...")
    save_morning_brief(brief)

    # 6. 配信（失敗してもサイト更新は継続）
    print("\n📤 配信開始...")
    try:
        import distribute_daily
        distribute_daily.main()
    except Exception as e:
        print(f"  ⚠️ 配信エラー（サイト更新は続行）: {e}")

    # 7. サイト更新（配信の成否に関わらず実行）
    print("\n🌐 GitHub Pages 更新中...")
    try:
        import build_pages
        build_pages.build_pages()
    except Exception as e:
        print(f"  ⚠️ サイト更新エラー: {e}")

    # 8. ヘルスチェック — フォールバック発動時にLINE障害通知 + exit(1)
    if is_degraded:
        print("\n🚨 ヘルスチェック: 品質低下を検知")
        try:
            from line_notifier import send_to_line
            alert_msg = (
                "🚨 AI News Bot 障害通知\n"
                "─────────\n\n"
                "Gemini API の呼び出しが全て失敗しました。\n"
                "フォールバックデータ（品質低下）で配信しています。\n\n"
                "📌 対処: GitHub Secrets の GOOGLE_API_KEY を確認してください。\n"
                "🔗 https://github.com/TadFuji/ai-news-bot/settings/secrets/actions"
            )
            send_to_line(alert_msg)
            print("  📱 LINE 障害通知を送信しました")
        except Exception as e:
            print(f"  ⚠️ LINE 障害通知の送信失敗: {e}")

        pipeline_elapsed = time.time() - pipeline_start
        print(f"\n{'=' * 50}")
        print(f"⚠️ Morning Brief 配信完了（品質低下モード）— 合計 {pipeline_elapsed:.1f}秒")
        print("=" * 50)
        sys.exit(1)

    pipeline_elapsed = time.time() - pipeline_start
    print(f"\n{'=' * 50}")
    print(f"✅ Morning Brief 配信完了！ — 合計 {pipeline_elapsed:.1f}秒")
    print("=" * 50)


if __name__ == "__main__":
    main()
