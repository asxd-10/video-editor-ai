#!/bin/bash
# Helper script to download and prepare test videos

set -e

echo "=== Video Editor AI - Test Video Preparation ==="
echo ""

# Check if yt-dlp is installed
if ! command -v yt-dlp &> /dev/null; then
    echo "❌ yt-dlp not found. Installing..."
    pip install yt-dlp
fi

# Create test videos directory
mkdir -p test_videos
cd test_videos

echo "📥 Downloading sample videos..."
echo ""

# Educational/Tutorial Videos
echo "1. Downloading Educational Video (Short Tutorial)..."
yt-dlp -f "best[height<=1080]" "https://www.youtube.com/watch?v=kqtD5dpn9C8" -o "educational_short.%(ext)s" || echo "⚠️  Failed to download educational video"

echo ""
echo "2. Downloading Cooking Tutorial..."
yt-dlp -f "best[height<=1080]" "https://www.youtube.com/watch?v=Anxl3v1XXrE" -o "cooking_tutorial.%(ext)s" || echo "⚠️  Failed to download cooking tutorial"

echo ""
echo "✅ Download complete!"
echo ""
echo "📋 Next steps:"
echo "1. Upload videos to database:"
echo "   curl -X POST http://localhost:8000/api/videos/upload -F \"file=@test_videos/educational_short.mp4\""
echo ""
echo "2. Get video_id from response, then trigger processing:"
echo "   curl -X POST http://localhost:8000/api/videos/{video_id}/transcribe"
echo "   curl -X POST http://localhost:8000/api/videos/{video_id}/analyze"
echo ""
echo "3. Run quality tests:"
echo "   python test_llm_quality.py {video_id}"

