import streamlit as st
import json
import glob
import os
import random
import sys
from datetime import datetime

# --- Configuration ---
NEWS_BOT_OUTPUT_DIR = r"G:\マイドライブ\antigravity_on_google_drive\ai-news-bot\output"
BOT_DIR = r"G:\マイドライブ\antigravity_on_google_drive\ai-news-bot"

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
    st.header("⚙️ Settings")
    if st.button("🔄 データを再読み込み"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.caption(f"監視フォルダ:\n{NEWS_BOT_OUTPUT_DIR}")

# --- Helper Functions ---

def generate_x_posts(articles):
    top_article = articles[0]
    date_str = datetime.now().strftime("%m/%d")
    
    # URL for reply (Algorithm Strategy: No URLs in main post)
    registration_url = "https://lin.ee/gTGnitS"
    reply_text = f"【続きはこちら】\nAIを味方につけて、情報の波を乗りこなしましょう🏄‍♂️\n毎朝7時に3行要約ニュースが届きます。\n👇\n{registration_url}"

    post_a = f"""
【AIニュース速報 {date_str}】
今日のトップニュースは「{top_article['title_ja']}」。

これ、かなり重要な動きです。
{top_article['summary_ja'][:60]}...

詳細と他のトップ10ニュースはLINEで配信中。
忙しい朝のインプットに最適です。
↓ (続きはリプライへ)

#AI #Gemini #TechNews
    """.strip()

    post_b = f"""
マジか... 今日のAIニュース、激震走ってる。

1位の「{top_article['title_ja']}」の内容がヤバい。
これを知らないと完全に置いていかれるレベル。

毎朝、勝手に重要ニュースだけ要約して届けてくれるこのBot、正直「チート」級に便利です。
無料のうちに使っておくべき。
↓ (詳細はリプライから)

#AI #駆け出しエンジニアと繋がりたい
    """.strip()
    
    titles = "\\n".join([f"・{a['title_ja']}" for a in articles[:3]])
    post_c = f"""
おはようございます！今日のAIトレンドTOP3 🤖

{titles}

...他7本。
全部読む時間はなくても、これだけ知っていれば会議でドヤれます。

続きはここから（3行要約で届きます）
↓ (リプライにURL貼ります)

#今日の積み上げ #AI
    """.strip()
    
    return {
        "Professional": post_a, 
        "Viral": post_b, 
        "Summary": post_c,
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
個人開発AIボットが「ニュース収集」の常識を変える —— Gemini 2.0搭載「Antigravity News」がLINE登録者数急増中

**サブタイトル:**
「情報収集にかける時間をゼロに」。24時間体制で世界中のテックニュースを監視・要約する完全自動化システムを無料公開。

---

**【{date_str} 東京】**
個人開発者の[あなたのお名前]は本日、世界中のAIニュースをリアルタイムで収集・要約し、LINEで配信するサービス「Antigravity AI News」の本格運用を開始しました。

**■ 背景**
AI技術の進化スピードは凄まじく、毎日数百本のニュースが生まれています。「情報のキャッチアップが追いたない」というエンジニア・ビジネスマンの課題を解決するため、Googleの最新AIモデル「Gemini 2.0 Flash」を活用した完全自動化システムを開発しました。

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
        os.system(f'python "{os.path.join(BOT_DIR, "main.py")}"')
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
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("👔 Professional")
            st.text_area("Copy this:", value=posts["Professional"], height=250)
            if st.button("🔴 AUTO-POST (Thread)", key="auto_a"):
                with st.spinner("🤖 Taking control of browser..."):
                    try:
                        post_to_x(posts["Professional"], reply_text=reply_url)
                        st.success("✅ Posted thread successfully!")
                    except Exception as e:
                        st.error(f"Failed: {e}")

        with col2:
            st.subheader("🔥 Viral")
            st.text_area("Copy this:", value=posts["Viral"], height=250)
            if st.button("🔴 AUTO-POST (Thread)", key="auto_b"):
                 with st.spinner("🤖 Taking control of browser..."):
                    try:
                        post_to_x(posts["Viral"], reply_text=reply_url)
                        st.success("✅ Posted thread successfully!")
                    except Exception as e:
                        st.error(f"Failed: {e}")

        with col3:
            st.subheader("📰 Summary")
            st.text_area("Copy this:", value=posts["Summary"], height=250)
            if st.button("🔴 AUTO-POST (Thread)", key="auto_c"):
                 with st.spinner("🤖 Taking control of browser..."):
                    try:
                        post_to_x(posts["Summary"], reply_text=reply_url)
                        st.success("✅ Posted thread successfully!")
                    except Exception as e:
                        st.error(f"Failed: {e}")
        
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
                        post_to_x(promo_text, reply_text=promo_reply)
                        st.success("✅ Posted promotion thread!")
                    except Exception as e:
                        st.error(f"Failed: {e}")

st.markdown("---")
st.caption("Powered by Antigravity Marketing Engine v3.1 (Dominator Edition)")
