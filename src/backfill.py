import os
import time
from datetime import datetime, timezone

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()

COINS = {'bitcoin': 'Bitcoin', 'ethereum': 'Ethereum', 'solana': 'Solana',
         'cardano': 'Cardano', 'ripple': 'XRP', 'dogecoin': 'Dogecoin',
         'polkadot': 'Polkadot', 'chainlink': 'Chainlink',
         'avalanche-2': 'Avalanche', 'litecoin': 'Litecoin'}
DAYS = 90 # Fetches 90 days of hourly data

conn = psycopg2.connect(os.environ['DATABASE_URL'])

for coin_id, name in COINS.items():
    print(f"Fetching data for {name}...")
    url = f'https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart'
    r = requests.get(url, params={'vs_currency': 'usd', 'days': DAYS}, timeout=60)
    r.raise_for_status()
    j = r.json()
    
    # Create dictionaries for quick lookup
    caps = dict((int(t), v) for t, v in j['market_caps'])
    vols = dict((int(t), v) for t, v in j['total_volumes'])
    
    with conn, conn.cursor() as cur:
        for t, price in j['prices']:
            t = int(t)
            ts = datetime.fromtimestamp(t / 1000, tz=timezone.utc).replace(minute=0, second=0, microsecond=0)
            if price and price > 0:
                cur.execute(
                    '''INSERT INTO crypto_prices
                    (coin_id, coin_name, price_usd, market_cap, volume_24h, ts)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (coin_id, ts) DO NOTHING''',
                    (coin_id, name, price, caps.get(t), vols.get(t), ts))
    
    print(f'✅ Backfilled {name}')
    time.sleep(15) # Sleep for 15 seconds to respect CoinGecko's API rate limits

conn.close()
print("🎉 ALL DONE! 90 days of data loaded.")