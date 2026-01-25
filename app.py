import streamlit as st
import json
import glob
import os
import sys
import time
from datetime import datetime
import subprocess
from dotenv import load_dotenv

from config import PROJECT_ROOT as BOT_DIR, NEWS_BOT_OUTPUT_DIR

# Add bot directory to path
if BOT_DIR not in sys.path:
    sys.path.append(BOT_DIR)

# Attempt Imports of Automation Modules
IMPORT_ERROR_MSG = None
try:
    from drivers.x_poster import post_to_x
    from generators.video_maker import create_video
    # generate_pdf is imported inside the function to avoid browser launch on startup
    MODULES_LOADED = True
except ImportError as e:
    # Capture the specific error for debugging
    IMPORT_ERROR_MSG = str(e)
    print(f"Module Import Warning: {e}")
    MODULES_LOADED = False
except Exception as e:
    # Capture other possible errors during import (e.g., missing dlls)
    IMPORT_ERROR_MSG = str(e)
    print(f"Module Unexpected Warning: {e}")
    MODULES_LOADED = False

# Page Config
st.set_page_config(
    page_title="Antigravity Marketing Engine",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 Antigravity Marketing Engine")
st.markdown("### 24時間AIニュース「大拡散」コマンドセンター")

if not MODULES_LOADED:
    st.warning("⚠️ Automation modules not found. 'drivers' and 'generators' folders must be in the bot directory.")
    if IMPORT_ERROR_MSG:
        st.error(f"🔍 Debug Info: {IMPORT_ERROR_MSG}")
        st.caption("Please install missing dependencies via `pip install -r requirements.txt` or check paths.")

@st.cache_data(ttl=60)
def load_latest_news():
    json_files = glob.glob(os.path.join(NEWS_BOT_OUTPUT_DIR, "*.json"))
    # Filter out system files
    json_files = [f for f in json_files if "check_history.json" not in f]
    
    if not json_files:
        return None, None
    latest_file = max(json_files, key=os.path.getmtime)
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Ensure data is a list of articles
    if not isinstance(data, list):
        return latest_file, []
        
    return latest_file, data

# Sidebar
with st.sidebar:
    # --- Sidebar ---
    debug_attach = False
    with st.expander("🔧 Advanced Settings"):
         debug_attach = st.checkbox("既存のChromeに接続 (Port 9222)", value=False, help="START_USER_CHROME.batで起動したChromeを操作する場合にチェックを入れてください。")
         
         if st.button("🔄 データを再読み込み (Cache Clear)"):
             st.cache_data.clear()
             st.rerun()
         
    # ... (existing manual update code) ...
    
    # ... (inside tabs) ...
    

        
    st.markdown("---")
    st.write("▼ ニュースを新しく取得")
    with st.expander("⚙️ オプション設定", expanded=True):
        sync_github = st.checkbox("GitHub Pagesにも反映する (Cloud Sync)", value=True, help="チェックを入れると、Webサイト(GitHub Pages)も最新ニュースに更新されます。")
        line_notify = st.checkbox("LINE通知も送信する (Push Notification)", value=False, help="チェックを入れると、更新完了時にLINEに通知が飛びます。通常はオフでOKです。")

    if st.button("⚡ 手動更新 (Web巡回を開始)"):
        with st.spinner("🤖 世界中のニュースを巡回中... (3-5分かかります)"):
            try:
                # 1. News Collection (main.py)
                cmd = [sys.executable, "main.py", "--mode", "daily"]
                if not line_notify:
                    cmd.append("--no-line")
                
                # Windows Console Encoding Fix
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                
                result = subprocess.run(
                    cmd,
                    cwd=BOT_DIR,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=env
                )
                
                if result.returncode != 0:
                    st.error("❌ ニュース収集エラー")
                    st.code(f"{result.stderr}\n{result.stdout}")
                    st.stop()
                
                log_output = f"✅ ニュース収集完了\n"
                
                # 2. Site Generation & Git Sync
                if sync_github:
                    with st.spinner("🌍 GitHub Pagesを更新中..."):
                        # Build Pages
                        build_cmd = [sys.executable, "build_pages.py"]
                        build_res = subprocess.run(
                            build_cmd,
                            cwd=BOT_DIR,
                            capture_output=True,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            env=env
                        )
                        
                        if build_res.returncode != 0:
                            st.warning("⚠️ サイト生成に失敗しました")
                            st.code(build_res.stderr)
                        else:
                            log_output += "✅ サイトデータ生成完了\n"
                            
                            # Git Commands
                            # using 'git' directly assumes it's in PATH (Git Bash or minimal git installed)
                            # 1. Add changes (docs folder specifically for site)
                            subprocess.run(["git", "add", "docs/"], cwd=BOT_DIR, capture_output=True)
                            subprocess.run(["git", "add", "public_reports/"], cwd=BOT_DIR, capture_output=True) # Sync reports too
                            
                            # 2. Commit
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
                            commit_msg = f"Manual Update: {timestamp} (via Cockpit)"
                            subprocess.run(["git", "commit", "-m", commit_msg], cwd=BOT_DIR, capture_output=True)
                            
                            # 3. Push
                            push_res = subprocess.run(["git", "push", "origin", "main"], cwd=BOT_DIR, capture_output=True)
                            
                            if push_res.returncode == 0:
                                log_output += "✅ GitHub Sync完了 (Webサイト更新)\n"
                            else:
                                log_output += f"⚠️ GitHub Push失敗 (認証エラー等の可能性): {push_res.stderr}\n"

                st.success(log_output)
                st.cache_data.clear()
                time.sleep(3)
                st.rerun()

            except Exception as e:
                st.error(f"実行エラー: {e}")
    
    st.markdown("---")
    st.markdown("---")
    st.caption("トラブルシューティング")
    
    with st.expander("🔑 ログインできない場合 (最終手段)"):
        st.info("""
        **ブラウザのセキュリティが強すぎてログインできない場合**
        
        1. デスクトップに作成された `START_USER_CHROME.bat` を実行してください。
        2. あなたの「いつものChrome」が起動します。
        3. その状態で「🔴 AUTO-POST」ボタンを押してください。
        
        ※ ロボットがあなたのChromeに接続して操作を行います。
        """)

    if st.button("🛑 ブラウザを強制リセット"):
         import subprocess
         try:
             # Force kill chromeMain and driver to unlock profile
             subprocess.run("taskkill /F /IM chrome.exe /T", shell=True)
             subprocess.run("taskkill /F /IM chromedriver.exe /T", shell=True)
             st.success("✅ ブラウザを強制終了しました。もう一度AUTO-POSTを試してください。")
         except Exception as e:
             st.error(f"Error: {e}")

    st.markdown("---")
    st.caption(f"監視フォルダ:\n{NEWS_BOT_OUTPUT_DIR}")

# --- Helper Functions ---

def generate_x_posts(articles):
    date_str = datetime.now().strftime("%m/%d")
    
    # List all 10 items with summaries
    news_content = ""
    for i, a in enumerate(articles[:10], 1):
        # Format: Number. Title / Summary
        news_content += f"{i}. {a['title_ja']}\n"
        news_content += f"▶︎ {a['summary_ja']}\n\n" # Removed character limit to match web content

    # URL for reply
    registration_url = "https://lin.ee/gTGnitS"
    reply_text = f"""
【完全無料で配信中】
毎朝7時に、今日のような厳選ニュースがLINEに届きます。
情報収集の時間を効率化し、AIを味方につけましょう。

▼ 友達追加はこちら（1秒で完了）
{registration_url}
    """.strip()

    post_content = f"""
【AIニュース 10選 ({date_str})】
今日読むべき重要情報を網羅しました。トレンドの最前線をこの1ポストで把握できます。

{news_content.strip()}

---
「情報の波に溺れず、賢く波に乗る」
こうした最新情報を、毎朝午前7時に「3行要約」でお届けしています。
忙しいビジネスパーソンのインプットに最適です。

完全無料で配信中。詳細はリプライを見てください！👇

#AI #TechNews #業務効率化
    """.strip()

    return {
        "Professional": post_content, 
        "ReplyURL": reply_text
    }

def generate_note_draft(articles):
    date_str = datetime.now().strftime("%Y年%m月%d日")
    md = f"""# 【{date_str}】今日のAIニュースまとめ：{articles[0]['title_ja']} 他

おはようございます！
Antigravity AI News Botが選んだ、今日の「読むべき10本」をお届けします。

## 💡 今日のハイライト
**第1位：{articles[0]['title_ja']}**
{articles[0]['summary_ja']}

このニュースは、今後のAI業界に大きな影響を与えそうです。

---

## 🚀 ランキング TOP10

"""
    for i, article in enumerate(articles, 1):
        md += f"### {i}. {article['title_ja']}\n"
        md += f"{article['summary_ja']}\n\n"
    
    md += """
---

## 毎朝、LINEで受け取りたい方へ
これらのニュースを、毎朝7時にLINEで自動配信しています。
「情報収集を自動化したい」という方は、ぜひ友達追加してください。完全無料です。

👉 **[LINEでニュースを受け取る（無料）](https://lin.ee/gTGnitS)**

情報の波に溺れず、賢く波に乗りましょう🏄‍♂️
"""
    return md

def generate_video_script(articles):
    top = articles[0]
    script = f"""
# 📺 30秒解説動画台本 (TikTok / YouTube Shorts)

【設定】
- テンポ: 超高速
- BGM: サイバーパンク系 or アップテンポ
- 冒頭1秒で文字デカ出し: 「{top['title_ja'][:15]}...」

---

**0:00 - 0:02 (Hook)**
(画面: ニュースのタイトル画像をドアップ)
「速報！これ知らないとマズい」
「{top['title_ja'][:20]} が起きました！」

**0:02 - 0:15 (Body)**
(画面: 箇条書き要約を高速スクロール)
「要点は3つ！」
1. {top['summary_ja'][:30]}...
2. これによりX業界が激変します
3. 明日から使える知識です

**0:15 - 0:25 (Insight)**
(画面: あなたの顔 or AIアバター)
「正直、ここまで進化するとは思ってなかった...」
「乗り遅れたくない人は、今すぐチェックして！」

**0:25 - 0:30 (CTA)**
(画面: 巨大な矢印とLINEアイコン)
「詳しい解説はプロフのLINEから！」
「毎朝7時に重要ニュースだけ届くよ！」
(SE: 登録音)

---
"""
    return script

def generate_reply_text(articles):
    top = articles[0]
    return {
        "Agreement": f"まさに仰る通りです！\\nちなみに今日の「{top['title_ja']}」でも、同様の傾向が見られましたね。\\n情報の陳腐化が早すぎて、追うのが大変ですが、この流れは止まらなそうです。",
        "Insight": f"これ、視点が鋭いですね。\\n実は直近の「{top['title_ja']}」にも関連する話で、今後はXXの分野が伸びていく予感がします。\\n毎日AIニュースを追っていますが、この変化は特筆すべきです。",
        "Question": f"非常に勉強になります！\\n一方で、「{top['title_ja']}」のような動きについてはどうお考えですか？\\n個人的には、今後ますますXXが重要になると感じています！"
    }

def generate_press_release(articles):
    date_str = datetime.now().strftime("%Y年%m月%d日")
    pr = f"""
# 📰 プレスリリース原稿 (PR Times / TechCrunch用)

**タイトル:**
個人開発AIボットが「ニュース収集」の常識を変える —— Gemini 3.0搭載「Antigravity News」がLINE登録者数急増中

**サブタイトル:**
「情報収集にかける時間をゼロに」。24時間体制で世界中のテックニュースを監視・要約する完全自動化システムを無料公開。

---

**【{date_str} 東京】**
個人開発者の[あなたのお名前]は本日、世界中のAIニュースをリアルタイムで収集・要約し、LINEで配信するサービス「Antigravity AI News」の本格運用を開始しました。

**■ 背景**
AI技術の進化スピードは凄まじく、毎日数百本のニュースが生まれています。「情報のキャッチアップが追いたない」というエンジニア・ビジネスマンの課題を解決するため、Googleの最新AIモデル「Gemini 3.0 Flash (Preview)」を活用した完全自動化システムを開発しました。

**■ サービスの特徴**
1. **完全自動運転**: RSS収集から翻訳、要約、配信までをPythonプログラムが全自動で実行。
2. **超速報体制**: 「センチネル・モード」により、1時間ごとにインターネットを巡回。重要なニュースを即座に検知します。
3. **今日の実例**: 本日配信された「{articles[0]['title_ja']}」のような重要ニュースも、いち早くユーザーにお届けしました。

**■ 今後の展望**
現在、登録者数は順調に推移しており、年内に1万人の利用を目指しています。「AIがAIのニュースを人間に教える」という新しい情報流通の形を提案していきます。

**■ サービスURL**
https://lin.ee/gTGnitS (LINE公式アカウント)

**■ 本件に関するお問い合わせ**
[あなたの連絡先/Xアカウント]

---
"""
    return pr

# --- Main UI ---

latest_file, articles = load_latest_news()

if not articles:
    st.error(f"ニュースデータが見つかりません。")
    if st.button("今すぐデータを生成する (Run main.py)"):
        os.system(f'python "{os.path.join(BOT_DIR, "main.py")}" --no-line')
        st.rerun()

else:
    st.success(f"✅ 最新データを読み込みました")
    
    # 7 Tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📢 X (Twitter)", 
        "📝 Note", 
        "📺 Video (New)", 
        "⚡ Reply (New)",
        "📰 PR (New)",
        "🖼️ OGP (Beta)",
        "🎁 Giveaway (New)"
    ])
    
    with tab1:
        st.header("X (Twitter) Post Generator")
        st.caption("⚠️ アルゴリズム対策: URLは「リプライ」にぶら下げます (Auto-Thread機能)")
        posts = generate_x_posts(articles)
        reply_url = posts["ReplyURL"]
        
        st.subheader("👔 Professional List (10 News Items)")
        st.text_area("X Post Content (Copy or Auto-Post):", value=posts["Professional"], height=400)
        
        if st.button("🔴 AUTO-POST (Thread)", key="auto_a"):
            with st.spinner("🤖 Taking control of browser..."):
                try:
                    post_to_x(posts["Professional"], reply_text=reply_url, force_attach=debug_attach)
                    st.success("✅ Posted thread successfully!")
                except Exception as e:
                    st.error(f"Failed: {e}")
                    with st.expander("詳細エラーログ (Traceback)"):
                        st.code(traceback.format_exc())
        
        st.markdown("---")
        st.subheader("🔗 Managed Reply (Algorithm Strategy)")
        st.text_area("Thread Reply Content:", value=reply_url, height=150)
            
    with tab2:
        st.header("Note Article Generator")
        note_draft = generate_note_draft(articles)
        st.text_area("Markdown Draft", value=note_draft, height=600)
    
    with tab3:
        st.header("📺 TikTok / Shorts Video Generator (Project Hollywood)")
        st.caption("AI音声 + 字幕で MP4動画を完全自動生成します。")
        video_script = generate_video_script(articles)
        st.text_area("Script Preview", value=video_script, height=200)
        
        if st.button("🎥 Render Video (MP4生成)", key="render_video"):
             with st.spinner("🎬 Lights, Camera, Action! (Rendering video...)"):
                try:
                    top_a = articles[0]
                    output_path = f"output_video_{datetime.now().strftime('%H%M%S')}.mp4"
                    full_output_path = os.path.join(NEWS_BOT_OUTPUT_DIR, output_path)
                    
                    result = create_video(top_a['title_ja'], top_a['summary_ja'], full_output_path)
                    if result:
                        st.success(f"✅ Video Rendered: {result}")
                        st.video(result)
                    else:
                        st.error("❌ Rendering failed.")
                except Exception as e:
                     st.error(f"Render Error: {e}")
        
    with tab4:
        st.header("⚡ Influencer Reply Generator (Newsjacking)")
        st.caption("有名人のAI関連ツイートにぶら下げるための「賢いリプライ」です。")
        replies = generate_reply_text(articles)
        
        r_col1, r_col2, r_col3 = st.columns(3)
        with r_col1:
            st.subheader("🤝 共感・同意")
            st.text_area("Agreement", value=replies["Agreement"], height=200)
        with r_col2:
            st.subheader("💡 補足・考察")
            st.text_area("Insight", value=replies["Insight"], height=200)
        with r_col3:
            st.subheader("🙋‍♂️ 質問・議論")
            st.text_area("Question", value=replies["Question"], height=200)

    with tab5:
        st.header("📰 PR Times Press Release")
        st.caption("メディア掲載を狙うための、プロ仕様プレスリリース原稿です。")
        pr_draft = generate_press_release(articles)
        st.text_area("Press Release Draft", value=pr_draft, height=600)

    with tab6:
        st.header("OGP Image Generator")
        st.info("この機能は現在開発中です。GeminiのImagen 3を使って、その日のトップニュースに合わせたアイキャッチ画像を生成する予定です。")
        st.image("https://placehold.co/600x400?text=Antigravity+OGP+Generator", caption="Future OGP Image")

    with tab7:
        st.header("🎁 Giveaway Generator (Tactical Weapon)")
        st.caption("「ニュース」ではなく「特典（PDFレポート）」を配ってリストを取ります。")
        
        col_pdf, col_promo = st.columns([1, 2])
        
        with col_pdf:
             st.subheader("Step 1: Create PDF")
             if st.button("📄 Generate PDF Report", key="gen_pdf"):
                 with st.spinner("Rendering PDF... (No Browser Required)"):
                     try:
                         # 1. Generate PDF
                         from generators.pdf_maker import create_pdf_report
                         pdf_filename = f"report_{datetime.now().strftime('%Y%m%d')}.pdf"
                         pdf_path = create_pdf_report(articles, os.path.join(NEWS_BOT_OUTPUT_DIR, pdf_filename))
                         
                         # 2. Auto-Deploy to Public Drive Folder
                         if pdf_path:
                             import shutil
                             public_dir = os.path.join(BOT_DIR, "public_reports")
                             if not os.path.exists(public_dir):
                                 os.makedirs(public_dir)
                             
                             public_path = os.path.join(public_dir, pdf_filename)
                             shutil.copy2(pdf_path, public_path)
                             
                             # 3. Create "Latest" Copy (For fixed link)
                             # Overwrite this file so the sharing link never changes, but content updates
                             latest_pdf_path = os.path.join(public_dir, "Antigravity_Latest_Report.pdf")
                             shutil.copy2(pdf_path, latest_pdf_path)
                             
                             st.success(f"✅ Generated & Deployed: {pdf_filename}")
                             st.info(f"📂 Saved to Public Drive: {public_path}")
                             st.success(f"🔗 Fixed Link Updated: Antigravity_Latest_Report.pdf")
                             st.caption("💡 User Strategy: Share the link to 'Antigravity_Latest_Report.pdf'. It always updates to the newest content!")
                         else:
                             st.error("Failed to generate PDF.")
                     except Exception as e:
                         st.error(f"Error: {e}")
        
        with col_promo:
            st.subheader("Step 2: Promo Tweet")
            
            top_a = articles[0]
            promo_text = f"""
【無料配布】
今週のAIトレンドをまとめた「Antigravity Weekly Report ({datetime.now().strftime('%m/%d')}号)」が完成しました。

TOPIC:
・{top_a['title_ja']}
...他5選。

正直、これさえ読めば今の流れは全部わかります。
欲しい人は「いいね & RT」してください。

↓
配布は【LINE】で自動化しました。
リプ欄のリンクから「1秒」でDLできます。
(DM待たなくてOKです)

#AI #Gemini #無料配布
"""
            st.text_area("Giveaway Promo Tweet", value=promo_text, height=250)
            if st.button("🔴 AUTO-POST (Promo)", key="auto_promo"):
                 with st.spinner("🤖 Taking control of browser..."):
                    try:
                        # Promotional strategy: Link to LINE in reply
                        promo_reply = f"【受取リンク】\nこちらのLINEで「レポート」と送ると、このPDFが自動で届きます！\n(友だち追加して待っててね)\n👇\nhttps://lin.ee/gTGnitS"
                        post_to_x(promo_text, reply_text=promo_reply, force_attach=debug_attach)
                        st.success("✅ Posted promotion thread!")
                    except Exception as e:
                        st.error(f"Failed: {e}")
                        with st.expander("詳細エラーログ (Traceback)"):
                            st.code(traceback.format_exc())

st.markdown("---")
st.caption("Powered by Antigravity Marketing Engine v3.1 (Dominator Edition)")
