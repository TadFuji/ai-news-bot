
import os
import sys
from datetime import datetime
from xhtml2pdf import pisa

# Japanese support via ReportLab
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Font configuration
# Antigravity Standard: Noto Sans JP
FONT_PATH = r"C:\Windows\Fonts\NotoSansJP-VF.ttf"
FONT_NAME = "NotoSansJP"

def create_pdf_report(articles, output_path="report.pdf"):
    """
    Generates a PDF report using xhtml2pdf (Pure Python), bypassing Selenium/Chrome.
    """
    try:
        # Register Font if available
        if os.path.exists(FONT_PATH):
            pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))
            font_family = FONT_NAME
        else:
            print("⚠️ Japanese font not found. Using default.")
            font_family = "Helvetica" # Fallback (might break JP chars)

        # 1. Prepare Data
        date_str = datetime.now().strftime("%Y.%m.%d")
        top_article = articles[0] if articles else {"title_ja": "No Data", "summary_ja": "", "source": "-"}
        
        # 2. Build HTML Content
        # We build a simple, clean HTML structure optimized for PDF
        
        news_items_html = ""
        for i, a in enumerate(articles[:5]):
            news_items_html += f"""
            <div class="news-item">
                <div class="news-title">{i+1}. {a['title_ja']}</div>
                <div class="news-meta">Source: {a.get('source', 'Web')}</div>
                <div class="news-summary">{a['summary_ja']}</div>
            </div>
            <hr class="separator">
            """

        html_content = f"""
        <html>
        <head>
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
                body {{
                    font_family: "{font_family}";
                    font-size: 10pt;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #000;
                    padding-bottom: 10px;
                    margin-bottom: 20px;
                }}
                .title {{
                    font-size: 24pt;
                    font-weight: bold;
                    color: #1a1a1a;
                }}
                .date {{
                    font-size: 12pt;
                    color: #666;
                    margin-top: 5px;
                }}
                .highlight-box {{
                    background-color: #f0f7ff;
                    border: 1px solid #cce3ff;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 20px;
                }}
                .h-title {{
                    font-size: 14pt;
                    font-weight: bold;
                    color: #0056b3;
                    margin-bottom: 10px;
                }}
                .h-content {{
                    font-size: 11pt;
                }}
                .news-item {{
                    margin-bottom: 15px;
                }}
                .news-title {{
                    font-size: 12pt;
                    font-weight: bold;
                    margin-bottom: 5px;
                }}
                .news-meta {{
                    font-size: 9pt;
                    color: #888;
                    margin-bottom: 5px;
                }}
                .news-summary {{
                    text-align: justify;
                }}
                .separator {{
                    border: none;
                    border-top: 1px dashed #ddd;
                    margin: 15px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    text-align: center;
                    font-size: 9pt;
                    color: #aaa;
                    border-top: 1px solid #eee;
                    padding-top: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">Antigravity Weekly Report</div>
                <div class="date">{date_str} Issue</div>
            </div>

            <div class="highlight-box">
                <div class="h-title">🔥 Top Topic: {top_article['title_ja'][:30]}...</div>
                <div class="h-content">
                    {top_article['summary_ja']}
                </div>
            </div>

            <h3>📊 Weekly AI Trends</h3>
            {news_items_html}

            <div class="footer">
                Powered by Antigravity News Engine | Gemini 3 Flash Preview <br/>
                For more updates, follow us on LINE: @Antigravity
            </div>
        </body>
        </html>
        """

        # 3. Generate PDF
        print(f"Generating PDF to: {output_path}")
        with open(output_path, "wb") as output_file:
            pisa_status = pisa.CreatePDF(
                src=html_content,
                dest=output_file,
                encoding='utf-8'
            )

        if pisa_status.err:
            print(f"❌ PDF Generation Error: {pisa_status.err}")
            return None
            
        print("✅ PDF Generated Successfully (xhtml2pdf)")
        return output_path

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        return None

if __name__ == "__main__":
    # Test Data
    mock_articles = [
        {"title_ja": "OpenAIがGPT-5を発表", "source": "TechCrunch", "summary_ja": "ついに次世代モデルが登場。推論能力が大幅に向上しました。"},
        {"title_ja": "Google Geminiが全デバイスに搭載", "source": "Google Blog", "summary_ja": "Android端末すべてにGemini Nanoが標準搭載されます。"},
    ]
    create_pdf_report(mock_articles, "test_report_xhtml.pdf")
