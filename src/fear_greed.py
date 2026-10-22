import os
from datetime import datetime, timezone

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

print("Fetching Fear and Greed data...")
r = requests.get('https://api.alternative.me/fng/', params={'limit': 120}, timeout=30)
r.raise_for_status()
rows = r.json()['data']

conn = psycopg2.connect(os.environ['DATABASE_URL'])
with conn, conn.cursor() as cur:
    for row in rows:
        day = datetime.fromtimestamp(int(row['timestamp']), tz=timezone.utc).date()
        cur.execute(
            '''INSERT INTO fear_greed (day, value, label) 
               VALUES (%s, %s, %s)
               ON CONFLICT (day) DO UPDATE SET value = EXCLUDED.value, label = EXCLUDED.label''',
            (day, int(row['value']), row['value_classification']))
conn.close()
print(f'✅ Loaded {len(rows)} days of Fear & Greed data')