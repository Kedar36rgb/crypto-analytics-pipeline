import os
import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

st.set_page_config(page_title='Crypto Analytics', layout='wide')
st.title('🪙 Crypto Market Analytics')
st.caption('Automated hourly pipeline: CoinGecko → GitHub Actions → Supabase → Streamlit')

@st.cache_data(ttl=3600)
def load(query):
    # Tries Streamlit secrets first (for cloud), falls back to .env (for local)
    uri = st.secrets['DATABASE_URL'] if 'DATABASE_URL' in st.secrets else os.getenv('DATABASE_URL')
    conn = psycopg2.connect(uri)
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

# Load data from the SQL views we created in Phase 6
metrics = load('SELECT * FROM rolling_metrics ORDER BY day')
dd = load('SELECT * FROM drawdowns ORDER BY day')
corr = load('SELECT * FROM return_correlations')
spikes = load('SELECT * FROM volume_spike_analysis WHERE next_day_return IS NOT NULL')

if metrics.empty:
    st.warning('No data yet. Run the pipeline first.')
    st.stop()

# Sidebar filters
coins = sorted(metrics['coin_name'].unique())
selected = st.sidebar.multiselect('Select Coins', coins, default=coins[:4])
min_d, max_d = metrics['day'].min(), metrics['day'].max()
date_range = st.sidebar.date_input('Date range', (min_d, max_d), min_value=min_d, max_value=max_d)

if len(date_range) != 2:
    st.stop()

m = metrics[metrics['coin_name'].isin(selected) & metrics['day'].between(*date_range)]
d = dd[dd['coin_name'].isin(selected) & dd['day'].between(*date_range)]

# KPI Cards (Latest Prices)
latest = m.sort_values('day').groupby('coin_name').tail(1)
cols = st.columns(max(len(latest), 1))
for col, (_, row) in zip(cols, latest.iterrows()):
    change = (row['daily_return'] or 0) * 100
    col.metric(row['coin_name'], f"${row['close_price']:,.2f}", f'{change:+.2f}%')

# Create Tabs
tab1, tab2, tab3, tab4 = st.tabs(['📈 Prices', '⚠️ Risk', '🔗 Relationships', '🔊 Volume Signal'])

with tab1:
    # Added log_y=True to fix the scale issue between Bitcoin and smaller coins
    st.plotly_chart(px.line(m, x='day', y='close_price', color='coin_name', title='Daily Close Price', log_y=True), use_container_width=True)
    st.plotly_chart(px.line(m, x='day', y='ma_7d', color='coin_name', title='7-Day Moving Average', log_y=True), use_container_width=True)

with tab2:
    st.plotly_chart(px.line(m, x='day', y='vol_7d', color='coin_name', title='Rolling 7-Day Volatility'), use_container_width=True)
    st.plotly_chart(px.line(d, x='day', y='drawdown', color='coin_name', title='Drawdown from Peak'), use_container_width=True)

with tab3:
    pivot = corr.pivot(index='coin_a', columns='coin_b', values='correlation')
    st.plotly_chart(px.imshow(pivot, text_auto='.2f', color_continuous_scale='RdBu_r', zmin=-1, zmax=1, title='Return Correlation Matrix'), use_container_width=True)

with tab4:
    summary = spikes.groupby('is_volume_spike')['next_day_return'].agg(['count', 'mean', 'std']).reset_index()
    st.dataframe(summary, use_container_width=True)
    st.info('💡 Key Insight: When volume spikes >1.5x the 14-day average, the average next-day return jumps from 0.18% to 1.40%, but volatility nearly doubles.')