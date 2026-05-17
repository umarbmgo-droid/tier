# Ranked Tests — BlockMango Tier Test Bot

A full-featured BlockMango tier testing Discord bot with queues, test tickets, appeals, blacklists, and tester role management.

---

## 🤖 Features

- `/setup` — Creates all roles, channels, and categories automatically
- Queue system with a panel embed + Join Queue button
- Test tickets auto-created when a tester claims a player
- Tier roles: `HT1` `HT2` `HT3` `LT1` `LT2` `LT3` `LT4` `LT5`
- Tester roles: `SA Tester` (senior) and `AS Tester`
- Results posted to a dedicated results channel
- Appeal system (SA Tester handles)
- Blacklist system
- `/ping` and `/uptime` commands
- Streaming status: **tier testing**

---

## 📁 File Structure

```
ranked-tests-bot/
├── main.py              # Bot entry point
├── requirements.txt
├── Procfile             # Railway deployment
├── .env.example         # Copy to .env and fill in
├── utils/
│   └── db.py            # Database + shared config
└── cogs/
    ├── setup.py         # /setup command
    ├── queue.py         # Queue, claim, tickets
    ├── tester.py        # Tester management, profiles
    ├── appeal.py        # Appeal system
    ├── blacklist.py     # Blacklist system
    └── help.py          # /help, /ping, /uptime
```

---

## ⚙️ Setup (Local or Railway)

### Step 1 — Create a Discord Bot

1. Go to https://discord.com/developers/applications
2. Click **New Application** → name it `Ranked Tests`
3. Go to **Bot** tab → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Copy your **Bot Token**
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot` + `applications.commands`
   - Bot Permissions: `Administrator` (easiest) or at minimum:
     - Manage Roles, Manage Channels, Send Messages, Embed Links,
       Read Message History, View Channels, Manage Messages
7. Open the generated URL and invite the bot to your server

---

### Step 2 — Deploy on Railway via GitHub

1. Push this entire folder to a **GitHub repo**

2. Go to https://railway.app and log in

3. Click **New Project → Deploy from GitHub repo**

4. Select your repo

5. Once deployed, go to your service → **Variables** tab and add:
   ```
   TOKEN = your_bot_token_here
   ```

6. Railway will auto-detect the `Procfile` and run `python main.py`

> ⚠️ **Important:** Railway's free tier sleeps after inactivity. Use the **Hobby plan ($5/mo)** for 24/7 uptime, or use a free keep-alive service like UptimeRobot on a health endpoint.

---

### Step 3 — Run /setup in your server

1. Make sure the bot is in your server
2. Run `/setup` — **only your Discord account (ID: 253335267618848778) can run this**
3. The bot will automatically create:
   - Roles: `SA Tester`, `AS Tester`, `Tested`, `In Queue`, + all tier roles
   - Channels: `📥︱request-test`, `📋︱queue`, `🏆︱tier-results`, `📢︱appeals`
   - Category: `🎮 Test Tickets` (for test + appeal tickets)
   - The test panel embed with a **Join Queue** button

---

## 📋 Commands

### Player Commands
| Command | Description |
|---|---|
| `/queue` | View the current queue |
| `/leavequeue` | Leave the queue |
| `/profile [user]` | View tier profile |
| `/appeal` | Appeal your tier result |
| `/blacklistcheck <user>` | Check if someone is blacklisted |
| `/ping` | Check bot latency |
| `/uptime` | Check bot uptime |
| `/help` | View all commands |

### AS Tester Commands
| Command | Description |
|---|---|
| `/claim` | Claim next player in queue |
| Submit Result button | Submit tier result in ticket |
| Close Ticket button | Close a test ticket |

### SA Tester Commands
| Command | Description |
|---|---|
| `/addtester <user> <role>` | Give tester role |
| `/removetester <user> <role>` | Remove tester role |
| `/setresult <user> <ign> <tier>` | Manually set a tier |
| `/clearqueue` | Clear the queue |
| `/blacklist <user> <reason>` | Blacklist a player |
| `/unblacklist <user>` | Unblacklist a player |
| `/blacklistlist` | View all blacklisted players |
| Accept/Deny Appeal buttons | Handle tier appeals |

### Owner Only
| Command | Description |
|---|---|
| `/setup` | Initial bot setup |

---

## 🏆 Tiers

| Tier | Type |
|---|---|
| HT1 | High Tier 1 (Best) |
| HT2 | High Tier 2 |
| HT3 | High Tier 3 |
| LT1 | Low Tier 1 |
| LT2 | Low Tier 2 |
| LT3 | Low Tier 3 |
| LT4 | Low Tier 4 |
| LT5 | Low Tier 5 |
