# video_processor.py
import tempfile
import os
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

def process_video(uploaded_file):
    # 1. Save the uploaded file to a temporary file on disk
    # We do this because moviepy needs a real file path, not just memory.
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    original_path = tfile.name
    
    try:
        # 2. Load the video
        clip = VideoFileClip(original_path)
        
        # 3. Extract Metadata (The technical details)
        metadata = {
            "filename": uploaded_file.name,
            "duration": f"{clip.duration:.2f} seconds",
            "resolution": f"{clip.w}x{clip.h}",
            "fps": f"{clip.fps:.2f}",
            "filesize": f"{uploaded_file.size / (1024 * 1024):.2f} MB"
        }

        # 4. Create the Watermark
        # We make a simple text watermark "TROVEO" in the center
        # fontsize=50, white color, semi-transparent (opacity 0.5)
        txt_clip = TextClip("TROVEO PREVIEW", fontsize=50, color='white')
        txt_clip = txt_clip.set_position('center').set_duration(clip.duration).set_opacity(0.5)
        
        # Overlay the text on top of the original video
        watermarked_clip = CompositeVideoClip([clip, txt_clip])
        
        # 5. Resize it for the preview (Make it smaller/faster)
        # We shrink the height to 480 pixels
        preview_clip = watermarked_clip.resize(height=480)
        
        # 6. Save this new preview video to a temporary file
        preview_tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        preview_clip.write_videofile(preview_tfile.name, codec='libx264', audio_codec='aac', logger=None)
        
        # Close the clips to free up memory
        clip.close()
        watermarked_clip.close()

        # Return the paths and data so the main app can use them
        return {
            "metadata": metadata,
            "original_path": original_path, # Path to clean, high-res video
            "preview_path": preview_tfile.name # Path to small, watermarked video
        }

    except Exception as e:
        return {"error": str(e)}