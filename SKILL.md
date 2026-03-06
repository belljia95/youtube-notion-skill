---
name: youtube-notion
description: Run the YouTube channel monitor to fetch new videos from tracked channels and sync them to Notion. Use when the user types /youtube-notion. Runs monitor.py and reports how many new videos were added.
---

# YouTube Notion Monitor Skill

## What This Does

Runs the YouTube channel monitoring script that:
1. Reads the list of tracked YouTube channels from Notion ("YouTube博主" database)
2. Fetches videos published in the last 7 days from each channel
3. Checks if each video already exists in Notion (to avoid duplicates)
4. Syncs new videos to the Notion "YouTube博主选题追踪" database with title, URL, description, views, likes, and publish date

## How to Run

Execute the following command and wait for it to complete (usually takes 30-60 seconds):

```bash
powershell -Command "cd 'C:\Users\90543\Projects\YouTubeNotionMonitor'; & 'C:\Users\90543\AppData\Local\Programs\Python\Python312\python.exe' 'monitor.py' 2>&1"
```

After it finishes, report to the user in Chinese:
- How many channels were monitored
- How many new videos were added
- Which channels had new content (list the video titles)
- If any errors occurred, explain them in plain Chinese

## Project Structure

| File | Purpose |
|------|---------|
| `C:\Users\90543\Projects\YouTubeNotionMonitor\monitor.py` | Main script |
| `C:\Users\90543\Projects\YouTubeNotionMonitor\config.py` | API keys and database IDs |
| `C:\Users\90543\Projects\YouTubeNotionMonitor\LEARN.md` | Learning notes |
| `C:\Users\90543\Projects\YouTubeNotionMonitor\PROGRESS.md` | Project progress log |

## Notion Databases

| Database | Notion ID | Purpose |
|----------|-----------|---------|
| YouTube博主 | `2fb60a1a5f1c80a59324f3a5df097de3` | List of channels to monitor |
| YouTube博主选题追踪 | `2fb60a1a5f1c81e7a989deb5b32a1ba4` | Synced video records |

## API Keys (stored in config.py)

- **YouTube Data API key**: starts with `AIza...` — from Google Cloud Console
- **Notion API key**: starts with `ntn_...` — from Notion Integrations page

---

## Setup Guide (How We Built This)

This section documents the full setup process so you can recreate it from scratch if needed.

### Step 1: Get a YouTube Data API Key

1. Go to https://console.cloud.google.com/
2. Create a new project (or select an existing one)
3. In the left menu, go to "APIs & Services" > "Library"
4. Search for "YouTube Data API v3" and click "Enable"
5. Go to "APIs & Services" > "Credentials"
6. Click "Create Credentials" > "API Key"
7. Copy the key — it starts with `AIza`
8. Paste it into `config.py` as `YOUTUBE_API_KEY`

**Quota note**: YouTube gives you 10,000 API units/day for free. Each channel check costs about 100-200 units. With 2 channels, you use ~400 units/day — well within the free limit.

### Step 2: Get a Notion API Key

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Give it a name (e.g., "YouTube Monitor")
4. Select your workspace
5. Click "Submit"
6. Copy the "Internal Integration Token" — it starts with `ntn_` or `secret_`
7. Paste it into `config.py` as `NOTION_API_KEY`

### Step 3: Connect the Integration to Your Notion Databases

The integration won't have access to your databases by default. For **each** database (YouTube博主 and YouTube博主选题追踪):

1. Open the database in Notion
2. Click the "..." menu in the top right
3. Click "Connections" (or "Add connections")
4. Find your integration by name and click "Confirm"

### Step 4: Get the Notion Database IDs

Each Notion database has a unique ID hidden in its URL:

1. Open the database in Notion
2. Click "Open as full page" if needed
3. Look at the URL — it looks like: `https://www.notion.so/yourworkspace/DATABASE_ID?v=...`
4. The DATABASE_ID is the 32-character string before the `?v=`
5. Copy it and paste into `config.py`

Our database IDs:
- `NOTION_CHANNEL_DATABASE_ID` = `2fb60a1a5f1c80a59324f3a5df097de3` (YouTube博主)
- `NOTION_VIDEO_DATABASE_ID` = `2fb60a1a5f1c81e7a989deb5b32a1ba4` (YouTube博主选题追踪)

### Step 5: Set Up the Notion Databases (Column Structure)

**YouTube博主 database** (channels to monitor) needs these columns:
- `Youtube博主` (Title type) — channel display name
- `主页地址` (URL type) — channel homepage link
- `channelID` (Text type) — YouTube channel ID (starts with `UC`)

To find a channel's ID: go to the channel page on YouTube, the URL contains the ID after `/channel/`.

**YouTube博主选题追踪 database** (synced videos) needs these columns:
- `Title` (Title type) — video title
- `主页地址` (URL type) — video link
- `channelID` (Text type) — which channel it came from
- `Description` (Text type) — video description (cleaned)
- `Views` (Number type) — view count
- `Likes` (Number type) — like count
- `发布时间` (Date type) — publish date
- `博主` (Select type) — channel name tag (color-coded)

### Step 6: Install Python Dependencies

Run this once to install the required library:

```bash
"C:\Users\90543\AppData\Local\Programs\Python\Python312\python.exe" -m pip install requests
```

### Step 7: Test Run

```bash
powershell -Command "cd 'C:\Users\90543\Projects\YouTubeNotionMonitor'; & 'C:\Users\90543\AppData\Local\Programs\Python\Python312\python.exe' 'monitor.py' 2>&1"
```

If it works, you'll see videos being added to Notion.

### Step 8: (Optional) Schedule Daily Runs

To run automatically every day using Windows Task Scheduler:

1. Open "Task Scheduler" (search in Start menu)
2. Click "Create Basic Task"
3. Name it "YouTube Notion Monitor"
4. Set trigger: Daily, at your preferred time
5. Set action: Start a program
6. Program: `C:\Users\90543\Projects\YouTubeNotionMonitor\run.bat`
7. Click Finish

The `run.bat` file handles running the Python script correctly.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| "获取频道列表失败" | Notion API key wrong or database not shared with integration | Check config.py key; re-share the database with the integration |
| "获取视频列表失败" | YouTube API key wrong or quota exceeded | Check the key; check quota at console.cloud.google.com |
| 0 new videos found | Videos older than 7 days, or already in Notion | Normal — means nothing new this week |
| Chinese characters garbled | Windows encoding issue | The script fixes this automatically with UTF-8 redirect |
