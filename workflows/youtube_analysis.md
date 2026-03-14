# YouTube Analysis Workflow

## Objective
Analyze trending YouTube content in the AI & automation niche and deliver a PowerPoint report with charts and insights via email.

## Required Inputs
- **Keywords** (optional): Comma-separated search terms. Defaults: "AI automation, AI agents, AI tools, AI workflow, AI coding assistant, LLM tutorial, no-code AI"
- **Max results** (optional): Videos per keyword. Default: 20
- **Recipient email**: Where to send the final report

## Prerequisites
1. `.env` must contain:
   - `RESEND_API_KEY` — Get from resend.com (free, 3K emails/month)
2. Dependencies installed: `pip install -r requirements.txt`

**No YouTube API key needed.** No Google OAuth. No credentials.json.

## Execution Steps

### Step 1: Fetch YouTube Data
```bash
python tools/fetch_youtube_data.py \
  --keywords "AI automation,AI agents,AI tools,AI workflow,AI coding assistant,LLM tutorial,no-code AI" \
  --max-results 20 \
  --output .tmp/raw_youtube_data.json
```

**How it works:** Uses `scrapetube` to discover videos by keyword, then `yt-dlp` to pull full metadata (views, likes, comments, duration, tags). No API key needed.

**Verify:** Check `.tmp/raw_youtube_data.json` exists and has video entries with `view_count`, `like_count`, etc.

**Note:** This step takes a few minutes since yt-dlp fetches each video individually. 20 results/keyword is a good balance of speed vs coverage.

### Step 2: Analyze Data
```bash
python tools/analyze_data.py \
  --input .tmp/raw_youtube_data.json \
  --output .tmp/analysis_results.json
```

**Verify:** Check `analysis_results.json` has `summary`, `top_videos`, `trending_keywords`, `insights` sections.

**No API calls** — pure Python processing. Instant.

### Step 3: Generate Charts
```bash
python tools/generate_charts.py \
  --analysis .tmp/analysis_results.json \
  --output-dir .tmp/charts/
```

**Verify:** At least 4 of 6 chart PNGs exist in `.tmp/charts/`.

**Charts produced:**
- `top_videos.png` — Top 10 videos by views
- `engagement_dist.png` — Engagement rate distribution
- `upload_heatmap.png` — Upload day/time heatmap
- `trending_keywords.png` — Top 15 keywords
- `views_engagement.png` — Views vs engagement scatter
- `duration_perf.png` — Performance by duration

**If a chart fails:** The tool continues with remaining charts. Proceed.

### Step 4: Generate PowerPoint Deck
```bash
python tools/generate_slides.py \
  --analysis .tmp/analysis_results.json \
  --charts-dir .tmp/charts/ \
  --output .tmp/youtube_trends_report.pptx
```

**Verify:** Open `.tmp/youtube_trends_report.pptx` — should have 10 slides with charts embedded.

**Slide structure:** Title → Key Metrics → Top Videos → Trending Keywords → Engagement → Views vs Engagement → Upload Patterns → Duration → Rising Channels → Key Insights

### Step 5: Send Report Email
```bash
python tools/send_report.py \
  --pptx .tmp/youtube_trends_report.pptx \
  --analysis .tmp/analysis_results.json \
  --to "<recipient email>"
```

**Verify:** Check recipient inbox for email with .pptx attachment and summary.

**If Resend fails:** The .pptx file is at `.tmp/youtube_trends_report.pptx` — share it directly.

## Error Handling

| Error | Cause | Fix |
|-------|-------|-----|
| scrapetube returns 0 results | YouTube blocking or keyword issue | Try different keywords or wait |
| yt-dlp fails for a video | Video removed or region-locked | Tool skips and continues |
| Chart generation fails | Bad data or missing matplotlib | Check analysis JSON; `pip install matplotlib` |
| Resend 403/422 | Invalid API key or sender | Verify key in `.env`; use `onboarding@resend.dev` for testing |

## Rate Limiting
- scrapetube and yt-dlp scrape YouTube directly — there's a 0.5s pause between videos to be respectful
- If YouTube starts blocking, reduce `--max-results` or wait a few minutes
- No hard quota like the official API

## Repeatability
- Run on-demand whenever a fresh report is needed
- Previous data in `.tmp/` is overwritten each run (disposable per CLAUDE.md)
- Final deliverable: .pptx attached to email
