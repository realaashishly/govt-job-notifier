# 📢 Sarkari Result Discord Alert Bot

Automated 24/7 scraper that checks `https://www.sarkariresult.com/latestjob/` hourly and delivers rich Discord notifications for newly published government jobs.

---

## 🚀 Quick Setup (3 Minutes)

### Step 1: Create a Discord Webhook
1. In Discord, go to the channel where you want notifications (e.g. `#sarkari-jobs`).
2. Click **Channel Settings** (⚙️) $\rightarrow$ **Integrations** $\rightarrow$ **Webhooks**.
3. Click **New Webhook**, name it `Sarkari Result Alerts`, and click **Copy Webhook URL**.

---

### Step 2: Push this Project to a GitHub Repository
1. Go to [GitHub](https://github.com) and click **New Repository**.
2. Name it `sarkari-discord-bot` and set it to **Private**.
3. In your local terminal, run:

```bash
cd /home/aashish/projects/sarkari-discord-bot
git init
git add .
git commit -m "Initial commit for Sarkari Discord Bot"
git branch -M main
git remote add origin https://github.com/realaashishly/govt-job-notifier.git
git push -u origin main
```

---

### Step 3: Add Your Webhook Secret in GitHub
1. In your GitHub repository, click **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Click **New repository secret**.
   - **Name**: `DISCORD_WEBHOOK_URL`
   - **Secret**: Paste your copied Discord webhook URL.
3. Click **Add secret**.

---

### Step 4: Test It (1-Click Run)
1. Go to the **Actions** tab in your repository.
2. Click **Check Sarkari Result Jobs** in the left sidebar.
3. Click **Run workflow** $\rightarrow$ **Run workflow**.

Within 30 seconds:
- You will receive a **🟢 Bot Activated** message in your Discord channel!
- The bot is now running automatically every hour 24/7.
