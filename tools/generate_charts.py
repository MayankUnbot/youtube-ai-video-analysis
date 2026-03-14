"""
generate_charts.py — Create matplotlib charts from YouTube analysis data

Usage:
    python tools/generate_charts.py \
        --analysis .tmp/analysis_results.json \
        --output-dir .tmp/charts/

Output (all PNG, 192 DPI):
    top_videos.png         — Top 10 videos by views (horizontal bar)
    engagement_dist.png    — Engagement rate distribution (histogram)
    upload_heatmap.png     — Upload day/time heatmap
    trending_keywords.png  — Top 15 trending keywords (horizontal bar)
    views_engagement.png   — Views vs engagement scatter (log x)
    duration_perf.png      — Duration bucket performance (grouped bar)
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

# Design constants
PRIMARY = "#1A1A2E"
ACCENT = "#E94560"
ACCENT_2 = "#0F3460"
BG_WHITE = "#FFFFFF"
BG_LIGHT = "#F8F9FA"
GRID_COLOR = "#EEEEEE"
DPI = 192


def setup_axes(ax):
    """Apply consistent styling to axes."""
    ax.set_facecolor(BG_LIGHT)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#DDDDDD")
    ax.spines["bottom"].set_color("#DDDDDD")


def save_chart(fig, path):
    """Save chart with consistent settings."""
    fig.tight_layout(pad=1.5)
    fig.savefig(str(path), dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def make_top_videos_chart(top_videos, output_path):
    """Horizontal bar chart of top 10 videos by views."""
    videos = top_videos.get("by_views", [])
    if not videos:
        print("  Skipping top_videos chart: no data")
        return False

    try:
        # Truncate titles
        labels = [v["title"][:40] + "..." if len(v["title"]) > 40 else v["title"] for v in reversed(videos)]
        values = [v["view_count"] for v in reversed(videos)]

        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_facecolor(BG_WHITE)
        setup_axes(ax)

        bars = ax.barh(labels, values, color=ACCENT, height=0.6, edgecolor="none")

        # Value labels
        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            label = f"{val:,.0f}" if val < 1_000_000 else f"{val / 1_000_000:.1f}M"
            ax.text(bar.get_width() + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                    label, va="center", ha="left", fontsize=8, fontweight="bold", color=PRIMARY)

        ax.set_title("Top 10 Videos by Views", fontsize=14, fontweight="bold", color=PRIMARY, pad=15)
        ax.xaxis.set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False, labelsize=9)
        ax.set_xlim(0, max_val * 1.25)

        save_chart(fig, output_path)
        print(f"  Saved: {output_path.name}")
        return True
    except Exception as e:
        print(f"  WARNING: Failed to create top_videos chart: {e}", file=sys.stderr)
        return False


def make_engagement_distribution(analysis, output_path):
    """Histogram of engagement rates across all videos."""
    top = analysis.get("top_videos", {})
    # Use engagement rates from both lists to build a representative sample
    all_rates = []
    for category in ["by_views", "by_engagement"]:
        for v in top.get(category, []):
            rate = v.get("engagement_rate", 0)
            if rate > 0:
                all_rates.append(rate)

    if len(all_rates) < 3:
        print("  Skipping engagement_dist chart: insufficient data")
        return False

    try:
        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor(BG_WHITE)
        setup_axes(ax)

        ax.hist(all_rates, bins=min(20, len(all_rates)), color=ACCENT, edgecolor=BG_WHITE, alpha=0.85)
        avg_rate = sum(all_rates) / len(all_rates)
        ax.axvline(avg_rate, color=ACCENT_2, linewidth=2, linestyle="--", label=f"Mean: {avg_rate:.2f}%")

        ax.set_title("Engagement Rate Distribution", fontsize=14, fontweight="bold", color=PRIMARY, pad=15)
        ax.set_xlabel("Engagement Rate (%)", fontsize=10, color=PRIMARY)
        ax.set_ylabel("Number of Videos", fontsize=10, color=PRIMARY)
        ax.legend(fontsize=10)
        ax.grid(axis="y", color=GRID_COLOR, linewidth=0.8, zorder=0)

        save_chart(fig, output_path)
        print(f"  Saved: {output_path.name}")
        return True
    except Exception as e:
        print(f"  WARNING: Failed to create engagement_dist chart: {e}", file=sys.stderr)
        return False


def make_upload_heatmap(upload_patterns, output_path):
    """Heatmap of upload frequency by day and hour."""
    matrix = upload_patterns.get("matrix", [])
    if not matrix or all(all(v == 0 for v in row) for row in matrix):
        print("  Skipping upload_heatmap chart: no data")
        return False

    try:
        fig, ax = plt.subplots(figsize=(12, 4))
        fig.patch.set_facecolor(BG_WHITE)

        data = np.array(matrix)
        cmap = mcolors.LinearSegmentedColormap.from_list("custom", [BG_LIGHT, ACCENT_2, ACCENT])
        im = ax.imshow(data, cmap=cmap, aspect="auto", interpolation="nearest")

        ax.set_yticks(range(7))
        ax.set_yticklabels(upload_patterns.get("day_labels", [f"Day {i}" for i in range(7)]), fontsize=9)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f"{h}:00" for h in range(0, 24, 2)], fontsize=8, rotation=45)
        ax.set_title("Upload Frequency by Day & Hour (UTC)", fontsize=14, fontweight="bold", color=PRIMARY, pad=15)

        fig.colorbar(im, ax=ax, label="Videos uploaded", shrink=0.8)

        save_chart(fig, output_path)
        print(f"  Saved: {output_path.name}")
        return True
    except Exception as e:
        print(f"  WARNING: Failed to create upload_heatmap chart: {e}", file=sys.stderr)
        return False


def make_trending_keywords_chart(trending_keywords, output_path):
    """Horizontal bar chart of top 15 keywords."""
    keywords = trending_keywords[:15]
    if not keywords:
        print("  Skipping trending_keywords chart: no data")
        return False

    try:
        labels = [k["keyword"] for k in reversed(keywords)]
        values = [k["count"] for k in reversed(keywords)]

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor(BG_WHITE)
        setup_axes(ax)

        bars = ax.barh(labels, values, color=ACCENT_2, height=0.6, edgecolor="none")

        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                    str(val), va="center", ha="left", fontsize=9, fontweight="bold", color=PRIMARY)

        ax.set_title("Top 15 Trending Keywords", fontsize=14, fontweight="bold", color=PRIMARY, pad=15)
        ax.xaxis.set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False, labelsize=9)
        ax.set_xlim(0, max_val * 1.2)

        save_chart(fig, output_path)
        print(f"  Saved: {output_path.name}")
        return True
    except Exception as e:
        print(f"  WARNING: Failed to create trending_keywords chart: {e}", file=sys.stderr)
        return False


def make_views_engagement_scatter(top_videos, output_path):
    """Scatter plot: views (log) vs engagement rate."""
    all_videos = []
    seen = set()
    for category in ["by_views", "by_engagement"]:
        for v in top_videos.get(category, []):
            vid = v.get("video_id", "")
            if vid not in seen and v.get("view_count", 0) > 0:
                seen.add(vid)
                all_videos.append(v)

    if len(all_videos) < 3:
        print("  Skipping views_engagement chart: insufficient data")
        return False

    try:
        views = [v["view_count"] for v in all_videos]
        engagement = [v["engagement_rate"] for v in all_videos]

        fig, ax = plt.subplots(figsize=(8, 6))
        fig.patch.set_facecolor(BG_WHITE)
        setup_axes(ax)

        ax.scatter(views, engagement, c=ACCENT, s=60, alpha=0.7, edgecolors=PRIMARY, linewidth=0.5)
        ax.set_xscale("log")

        ax.set_title("Views vs Engagement Rate", fontsize=14, fontweight="bold", color=PRIMARY, pad=15)
        ax.set_xlabel("Views (log scale)", fontsize=10, color=PRIMARY)
        ax.set_ylabel("Engagement Rate (%)", fontsize=10, color=PRIMARY)
        ax.grid(True, color=GRID_COLOR, linewidth=0.8, alpha=0.7)

        save_chart(fig, output_path)
        print(f"  Saved: {output_path.name}")
        return True
    except Exception as e:
        print(f"  WARNING: Failed to create views_engagement chart: {e}", file=sys.stderr)
        return False


def make_duration_performance_chart(duration_analysis, output_path):
    """Grouped bar chart of performance by duration bucket."""
    if not duration_analysis:
        print("  Skipping duration_perf chart: no data")
        return False

    try:
        buckets = list(duration_analysis.keys())
        avg_views = [duration_analysis[b]["avg_views"] for b in buckets]
        counts = [duration_analysis[b]["count"] for b in buckets]

        # Short labels
        short_labels = [b.split("(")[1].rstrip(")") if "(" in b else b for b in buckets]

        fig, ax1 = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor(BG_WHITE)
        setup_axes(ax1)

        x = np.arange(len(buckets))
        width = 0.35

        bars1 = ax1.bar(x - width / 2, avg_views, width, color=ACCENT, label="Avg Views", edgecolor="none")
        ax1.set_ylabel("Average Views", fontsize=10, color=ACCENT)
        ax1.tick_params(axis="y", labelcolor=ACCENT)

        ax2 = ax1.twinx()
        bars2 = ax2.bar(x + width / 2, counts, width, color=ACCENT_2, label="Video Count", alpha=0.7, edgecolor="none")
        ax2.set_ylabel("Video Count", fontsize=10, color=ACCENT_2)
        ax2.tick_params(axis="y", labelcolor=ACCENT_2)
        ax2.spines["top"].set_visible(False)

        ax1.set_xticks(x)
        ax1.set_xticklabels(short_labels, fontsize=9)
        ax1.set_title("Performance by Video Duration", fontsize=14, fontweight="bold", color=PRIMARY, pad=15)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=9)

        save_chart(fig, output_path)
        print(f"  Saved: {output_path.name}")
        return True
    except Exception as e:
        print(f"  WARNING: Failed to create duration_perf chart: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate charts from YouTube analysis data")
    parser.add_argument("--analysis", required=True, help="Path to analysis results JSON")
    parser.add_argument("--output-dir", default=".tmp/charts/", help="Directory to save charts")
    args = parser.parse_args()

    analysis_path = Path(args.analysis)
    if not analysis_path.exists():
        print(f"ERROR: Analysis file not found: {args.analysis}", file=sys.stderr)
        sys.exit(1)

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating charts...")
    results = {}

    results["top_videos"] = make_top_videos_chart(
        analysis.get("top_videos", {}), output_dir / "top_videos.png")

    results["engagement_dist"] = make_engagement_distribution(
        analysis, output_dir / "engagement_dist.png")

    results["upload_heatmap"] = make_upload_heatmap(
        analysis.get("upload_patterns", {}), output_dir / "upload_heatmap.png")

    results["trending_keywords"] = make_trending_keywords_chart(
        analysis.get("trending_keywords", []), output_dir / "trending_keywords.png")

    results["views_engagement"] = make_views_engagement_scatter(
        analysis.get("top_videos", {}), output_dir / "views_engagement.png")

    results["duration_perf"] = make_duration_performance_chart(
        analysis.get("duration_analysis", {}), output_dir / "duration_perf.png")

    succeeded = sum(1 for v in results.values() if v)
    print(f"\nCharts complete: {succeeded}/{len(results)} generated")
    for name, ok in results.items():
        status = "OK" if ok else "SKIPPED"
        print(f"  [{status}] {name}")


if __name__ == "__main__":
    main()
