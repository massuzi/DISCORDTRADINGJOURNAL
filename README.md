# DISCORDTRADINGJOURNAL

A Discord bot for parsing trade messages from specific channels and exporting them to Google Sheets for journaling and analysis.

## Features
- Parses trade messages from Discord channels using flexible regex.
- Exports parsed trades to a Google Sheet (one tab per channel).
- Handles images, timestamps, and multiple trade fields.
- Keeps your credentials and secrets safe using a `.env` file.

## Setup

### 1. Clone the repository
```
git clone https://github.com/massuzi/DISCORDTRADINGJOURNAL.git
cd DISCORDTRADINGJOURNAL
```

### 2. Install dependencies
```
pip install -r requirements.txt
```
(Or manually: `pip install discord.py google-api-python-client google-auth python-dotenv`)

### 3. Prepare your `.env` file
Create a `.env` file in the project root with:
```
DISCORD_TOKEN=your_discord_token
SPREADSHEET_ID=your_google_sheet_id
SERVICE_ACCOUNT_FILE=credentials.json
```

- Never commit your `.env` or `credentials.json` files!

### 4. Google Service Account
- Create a Google Cloud service account with Sheets API access.
- Download the `credentials.json` and place it in the project root.
- Share your Google Sheet with the service account email.

### 5. Run the bot
```
python main.py
```

## Example: Logging a Trade in Discord

A trade message in Discord should look like this:

```
https://atas.net/s/XXXXXXX.png
outcome: loss
Session: IS3
Direction: long
profit in ticks: -15
risk in ticks : 15
potential in tick:  2
Comments: nyVWAP, 8EMA 1MSD
HTF: bullish
MTF: bearish
LTF: bullish
L1: nyVWAP
L2: 8EMA
L3: 1MSD
L4:
L5:
```

- **You can leave any field empty if not applicable.**
- **The time and date are automatically taken from the Discord message timestamp.**
- If you want to adjust the time zone, change the `ZoneInfo("Europe/Amsterdam")` in `main.py` to your preferred time zone.

## Security
- All secrets are loaded from `.env` (see `.gitignore`).
- Do not share your `.env` or `credentials.json`.

## Customization
- Edit `CHANNEL_IDS` and `RANGE_NAMES` in `main.py` to match your Discord channels and Google Sheet tabs.
- Adjust regex in `parse_trade` if your trade message format changes.

## License
MIT
