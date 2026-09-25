"""dedup.py — 見出しの類似度で「同じ出来事」のニュースを束ねる。

curate_morning_brief.py の URL 重複排除は完全一致のみで、同じ出来事を別メディアが
報じた記事は別物として残り、Top10 の枠を食い合う。本モジュールは翻訳済み見出し
（title_ja）の類似度で意味的な重複を束ね、各グループからスコア最高の1本を残す。

日本語の翻訳見出しは語順・助詞・体言止めが揺れるため、文字単位の比較だけでは
取りこぼしやすい。そこで「単語の重なり（Jaccard 係数）」を主指標、difflib の
SequenceMatcher を境界帯の救済に使う二段構えにしている。

依存は標準ライブラリ＋既存の python-dateutil のみ（追加依存なし）。
"""

import re
import datetime
import unicodedata
from difflib import SequenceMatcher

from dateutil import parser as date_parser

# 見出し正規化で除去する記号・約物（日本語の括弧・引用符・ダッシュ・中黒等を含む）
_PUNCT = re.compile(r"[\s　、。，．・「」『』（）()\[\]【】“”\"'’‘:：;；!！?？\-—–~〜/|]+")

_MIN_TOKENS = 2        # 正規化後トークンがこれ未満の見出しは束ねず素通り（短すぎ）
# 閾値は実測で確定（現実的なAIニュース見出しで計測）:
#   同一出来事ペアの Jaccard 最小 ≈ 0.29、別出来事ペアの最大 ≈ 0.09。
#   「同じ企業の別ニュース」(例: OpenAI資金調達 vs OpenAI新モデル) でも 0.06。
#   誤マージ（別ニュースを消す）を最優先で避けるため、谷の中で安全側に 0.25 を採用。
_JACCARD_MAIN = 0.25   # 主判定: トークン Jaccard がこの値以上なら同一とみなす
_JACCARD_BORDER = 0.18  # 境界帯の下限（ここ〜MAIN の間のみ SM 救済を許す）
_SM_RESCUE = 0.78      # 境界帯で SequenceMatcher 比率がこの値以上なら救済


def _title_of(article: dict) -> str:
    return (article.get("title_ja") or article.get("title") or "").strip()


def _normalize(text: str) -> str:
    """NFKC 正規化 → 小文字化 → 記号除去 → 空白正規化。"""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = _PUNCT.sub(" ", text)
    return text.strip()


def _tokens(norm: str) -> set[str]:
    """英数字は単語単位、日本語は文字 bigram でトークン集合を作る。

    日本語は分かち書きがないため、形態素解析器（追加依存）を避け、
    文字 2-gram で語順に依存しない近似トークン化を行う。
    """
    if not norm:
        return set()
    tokens: set[str] = set()
    # 英数字の連続を1語として扱う（固有名詞・モデル名の一致を捉える）
    for word in re.findall(r"[a-z0-9]+", norm):
        tokens.add(word)
    # 英数字・空白以外（主に日本語）の連続を bigram 化
    for chunk in re.findall(r"[^a-z0-9\s]+", norm):
        if len(chunk) == 1:
            tokens.add(chunk)
        else:
            for i in range(len(chunk) - 1):
                tokens.add(chunk[i:i + 2])
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _numbers(norm: str) -> set[str]:
    """見出し中の数値（モデル番号・バージョン・年・金額など）を抽出する。

    AI ニュースは「GPT-5 と GPT-4」「Gemini 1.5 と 2.0」のようにモデル番号だけが
    異なる別発表が共存しやすい。数値は強い識別子として扱い、両見出しが数値を持ち
    かつ食い違う場合は別の出来事とみなす（誤マージ防止）。
    """
    return set(re.findall(r"\d+", norm))


def _is_similar(item_a: tuple, item_b: tuple, jaccard_main: float) -> bool:
    """2件の見出しが「同じ出来事」かを判定する。item = (idx, article, norm, tokens, numbers)。"""
    _, _, norm_a, tok_a, num_a = item_a
    _, _, norm_b, tok_b, num_b = item_b
    # モデル番号・バージョン・年・金額などの数値が両方にあり食い違うなら別ニュース
    if num_a and num_b and num_a != num_b:
        return False
    j = _jaccard(tok_a, tok_b)
    if j >= jaccard_main:
        return True
    # 境界帯のみ、語順入れ替え・言い回し差を SequenceMatcher で救済
    if j >= _JACCARD_BORDER:
        return SequenceMatcher(None, norm_a, norm_b).ratio() >= _SM_RESCUE
    return False


def _published_key(article: dict) -> datetime.datetime:
    """published を aware datetime に変換。欠損・解析失敗は最弱（min, UTC）。"""
    pub = article.get("published")
    if isinstance(pub, datetime.datetime):
        return pub if pub.tzinfo else pub.replace(tzinfo=datetime.timezone.utc)
    if isinstance(pub, str) and pub:
        try:
            dt = date_parser.parse(pub)
            return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)
        except Exception:
            pass
    return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)


def _representative(members: list[tuple[int, dict]]) -> tuple[int, dict]:
    """クラスタ代表を選ぶ: importance_score 降順 → published 新しい順 → 出現順。

    既存コード（collect_rss_gemini.py / ai_client.py）の「published 欠損は
    datetime.min で最弱扱い」という規約に合わせる。
    """
    return max(
        members,
        key=lambda m: (
            m[1].get("importance_score", 0) or 0,
            _published_key(m[1]),
            -m[0],   # 同点なら元の出現が早い方（idx 小）を優先
        ),
    )


def dedup_articles(articles: list[dict], threshold: float = _JACCARD_MAIN) -> list[dict]:
    """意味的に同じ出来事の記事を束ね、各グループ代表のみ残す（greedy）。

    Args:
        articles: 記事 dict のリスト（title_ja / importance_score / published 等を含む）
        threshold: トークン Jaccard の主判定閾値（大きいほど束ねにくい）

    Returns:
        重複を束ねた記事リスト（元の出現順を維持）
    """
    if len(articles) <= 1:
        return articles

    # 短すぎ・空の見出しは束ねず素通りさせ、誤クラスタ化を防ぐ
    passthrough: list[tuple[int, dict]] = []
    candidates: list[tuple] = []  # (idx, article, norm, tokens, numbers)
    for idx, article in enumerate(articles):
        norm = _normalize(_title_of(article))
        tokens = _tokens(norm)
        if len(tokens) < _MIN_TOKENS:
            passthrough.append((idx, article))
        else:
            candidates.append((idx, article, norm, tokens, _numbers(norm)))

    # complete-linkage クラスタリング: クラスタの「全メンバー」と類似する場合のみ合流する。
    # 単連結（代表とだけ比較）だと A≈B・B≈C だが A≠C のとき A と C が同居して
    # 別ニュースを誤って束ねる（入力順依存の非決定的な取りこぼし）。全メンバー一致を
    # 条件にすることで、非類似ペアが決して同居しないようにする。
    clusters: list[list[tuple]] = []
    for item in candidates:
        placed = False
        for cluster in clusters:
            if all(_is_similar(item, member, threshold) for member in cluster):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])

    # 代表＋素通り分を集め、元の出現順に並べ直す
    kept: list[tuple[int, dict]] = list(passthrough)
    for cluster in clusters:
        members = [(item[0], item[1]) for item in cluster]
        kept.append(_representative(members))
    kept.sort(key=lambda m: m[0])
    result = [article for _, article in kept]

    removed = len(articles) - len(result)
    if removed > 0:
        print(f"  🔗 重複束ね: {len(articles)} 件 → {len(result)} 件（{removed} 件を集約）")
    return result
