import discord
import re
import asyncio
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import timezone
from zoneinfo import ZoneInfo  # Alleen beschikbaar in Python 3.9+
import os
from dotenv import load_dotenv

# === CONFIGURATIE ===
load_dotenv()

DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

CHANNEL_IDS = {
    "sheet1": 1088837681183727687,  # ← Kanaal-ID voor eerste tabblad
    "sheet2": 1107769486712508516   # ← Kanaal-ID voor tweede tabblad
}

RANGE_NAMES = {
    "sheet1": "Sheet1!A1",
    "sheet2": "Sheet2!A1"
}

# Dit wordt gebruikt om trades per kanaal op te slaan
all_trades = {}

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === REGEX VOOR TRADE PARSING ===
def parse_trade(message):
    text = message.content

    # 1) Haal alle URL's (images) eruit
    images = re.findall(r'https?://[^\s]+', text)
    image_str = ','.join(images)  # Gescheiden door een komma

    # 2) Probeer expliciete tijd uit de text te halen
    m_time = re.search(r'(\d{2}:\d{2})', text)
    if m_time:
        time_str = m_time.group(1)
    else:
        # fallback: gebruik Discord timestamp (UTC omzetten naar locale zonodig)
        local_time = message.created_at.replace(tzinfo=timezone.utc).astimezone(ZoneInfo("Europe/Amsterdam"))
        time_str = local_time.strftime('%H:%M')

    # 3) Parse fields line by line
    field_label_patterns = {
        'outcome': r'^outcome:\s*(.*)$',
        'session': r'^Session:\s*(.*)$',
        'direction': r'^Direction:\s*(.*)$',
        'profit': r'^profit in ticks:\s*(.*)$',
        'risk': r'^risk in ticks\s*:\s*(.*)$',
        'potential': r'^potential in tick:\s*(.*)$',
        'comments': r'^\s*comm?ents?\s*[:：]\s*(.*)$',  # Flexible: comment/comments, any colon, any whitespace
        'mtf': r'^MTF:\s*(.*)$',
        'ltf': r'^LTF:\s*(.*)$',
        'l1': r'^L1:\s*(.*)$',
        'l2': r'^L2:\s*(.*)$',
        'l3': r'^L3:\s*(.*)$',
        'l4': r'^L4:\s*(.*)$',
        'l5': r'^L5:\s*(.*)$',
    }
    field_names = list(field_label_patterns.keys())
    result = {
        'date':    local_time.strftime('%Y-%m-%d'),
        'time':    time_str if m_time else local_time.strftime('%H:%M'),
        'image':   image_str  # Alle URL's worden verzameld
    }
    # Initialize all fields as empty
    for f in field_names:
        result[f] = ''
    # Parse each line for a field
    for line in text.splitlines():
        for f in field_names:
            pattern = field_label_patterns[f]
            m = re.match(pattern, line.strip(), re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                result[f] = value
                break
        else:
            # Debug: print lines that look like comments but are not matched
            if re.match(r'.*comm?ents?.*', line, re.IGNORECASE):
                print(f"[DEBUG] Unmatched possible comments line: '{line}'")

    # 5) Zorg ervoor dat er altijd een trade is (uitkomst + richting zijn belangrijk)
    if result['outcome'] and result['direction']:
        return result  # Alleen teruggeven als we een "outcome" en "direction" hebben
    return None  # Geen geldige trade, dus None teruggeven

# === DISCORD GEGEVENS OPHALEN ===
@client.event
async def on_ready():
    print(f"✅ Ingelogd als {client.user}")

    # Loop over beide kanalen; trades per kanaal
    for sheet_key, channel_id in CHANNEL_IDS.items():
        # 1) Kanaal ophalen en debug-check
        channel = client.get_channel(channel_id)
        print(f"🔎 Kanaal lookup [{sheet_key}]:", channel)
        if channel is None:
            print(f"❌ Kanaal '{sheet_key}' (ID {channel_id}) niet gevonden of bot mist permissies.")
            continue

        # 2) Berichten ophalen
        print(f"📥 Ophalen van berichten uit kanaal '{channel.name}' ({channel_id})")
        try:
            messages = [msg async for msg in channel.history(limit=1000)]  # Geüpdatet naar 1000 berichten
            print(f"📨 {len(messages)} berichten opgehaald uit {sheet_key}")
        except Exception as e:
            print(f"⚠️ Fout bij ophalen berichten uit {sheet_key}: {e}")
            continue

        # 3) Parsen van berichten
        local_trades = []
        for msg in messages:
            print(f"🔍 Verwerken bericht {msg.id}")
            if 'outcome:' not in msg.content.lower():
                continue

            try:
                parsed = parse_trade(msg)
                if parsed:
                    local_trades.append(parsed)
                else:
                    print(f"⚠️ Bericht {msg.id} bevat geen geldige trade.")
            except Exception as e:
                print(f"⚠️ Parse error in bericht {msg.id}: {e}")

        print(f"✅ {len(local_trades)} trades geparsed uit {sheet_key}")

        # 4) Opslaan van de trades per kanaal
        if local_trades:
            all_trades[sheet_key] = local_trades
        else:
            print(f"⚠️ Geen trades om te exporteren voor {sheet_key}.")

    # 5) Exporteren naar Google Sheets
    for key, trades in all_trades.items():
        if trades:
            try:
                export_to_google_sheets(trades, RANGE_NAMES[key])
            except Exception as e:
                print(f"⚠️ Fout bij exporteren naar Google Sheets ({key}): {e}")
        else:
            print(f"⚠️ Geen trades gevonden voor {key}.")

    # 6) Sluit de bot af na verwerking van alle kanalen
    print("🔒 Alle kanalen verwerkt. Sluit bot af.")
    await client.close()

# === EXPORT NAAR GOOGLE SHEETS ===
def export_to_google_sheets(trades, sheet_range):
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)

    headers = [
    'date', 'time', 'image', 'outcome', 'session', 'direction',
    'profit', 'risk', 'potential', 'comments', 'mtf', 'ltf',
    'l1', 'l2', 'l3', 'l4', 'l5'
]
    values = [headers] + [[trade.get(h, '') for h in headers] for trade in trades]

    body = {'values': values}
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=sheet_range,
        valueInputOption='RAW',
        body=body
    ).execute()
    print(f"📤 Data geëxporteerd naar Google Sheet range: {sheet_range}")

# === SCRIPT DRAAIEN ===
def run():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.start(DISCORD_TOKEN))

if __name__ == '__main__':
    run()
