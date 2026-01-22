import os
import asyncio
import edge_tts
from moviepy import ColorClip, TextClip, CompositeVideoClip, AudioFileClip
from datetime import datetime

# Font settings (try to use a standard Windows font to avoid ImageMagick issues if possible, 
# though TextClip usually requires ImageMagick. If it fails, we fallback or user needs to install it.)
# For now, we will try to use a default method. If TextClip fails, we might need a workaround.
FONT = "Arial" 

async def _generate_voice(text, output_file, voice="ja-JP-NanamiNeural"):
    """Generate voiceover using Edge-TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def create_video(title, summary, output_path="output_video.mp4"):
    """
    Creates a simple vertical video (9:16) with voiceover and text.
    """
    temp_audio = "temp_audio.mp3"
    
    # 1. Generate Audio
    print(f"🎤 Generating Audio for: {title}...")
    text_to_speak = f"{title}. {summary}"
    try:
        asyncio.run(_generate_voice(text_to_speak, temp_audio))
    except Exception as e:
        print(f"❌ Audio generation failed: {e}")
        return None

    # 2. visual Settings (Vertical Video 1080x1920)
    w, h = 1080, 1920
    duration = AudioFileClip(temp_audio).duration + 1.0 # Buffer

    # 3. Create Background (Dark Blue)
    bg = ColorClip(size=(w, h), color=(10, 20, 40), duration=duration)

    # 4. Create Text (Title)
    # Note: TextClip requires ImageMagick binary.
    try:
        txt_clip = TextClip(title, fontsize=70, color='white', size=(w-200, None), method='caption')
        txt_clip = txt_clip.set_position('center').set_duration(duration)
        video = CompositeVideoClip([bg, txt_clip])
    except Exception as e:
        print(f"⚠️ TextClip failed (ImageMagick missing?): {e}")
        print("ℹ️ Fallback to simple colored background with audio.")
        video = bg

    # 5. Set Audio
    audio = AudioFileClip(temp_audio)
    video = video.set_audio(audio)

    # 6. Write File
    print(f"💾 Rendering Video to {output_path}...")
    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    
    # Cleanup
    if os.path.exists(temp_audio):
        os.remove(temp_audio)
        
    return output_path

if __name__ == "__main__":
    print("🧪 Testing Video Maker...")
    create_video("AIニュース速報テスト", "これはテスト動画です。音声と字幕が正しく生成されるか確認しています。", "test_video.mp4")
