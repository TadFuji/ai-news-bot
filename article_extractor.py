"""article_extractor.py — 記事URLから本文を取得する（trafilatura）。

RSS の冒頭要約だけでは AI の判断材料が薄いため、上位候補の記事本文を取得して
1次分析（ai_client.process_with_gemini）へ渡す。本文は AI への入力専用とし、
出力JSONには残さない（呼び出し側で copy 後に pop する想定）。

重要（CRITICAL）:
    trafilatura.extract() は抽出のタイムアウトを SIGALRM シグナルで実装している。
    ThreadPoolExecutor のワーカースレッド内で呼ぶと
    ``ValueError: signal only works in main thread`` で必ず失敗する。
    そのため EXTRACTION_TIMEOUT=0 でシグナルを無効化することが必須。
    （並列取得そのもの = fetch_url はシグナルを使わないため影響を受けない）
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import trafilatura
from trafilatura.settings import use_config

# 既存 rss_client.py の並列度に合わせる
_MAX_WORKERS = 8
_DOWNLOAD_TIMEOUT_SEC = 15
_BODY_MAX_CHARS = 6000    # Gemini トークン節約のための本文上限
_MIN_BODY_CHARS = 200     # これ未満の抽出は失敗扱い（呼び出し側で要約へフォールバック）

# モジュールレベルで config を1度だけ構築する。
# EXTRACTION_TIMEOUT=0 でシグナル（SIGALRM）を無効化し、スレッド内 extract() を安全にする。
_CONFIG = use_config()
_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "0")
_CONFIG.set("DEFAULT", "DOWNLOAD_TIMEOUT", str(_DOWNLOAD_TIMEOUT_SEC))
_CONFIG.set("DEFAULT", "MIN_EXTRACTED_SIZE", str(_MIN_BODY_CHARS))


def fetch_article_text(url: str) -> str | None:
    """単一 URL から本文を抽出する。取得・抽出に失敗したら None を返す。

    呼び出し側は None のとき RSS 要約へフォールバックする想定。

    Returns:
        本文文字列（最大 _BODY_MAX_CHARS）/ 取得・抽出失敗時は None
    """
    if not url:
        return None
    try:
        # fetch_url は 403・UAブロック・タイムアウト時に None を返す
        downloaded = trafilatura.fetch_url(url, config=_CONFIG)
        if not downloaded:
            return None
        text = trafilatura.extract(
            downloaded,
            config=_CONFIG,           # EXTRACTION_TIMEOUT=0（スレッド安全）
            favor_precision=True,     # ナビ・広告・関連リンクの混入を抑える
            include_comments=False,
            include_tables=False,
        )
        if not text or len(text) < _MIN_BODY_CHARS:
            return None
        return text[:_BODY_MAX_CHARS]
    except Exception:
        # 1 件の失敗が全体を止めないよう握りつぶす（呼び出し側で要約へフォールバック）
        return None


def enrich_with_full_text(articles: list[dict], top_n: int = 15) -> list[dict]:
    """上位 top_n 件のうち本文未取得の記事だけ、本文を並列取得して付与する。

    各記事 dict に ``full_text`` キーを **追加** する（既存キーは一切変更しない）。
    冪等: 既に full_text を持つ記事は再取得しない（同一プロセス内の二重取得を回避）。
    本文取得に失敗した記事には full_text を付けない（呼び出し側で要約を使う）。

    Returns:
        articles（in-place で更新済みの同一リスト）
    """
    targets = [
        a for a in articles[:top_n]
        if not a.get("full_text") and a.get("url")
    ]
    if not targets:
        return articles

    start = time.time()
    print(f"📄 上位 {len(targets)} 件の本文を並列取得中（最大{_MAX_WORKERS}スレッド）...")

    success = 0
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_article = {
            executor.submit(fetch_article_text, a["url"]): a for a in targets
        }
        for future in as_completed(future_to_article):
            article = future_to_article[future]
            try:
                # 遅いサイトの足切りは fetch_url の DOWNLOAD_TIMEOUT が担う。
                # as_completed が返す future は完了済みのため、ここの timeout は
                # （実質的な足切りではなく）完了済み future への安全弁。
                body = future.result(timeout=_DOWNLOAD_TIMEOUT_SEC + 5)
            except Exception as e:
                print(f"  ⚠️ 本文取得失敗 [{article.get('source', '?')}]: {e}")
                body = None
            if body:
                article["full_text"] = body
                success += 1

    elapsed = time.time() - start
    print(
        f"✅ 本文取得: {success}/{len(targets)} 件成功"
        f"（残りは要約で代替, {elapsed:.1f}秒）"
    )
    return articles
