# 🍎 MacBook Pro セットアップガイド

このドキュメントは、`ai-news-bot` プロジェクトを外出先（MacBook Pro）で快適に運用・開発するための初期設定手順書です。このファイルを GitHub 経由で同期することで、どの PC からでも手順を確認できます。

---

## 🚀 1. 準備：リポジトリの取得

Mac の「ターミナル (Terminal)」を開き、以下のコマンドを順番に実行して、クラウド（GitHub）から最新のコードを手元にコピーします。

```bash
# デスクトップに移動（場所はお好みで変更してください）
cd ~/Desktop

# リポジトリをクローン（複製）
git clone https://github.com/TadFuji/ai-news-bot.git

# プロジェクトのフォルダに入る
cd ai-news-bot
```

## ⚙️ 2. 環境構築：Python 仮想環境の作成

Windows と Mac では Python の動く仕組みが微妙に異なるため、Mac 専用の「作業部屋（仮想環境）」を新しく作ります。

```bash
# Mac専用の仮想環境 (.venv) を作成
python3 -m venv .venv

# 仮想環境を有効化（これからこの部屋で作業するという宣言）
source .venv/bin/activate

# 必要なライブラリを一括インストール
pip install -r requirements.txt
```

> **🔑 ポイント**: 
> これ以降、Mac で作業を再開する際は、必ずフォルダ移動後に `source .venv/bin/activate` を実行してください。

## 🔐 3. 秘密鍵：.env ファイルの作成

セキュリティ上の理由から、APIキーなどの機密情報は GitHub には保存されていません。Windows 側のプロジェクトにある `.env` ファイルの内容をコピーする必要があります。

1. **Windows側**: `ai-news-bot/.env` ファイルをメモ帳などで開きます。
2. **Mac側**: `ai-news-bot/` フォルダの中に、新しく `.env` という名前のファイルを作ります。
3. **内容をコピー**: Windows 側の内容をそのまま Mac 側のファイルに貼り付けて保存します。

## 🔄 4. 日常の同期ワークフロー

作業の「先祖返り」や「衝突（コンフリクト）」を防ぐための合言葉です。

### 🍎 外出先 (Mac) で作業を始めるとき
```bash
git pull
```
※自動ボットなどが更新した最新のレポートを取り込みます。

### 🍎 外出先 (Mac) での作業を終えるとき
```bash
git add .
git commit -m "Macでの作業完了：[ここに内容を記載]"
git push
```
※修正内容をクラウドに送り、自宅の Windows で受け取れる状態にします。

---

## 🛠️ 困ったときは

Antigravity にこう話しかけてください：
- 「Macでのセットアップがうまくいかないので、エラーを見て助けて」
- 「Windowsとの同期でコンフリクトが起きたから解決して」

---
*Last Updated: 2026-01-26*
