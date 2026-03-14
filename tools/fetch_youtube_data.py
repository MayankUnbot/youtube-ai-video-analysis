"""
fetch_youtube_data.py — Fetch YouTube video & channel data using scrapetube + yt-dlp

No API key needed. No quotas. No Google Cloud Console.

Usage:
    python tools/fetch_youtube_data.py \
        --keywords "AI automation,AI agents,LLM tools" \
        --max-results 20 \
        --output .tmp/raw_youtube_data.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import scrapetube
from yt_dlp import YoutubeDL

DEFAULT_KEYWORDS = [
    "AI automation",
    "AI agents",
    "AI tools",
    "AI workflow",
    "AI coding assistant",
    "LLM tutorial",
    "no-code AI",
]

# yt-dlp options: metadata only, no download
YDL_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "skip_download": True,
    "extract_flat": False,
}


def discover_video_ids(keyword, max_results):
    """Use scrapetube to find video IDs for a keyword. No API key needed."""
    try:
        videos = scrapetube.get_search(
            query=keyword,
            limit=max_results,
            sort_by="view_count",
        )
        results = []
        for video in videos:
            vid_id = video.get("videoId", "")
            if vid_id:
                results.append({
                    "video_id": vid_id,
                    "title": video.get("title", {}).get("runs", [{}])[0].get("text", ""),
                    "channel_title": video.get("ownerText", {}).get("runs", [{}])[0].get("text", ""),
                    "channel_id": video.get("ownerText", {}).get("runs", [{}])[0].get(
                        "navigationEndpoint", {}).get("browseEndpoint", {}).get("browseId", ""),
                    "view_count_text": video.get("viewCountText", {}).get("simpleText", ""),
                    "published_text": video.get("publishedTimeText", {}).get("simpleText", ""),
                    "thumbnail_url": video.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", ""),
                    "length_text": video.get("lengthText", {}).get("simpleText", ""),
                })
        return results
    except Exception as e:
        print(f"  ERROR discovering videos for '{keyword}': {e}", file=sys.stderr)
        return []


def enrich_with_ytdlp(video_id):
    """Use yt-dlp to get full metadata for a single video. No API key needed."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            return {
                "view_count": info.get("view_count", 0) or 0,
                "like_count": info.get("like_count", 0) or 0,
                "comment_count": info.get("comment_count", 0) or 0,
                "duration_seconds": info.get("duration", 0) or 0,
                "upload_date": info.get("upload_date", ""),  # YYYYMMDD format
                "tags": info.get("tags", []) or [],
                "categories": info.get("categories", []) or [],
                "description": (info.get("description", "") or "")[:500],
                "channel_follower_count": info.get("channel_follower_count", 0) or 0,
                "channel_id": info.get("channel_id", ""),
                "channel_url": info.get("channel_url", ""),
                "title": info.get("title", ""),
                "channel_title": info.get("uploader", ""),
                "thumbnail_url": info.get("thumbnail", ""),
            }
    except Exception as e:
        print(f"    WARNING: yt-dlp failed for {video_id}: {e}", file=sys.stderr)
        return None


def parse_upload_date(date_str):
    """Convert YYYYMMDD to ISO format."""
    if not date_str or len(date_str) != 8:
        return ""
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube data (no API key needed)")
    parser.add_argument("--keywords", default=None,
                        help="Comma-separated keywords (default: AI niche defaults)")
    parser.add_argument("--max-results", type=int, default=20,
                        help="Max results per keyword (default: 20)")
    parser.add_argument("--output", default=".tmp/raw_youtube_data.json",
                        help="Output JSON path")
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else DEFAULT_KEYWORDS

    print("YouTube Data Fetcher (no API key required)")
    print(f"  Keywords: {keywords}")
    print(f"  Max results/keyword: {args.max_results}")
    print()

    # Step 1: Discover video IDs via scrapetube
    all_videos = []
    seen_ids = set()

    for keyword in keywords:
        print(f"  Searching: '{keyword}'...")
        results = discover_video_ids(keyword, args.max_results)
        new_count = 0
        for video in results:
            if video["video_id"] not in seen_ids:
                seen_ids.add(video["video_id"])
                all_videos.append(video)
                new_count += 1
        print(f"    Found {len(results)} results, {new_count} new")

    print(f"\n  Total unique videos: {len(all_videos)}")

    # Step 2: Enrich with yt-dlp (full metadata)
    print(f"\n  Enriching with full metadata (yt-dlp)...")
    enriched_videos = []
    channels = {}
    failed = 0

    for i, video in enumerate(all_videos):
        vid_id = video["video_id"]
        print(f"    [{i + 1}/{len(all_videos)}] {video.get('title', vid_id)[:60]}...")

        metadata = enrich_with_ytdlp(vid_id)
        if metadata:
            enriched = {
                "video_id": vid_id,
                "title": metadata.get("title") or video.get("title", ""),
                "channel_id": metadata.get("channel_id") or video.get("channel_id", ""),
                "channel_title": metadata.get("channel_title") or video.get("channel_title", ""),
                "published_at": parse_upload_date(metadata.get("upload_date", "")),
                "description": metadata.get("description", ""),
                "thumbnail_url": metadata.get("thumbnail_url") or video.get("thumbnail_url", ""),
                "view_count": metadata["view_count"],
                "like_count": metadata["like_count"],
                "comment_count": metadata["comment_count"],
                "duration_seconds": metadata["duration_seconds"],
                "tags": metadata["tags"],
                "categories": metadata["categories"],
            }
            enriched_videos.append(enriched)

            # Track channel data
            ch_id = enriched["channel_id"]
            if ch_id and ch_id not in channels:
                channels[ch_id] = {
                    "channel_id": ch_id,
                    "title": enriched["channel_title"],
                    "subscriber_count": metadata.get("channel_follower_count", 0),
                    "total_views": 0,  # not available per-channel via yt-dlp
                    "video_count": 0,
                    "thumbnail_url": "",
                }
            if ch_id:
                channels[ch_id]["video_count"] += 1
                channels[ch_id]["total_views"] += enriched["view_count"]
        else:
            failed += 1

        # Brief pause to be respectful to YouTube
        if i < len(all_videos) - 1:
            time.sleep(0.5)

    # Build output
    output = {
        "fetch_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "keywords": keywords,
        "videos": enriched_videos,
        "channels": list(channels.values()),
        "trending": [],  # scrapetube doesn't have a trending endpoint
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone!")
    print(f"  Videos enriched: {len(enriched_videos)}")
    print(f"  Videos failed: {failed}")
    print(f"  Channels: {len(channels)}")
    print(f"  No API key used")
    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
