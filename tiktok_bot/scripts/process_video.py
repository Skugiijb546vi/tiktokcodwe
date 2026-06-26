import os
import subprocess
import sys
import glob

def download_video(url, output_filename="input_movie.mp4"):
    print(f"Downloading video from {url}...")
    # using yt-dlp to handle direct links and video platforms robustly
    subprocess.run(["yt-dlp", "-o", output_filename, url], check=True)
    return output_filename

def process_and_split(input_file, output_dir="clips"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print("Processing and splitting video...")
    # FFmpeg command:
    # -i input_file
    # -vf "setpts=0.95*PTS,hflip,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2" 
    # (speed up by ~1.05x, mirror horizontally, fit to 9:16 aspect ratio with black bars)
    # -af "atempo=1.05"
    # -f segment -segment_time 120
    # -c:v libx264 -preset fast
    
    command = [
        "ffmpeg", "-i", input_file,
        "-vf", "setpts=0.95*PTS,hflip,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "-af", "atempo=1.05",
        "-f", "segment",
        "-segment_time", "120",
        "-c:v", "libx264",
        "-preset", "fast",
        "-reset_timestamps", "1",
        "-map", "0",
        os.path.join(output_dir, "clip_%03d.mp4")
    ]
    
    subprocess.run(command, check=True)
    print("Video processing complete.")
    
    clips = sorted(glob.glob(os.path.join(output_dir, "clip_*.mp4")))
    return clips

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_video.py <video_url>")
        sys.exit(1)
        
    url = sys.argv[1]
    input_vid = download_video(url)
    process_and_split(input_vid)
