import os
import time
import shutil
import requests
import threading
from moviepy.editor import VideoFileClip, concatenate_videoclips
from PIL import Image
from io import BytesIO
from utils.visual_utils import upload_image_to_imgur, image_to_video

class VideoManager:
    def __init__(self, video_tmp_dir="./video_tmp", saves_dir="./saves"):
        self.video_tmp_dir = video_tmp_dir
        self.saves_dir = saves_dir
        self.videos_generated = 0
        os.makedirs(self.video_tmp_dir, exist_ok=True)
        os.makedirs(self.saves_dir, exist_ok=True)

    def start_video_generation(self, image_path, prompt, callback, rate_limited_flag):
        def video_gen_thread():
            try:
                # Upload image to imgur
                image_url = upload_image_to_imgur(image_path)
                
                # Generate unique video name
                video_name = f"video_{self.videos_generated}.mp4"
                temp_video_path = os.path.join(self.video_tmp_dir, video_name)
                
                # Generate video
                image_to_video(prompt, image_url, temp_video_path)
                
                # Extract last frame
                last_frame = self.extract_last_frame(temp_video_path)
                callback(video_path=temp_video_path, last_frame=last_frame, rate_limited=False)
                
                self.videos_generated += 1

            except requests.exceptions.RetryError:
                callback(video_path=None, last_frame=None, rate_limited=True)
            except Exception as e:
                print(f"Video generation failed: {str(e)}")
                callback(video_path=None, last_frame=None, rate_limited=False)

        thread = threading.Thread(target=video_gen_thread, daemon=True)
        thread.start()

    def extract_last_frame(self, video_path):
        try:
            with VideoFileClip(video_path) as clip:
                frames = [frame for i, frame in enumerate(clip.iter_frames()) 
                          if i >= clip.reader.nframes - 1]
                if frames:
                    return Image.fromarray(frames[-1])
        except Exception as e:
            print(f"Error extracting last frame: {e}")
        return None

    def compile_videos(self):
        """Compile all videos in video_tmp into a single video."""
        try:
            video_files = sorted(
                [f for f in os.listdir(self.video_tmp_dir) if f.startswith("video_")],
                key=lambda x: int(x.split("_")[1].split(".")[0])
            )
            
            if not video_files:
                return None, "No videos found to compile"

            clips = []
            for video_file in video_files:
                video_path = os.path.join(self.video_tmp_dir, video_file)
                try:
                    clip = VideoFileClip(video_path)
                    clips.append(clip)
                except Exception as e:
                    print(f"Error loading video {video_file}: {e}")
                    continue

            if not clips:
                return None, "No valid video clips found"

            compilation_path = os.path.join(self.video_tmp_dir, "compilation.mp4")
            
            final_clip = concatenate_videoclips(clips, method="compose")
            final_clip.write_videofile(compilation_path)
            
            for clip in clips:
                clip.close()
            final_clip.close()

            return compilation_path, "Success"
            
        except Exception as e:
            return None, f"Compilation failed: {str(e)}"

    def cleanup_old_videos(self):
        """Remove old video files to prevent disk space issues"""
        if not os.path.exists(self.saves_dir):
            return
        for file in os.listdir(self.saves_dir):
            if file.startswith("save_video_"):
                file_path = os.path.join(self.saves_dir, file)
                # Keep only videos from last 24 hours
                if time.time() - os.path.getctime(file_path) > 86400:
                    try:
                        os.remove(file_path)
                        print(f"Removed old video: {file_path}")
                    except Exception as e:
                        print(f"Error removing old video {file_path}: {e}")
