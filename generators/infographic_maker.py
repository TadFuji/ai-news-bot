
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# 日本語フォント探索（環境変数 → Windows → Linux Noto CJK の順）。
# CI(ubuntu)では NOTO_JP_FONT 環境変数 もしくは apt の fonts-noto-cjk を使う。
_FONT_CANDIDATES = [
    os.environ.get("NOTO_JP_FONT", ""),
    r"C:\Windows\Fonts\NotoSansJP-VF.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
]


def _load_font(size):
    """利用可能な日本語フォントを探して読み込む。無ければデフォルト（豆腐回避は不可）。"""
    for path in _FONT_CANDIDATES:
        if path and os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()

def create_infographic(title, summary, date_str=None, output_path="infographic.png"):
    """
    Generates a high-quality 'Breaking News' card using Pillow (No Browser).
    Safe for Headless environments.
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y.%m.%d')

    # Canvas Setup (1200x630 - OG Standard)
    width, height = 1200, 630
    # Gradient background simulated by drawing lines? Or just solid dark slate.
    # Let's do a stylish dark background.
    bg_color = (20, 20, 25) # Dark almost black
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Fonts（環境ごとにフォントを探索: CI(Ubuntu)では NOTO_JP_FONT / Noto CJK）
    title_font = _load_font(60)
    body_font = _load_font(32)
    meta_font = _load_font(24)
    logo_font = _load_font(28)

    # --- Design Elements ---

    # 1. Header Bar (Cyan Accent)
    draw.rectangle([(60, 60), (70, 130)], fill=(0, 170, 255))
    
    # 2. Label "BREAKING NEWS"
    draw.text((90, 65), f"BREAKING NEWS / {date_str}", font=meta_font, fill=(0, 170, 255))

    # 3. Title (Wrap text)
    # Simple wrap logic
    def draw_text_wrapped(text, font, max_width):
        lines = []
        # Japanese doesn't separate by space naturally, so char by char check or simple splitting
        # For simplicity in JP, we just slice.
        current_line = ""
        for char in text:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        lines.append(current_line)
        return lines

    title_lines = draw_text_wrapped(title, title_font, 1000)
    y_text = 100
    for line in title_lines[:2]: # Max 2 lines for title
        draw.text((90, y_text), line, font=title_font, fill=(255, 255, 255))
        y_text += 80

    # 4. Content Box
    box_top = y_text + 40
    box_height = 250
    draw.rectangle([(60, box_top), (1140, box_top + box_height)], outline=(100, 100, 100), width=2)
    # Slight fill? No, clean outline.
    
    # Body Text inside box
    summary_lines = draw_text_wrapped(summary, body_font, 1040)
    y_body = box_top + 40
    for line in summary_lines[:5]: # Max 5 lines
        draw.text((100, y_body), line, font=body_font, fill=(200, 200, 200))
        y_body += 45

    # 5. Footer & Branding
    draw.line([(0, 550), (1200, 550)], fill=(50, 50, 50), width=1)
    
    draw.text((60, 570), "Antigravity Report", font=logo_font, fill=(255, 255, 255))
    draw.text((350, 575), "AI Trend Analysis Bot", font=meta_font, fill=(150, 150, 150))
    
    # CTA Button simulation
    btn_x = 900
    btn_y = 560
    draw.rounded_rectangle([(btn_x, btn_y), (btn_x + 240, btn_y + 50)], radius=25, fill=(255, 255, 255))
    draw.text((btn_x + 40, btn_y + 12), "Read Full Report →", font=meta_font, fill=(0, 0, 0))

    # Save
    img.save(output_path)
    print(f"PIL: Infographic saved to {output_path}")
    return output_path

if __name__ == "__main__":
    create_infographic(
        "OpenAIがGPT-5を発表！推論能力が飛躍的向上", 
        "次世代モデルは推論能力が100倍に向上すると予測されています。産業界への影響は計り知れません。APIの価格も大幅に低下する見込みです。",
        output_path="test_pil.png"
    )
