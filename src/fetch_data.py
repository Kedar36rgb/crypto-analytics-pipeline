import logging
import os
import sys
import time
from datetime import datetime, timezone

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

COINS = ['bitcoin', 'ethereum', 'solana', 'cardano', 'ripple',
         'dogecoin', 'polkadot', 'chainlink', 'avalanche-2', 'litecoin']
URL = 'https://api.coingecko.com/api/v3/coins/markets'

def fetch_with_retry(retries=3, backoff=5):
    params = {'vs_currency': 'usd', 'ids': ','.join(COINS), 'order': 'market_cap_desc'}
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(URL, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, list) or not data:
                raise ValueError(f'Unexpected response: {str(data)[:200]}')
            return data
        except (requests.RequestException, ValueError) as e:
            logging.warning('Attempt %d/%d failed: %s', attempt, retries, e)
            if attempt == retries:
                raise
            time.sleep(backoff * attempt)

def is_valid(coin):
    price = coin.get('current_price')
    return (price is not None and price > 0
            and coin.get('market_cap') is not None
            and coin.get('total_volume') is not None)

def main():
    logging.info('Starting data fetch...')
    data = fetch_with_retry()
    
    # We truncate the time to the top of the hour to prevent duplicates if it runs multiple times
    ts = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    valid = [c for c in data if is_valid(c)]
    skipped = len(data) - len(valid)
    
    if skipped:
        logging.warning('Skipped %d invalid records', skipped)
    if not valid:
        logging.error('No valid records, aborting')
        sys.exit(1)
    
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    try:
        with conn, conn.cursor() as cur:
            for c in valid:
                cur.execute(
                    '''INSERT INTO crypto_prices
                    (coin_id, coin_name, price_usd, market_cap, volume_24h, ts)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (coin_id, ts) DO NOTHING''',
                    (c['id'], c['name'], c['current_price'],
                     c['market_cap'], c['total_volume'], ts))
        logging.info('Loaded %d rows for %s', len(valid), ts)
    finally:
        conn.close()

if __name__ == '__main__':
    main()