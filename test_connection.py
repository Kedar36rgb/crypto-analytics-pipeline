import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print("✅ SUCCESS! Connected to the Supabase database.")
    conn.close()
except Exception as e:
    print("❌ CONNECTION FAILED. Error:")
    print(e)