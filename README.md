# YouTube AI Video Analysis

Automated pipeline that scrapes YouTube videos in the AI & automation niche, analyzes trends, generates a professional PowerPoint report with charts, and emails it to you.

**No YouTube API key needed.** Uses `scrapetube` + `yt-dlp` to fetch data directly.

## Pipeline

```
Fetch → Analyze → Chart → Slides → Email
```

| Step | Tool | What it does |
|------|------|-------------|
| 1 | `tools/fetch_youtube_data.py` | Discovers videos by keyword via scrapetube, enriches metadata via yt-dlp |
| 2 | `tools/analyze_data.py` | Computes engagement rates, trending keywords, upload patterns, rising channels |
| 3 | `tools/generate_charts.py` | Generates 6 matplotlib charts (bar, scatter, heatmap, histogram) |
| 4 | `tools/generate_slides.py` | Builds a 10-slide PowerPoint deck with embedded charts |
| 5 | `tools/send_report.py` | Emails the .pptx report via Resend API |

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
RESEND_API_KEY=re_your_key_here
RECIPIENT_EMAIL=you@example.com
```

Get a free Resend API key at [resend.com](https://resend.com) (3,000 emails/month).

## Usage

Run the full pipeline:

```bash
# 1. Fetch videos (takes a few minutes)
python tools/fetch_youtube_data.py \
  --keywords "AI automation,AI agents,AI tools" \
  --max-results 20 \
  --output .tmp/raw_youtube_data.json

# 2. Analyze
python tools/analyze_data.py \
  --input .tmp/raw_youtube_data.json \
  --output .tmp/analysis_results.json

# 3. Generate charts
python tools/generate_charts.py \
  --analysis .tmp/analysis_results.json \
  --output-dir .tmp/charts/

# 4. Build PowerPoint deck
python tools/generate_slides.py \
  --analysis .tmp/analysis_results.json \
  --charts-dir .tmp/charts/ \
  --output .tmp/youtube_trends_report.pptx

# 5. Send email
python tools/send_report.py \
  --pptx .tmp/youtube_trends_report.pptx \
  --analysis .tmp/analysis_results.json \
  --to "you@example.com"
```

## Charts Included

- **Top Videos by Views** — Horizontal bar chart of top 10
- **Engagement Distribution** — Histogram of engagement rates
- **Upload Heatmap** — Day-of-week x hour-of-day pattern
- **Trending Keywords** — Top 15 tags/keywords
- **Views vs Engagement** — Scatter plot (log scale)
- **Duration Performance** — Avg views & engagement by duration bucket

## Architecture

Built on the **WAT framework** (Workflows, Agents, Tools):
- **Workflows** (`workflows/`) — Markdown SOPs defining the pipeline
- **Agents** — Claude orchestrates tool execution
- **Tools** (`tools/`) — Deterministic Python scripts

## Dependencies

- `scrapetube` — YouTube search scraping (no API key)
- `yt-dlp` — Video metadata extraction (no API key)
- `python-pptx` — Local PowerPoint generation
- `matplotlib` / `numpy` — Chart generation
- `requests` / `python-dotenv` — HTTP + env config
