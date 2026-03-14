"""
analyze_data.py — Analyze raw YouTube data into actionable insights

Usage:
    python tools/analyze_data.py \
        --input .tmp/raw_youtube_data.json \
        --output .tmp/analysis_results.json

No API calls — pure Python processing. No cost, no failures beyond bad input.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from statistics import mean, median

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "it", "this", "that", "are", "was", "be",
    "has", "had", "have", "do", "does", "did", "will", "can", "could",
    "would", "should", "may", "might", "i", "you", "he", "she", "we",
    "they", "my", "your", "his", "her", "our", "its", "not", "no", "so",
    "if", "how", "what", "when", "where", "who", "why", "which", "all",
    "just", "about", "up", "out", "one", "new", "from", "get", "got",
    "use", "using", "used", "make", "made", "way", "best", "top", "most",
    "more", "than", "like", "into", "over", "also", "here", "there",
    "now", "then", "these", "those", "been", "being", "some", "any",
    "each", "every", "both", "few", "own", "other", "such", "only",
    "same", "very", "even", "still", "after", "before", "between",
    "through", "during", "under", "above", "below", "don't", "won't",
    "can't", "didn't", "doesn't", "isn't", "aren't", "wasn't", "weren't",
    "video", "videos", "watch", "channel", "subscribe", "2024", "2025", "2026",
}

DURATION_BUCKETS = {
    "short (<5 min)": (0, 300),
    "medium (5-20 min)": (300, 1200),
    "long (20-60 min)": (1200, 3600),
    "extra-long (60+ min)": (3600, float("inf")),
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def calculate_engagement(video):
    """Calculate engagement rate as (likes + comments) / views * 100."""
    views = video.get("view_count", 0)
    if views == 0:
        return 0.0
    likes = video.get("like_count", 0)
    comments = video.get("comment_count", 0)
    return round((likes + comments) / views * 100, 3)


def rank_top_performers(videos, n=10):
    """Return top N videos by views and by engagement."""
    by_views = sorted(videos, key=lambda v: v.get("view_count", 0), reverse=True)[:n]
    by_engagement = sorted(videos, key=lambda v: v.get("engagement_rate", 0), reverse=True)[:n]

    def summarize(v):
        return {
            "video_id": v["video_id"],
            "title": v["title"],
            "channel_title": v.get("channel_title", ""),
            "view_count": v.get("view_count", 0),
            "like_count": v.get("like_count", 0),
            "comment_count": v.get("comment_count", 0),
            "engagement_rate": v.get("engagement_rate", 0),
            "duration_seconds": v.get("duration_seconds", 0),
            "published_at": v.get("published_at", ""),
        }

    return {
        "by_views": [summarize(v) for v in by_views],
        "by_engagement": [summarize(v) for v in by_engagement],
    }


def analyze_trending_topics(videos, n=20):
    """Extract top keywords from tags and titles."""
    word_counter = Counter()

    for video in videos:
        # Count tags
        for tag in video.get("tags", []):
            tag_lower = tag.lower().strip()
            if tag_lower and tag_lower not in STOP_WORDS and len(tag_lower) > 2:
                word_counter[tag_lower] += 1

        # Count significant words from titles
        title_words = re.findall(r"[a-zA-Z]+", video.get("title", "").lower())
        for word in title_words:
            if word not in STOP_WORDS and len(word) > 2:
                word_counter[word] += 1

    return [{"keyword": kw, "count": count} for kw, count in word_counter.most_common(n)]


def analyze_upload_patterns(videos):
    """Build a 7x24 heatmap matrix of upload times."""
    heatmap = [[0] * 24 for _ in range(7)]

    for video in videos:
        published = video.get("published_at", "")
        if not published:
            continue
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            heatmap[dt.weekday()][dt.hour] += 1
        except (ValueError, IndexError):
            continue

    # Find peak upload windows
    peaks = []
    for day_idx, row in enumerate(heatmap):
        for hour, count in enumerate(row):
            if count > 0:
                peaks.append({"day": DAY_NAMES[day_idx], "hour": hour, "count": count})

    peaks.sort(key=lambda p: p["count"], reverse=True)

    return {
        "matrix": heatmap,
        "day_labels": DAY_NAMES,
        "peak_windows": peaks[:5],
    }


def analyze_duration_performance(videos):
    """Analyze performance by video duration bucket."""
    buckets = {name: {"views": [], "engagement": [], "count": 0} for name in DURATION_BUCKETS}

    for video in videos:
        duration = video.get("duration_seconds", 0)
        for name, (low, high) in DURATION_BUCKETS.items():
            if low <= duration < high:
                buckets[name]["views"].append(video.get("view_count", 0))
                buckets[name]["engagement"].append(video.get("engagement_rate", 0))
                buckets[name]["count"] += 1
                break

    result = {}
    for name, data in buckets.items():
        result[name] = {
            "count": data["count"],
            "avg_views": round(mean(data["views"])) if data["views"] else 0,
            "avg_engagement": round(mean(data["engagement"]), 3) if data["engagement"] else 0,
            "median_views": round(median(data["views"])) if data["views"] else 0,
        }

    return result


def identify_rising_channels(channels, videos):
    """Find channels with high views-per-video relative to subscriber count."""
    # Count videos per channel in our dataset
    channel_video_counts = Counter(v.get("channel_id", "") for v in videos)

    rising = []
    for channel in channels:
        cid = channel.get("channel_id", "")
        subs = channel.get("subscriber_count", 0)
        total_views = channel.get("total_views", 0)
        video_count = channel.get("video_count", 1) or 1
        dataset_videos = channel_video_counts.get(cid, 0)

        views_per_video = total_views / video_count
        # "Rising" score: high views-per-video relative to subscriber count
        rising_score = (views_per_video / max(subs, 1)) * 100 if subs > 0 else 0

        rising.append({
            "channel_id": cid,
            "title": channel.get("title", ""),
            "subscriber_count": subs,
            "total_views": total_views,
            "video_count": video_count,
            "views_per_video": round(views_per_video),
            "rising_score": round(rising_score, 2),
            "videos_in_dataset": dataset_videos,
        })

    rising.sort(key=lambda c: c["rising_score"], reverse=True)
    return rising[:10]


def generate_insights(summary, top_videos, trending_keywords, duration_analysis, upload_patterns):
    """Generate natural language insights from the analysis."""
    insights = []

    # Top keyword insight
    if trending_keywords:
        top_kw = trending_keywords[0]["keyword"]
        insights.append(f"'{top_kw}' is the most frequently used keyword/tag across analyzed videos")

    # Top video insight
    if top_videos.get("by_views"):
        top = top_videos["by_views"][0]
        insights.append(
            f"The top-performing video '{top['title'][:50]}...' by {top['channel_title']} "
            f"has {top['view_count']:,} views"
        )

    # Duration insight
    if duration_analysis:
        best_bucket = max(duration_analysis.items(), key=lambda x: x[1]["avg_views"])
        insights.append(
            f"Videos in the '{best_bucket[0]}' category average the most views "
            f"({best_bucket[1]['avg_views']:,})"
        )

    # Engagement insight
    avg_eng = summary.get("avg_engagement_rate", 0)
    insights.append(f"Average engagement rate across all analyzed videos is {avg_eng}%")

    # Upload timing insight
    peaks = upload_patterns.get("peak_windows", [])
    if peaks:
        top_peak = peaks[0]
        insights.append(
            f"Most videos are uploaded on {top_peak['day']}s around {top_peak['hour']}:00 UTC"
        )

    # Volume insight
    insights.append(
        f"Analyzed {summary['total_videos']} videos across {summary['total_channels']} channels "
        f"from the last {summary.get('days_back', 30)} days"
    )

    return insights


def main():
    parser = argparse.ArgumentParser(description="Analyze raw YouTube data")
    parser.add_argument("--input", required=True, help="Path to raw YouTube data JSON")
    parser.add_argument("--output", default=".tmp/analysis_results.json", help="Output path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    videos = data.get("videos", [])
    channels = data.get("channels", [])
    trending = data.get("trending", [])

    if not videos:
        print("ERROR: No videos found in input data", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {len(videos)} videos from {len(channels)} channels...")

    # Step 1: Calculate engagement for all videos
    for video in videos:
        video["engagement_rate"] = calculate_engagement(video)

    # Step 2: Summary stats
    view_counts = [v.get("view_count", 0) for v in videos]
    engagement_rates = [v.get("engagement_rate", 0) for v in videos]
    summary = {
        "total_videos": len(videos),
        "total_channels": len(channels),
        "total_trending": len(trending),
        "avg_views": round(mean(view_counts)) if view_counts else 0,
        "median_views": round(median(view_counts)) if view_counts else 0,
        "max_views": max(view_counts) if view_counts else 0,
        "avg_engagement_rate": round(mean(engagement_rates), 3) if engagement_rates else 0,
        "median_engagement_rate": round(median(engagement_rates), 3) if engagement_rates else 0,
        "fetch_date": data.get("fetch_date", ""),
        "keywords": data.get("keywords", []),
        "days_back": data.get("days_back", 30),
    }
    print(f"  Avg views: {summary['avg_views']:,} | Median: {summary['median_views']:,}")
    print(f"  Avg engagement: {summary['avg_engagement_rate']}%")

    # Step 3: Rankings
    print(f"  Ranking top performers...")
    top_videos = rank_top_performers(videos)

    # Step 4: Trending topics
    print(f"  Analyzing trending topics...")
    trending_keywords = analyze_trending_topics(videos)

    # Step 5: Upload patterns
    print(f"  Analyzing upload patterns...")
    upload_patterns = analyze_upload_patterns(videos)

    # Step 6: Duration analysis
    print(f"  Analyzing duration performance...")
    duration_analysis = analyze_duration_performance(videos)

    # Step 7: Rising channels
    print(f"  Identifying rising channels...")
    rising_channels = identify_rising_channels(channels, videos)

    # Step 8: Generate insights
    insights = generate_insights(summary, top_videos, trending_keywords, duration_analysis, upload_patterns)

    # Build output
    output = {
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "summary": summary,
        "top_videos": top_videos,
        "trending_keywords": trending_keywords,
        "upload_patterns": upload_patterns,
        "duration_analysis": duration_analysis,
        "rising_channels": rising_channels,
        "insights": insights,
    }

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis complete!")
    print(f"  Top keyword: {trending_keywords[0]['keyword'] if trending_keywords else 'N/A'}")
    print(f"  Insights generated: {len(insights)}")
    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
