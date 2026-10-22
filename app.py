import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

# --- 1. PAGE CONFIG & CUSTOM CSS ---
st.set_page_config(page_title='Crypto Terminal', layout='wide', page_icon="📈")

# Hide Streamlit's default menu, footer, and padding to make it look like a real app
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .block-container {padding-top: 2rem; padding-bottom: 2rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Custom Header
st.markdown("""
    <div style="background: linear-gradient(90deg, #00FFAA 0%, #0077FF 100%); padding: 20px; border-radius: 10px; margin-bottom: 25px;">
        <h1 style="color: white; margin: 0; font-family: 'Helvetica Neue', sans-serif;">📈 Crypto Market Terminal</h1>
        <p style="color: #e0e0e0; margin: 0; font-size: 16px;">Automated hourly data pipeline | Live SQL Analytics | Powered by Streamlit</p>
    </div>
""", unsafe_allow_html=True)

# --- 2. DATA LOADING ---
@st.cache_data(ttl=3600)
def load(query):
    uri = st.secrets['DATABASE_URL'] if 'DATABASE_URL' in st.secrets else os.getenv('DATABASE_URL')
    conn = psycopg2.connect(uri)
    try:
        return pd.read_sql(query, conn)
    finally:
        conn.close()

metrics = load('SELECT * FROM rolling_metrics ORDER BY day')
dd = load('SELECT * FROM drawdowns ORDER BY day')
corr = load('SELECT * FROM return_correlations')
spikes = load('SELECT * FROM volume_spike_analysis WHERE next_day_return IS NOT NULL')

if metrics.empty:
    st.warning('No data yet. Run the pipeline first.')
    st.stop()

# --- 3. SIDEBAR FILTERS ---
st.sidebar.markdown("### 🎛️ Dashboard Controls")
coins = sorted(metrics['coin_name'].unique())
# Default to 3 coins so the chart looks full and attractive
selected = st.sidebar.multiselect('Select Assets', coins, default=['Bitcoin', 'Ethereum', 'Solana'])

min_d, max_d = metrics['day'].min(), metrics['day'].max()
date_range = st.sidebar.date_input('Date range', (min_d, max_d), min_value=min_d, max_value=max_d)

if len(date_range) != 2:
    st.stop()

m = metrics[metrics['coin_name'].isin(selected) & metrics['day'].between(*date_range)]
d = dd[dd['coin_name'].isin(selected) & dd['day'].between(*date_range)]

# --- 4. KPI METRICS (TOP ROW) ---
st.markdown("### Market Snapshot")
latest = m.sort_values('day').groupby('coin_name').tail(1)
cols = st.columns(max(len(latest), 1))
for col, (_, row) in zip(cols, latest.iterrows()):
    change = (row['daily_return'] or 0) * 100
    col.metric(
        label=f"{row['coin_name']}", 
        value=f"${row['close_price']:,.2f}", 
        delta=f'{change:+.2f}%',
        delta_color="normal"
    )

st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

# --- 5. CHARTS ---
tab1, tab2, tab3, tab4 = st.tabs(['📈 Market Trends', '⚠️ Risk Analysis', '🔗 Correlations', '🔊 Volume Alpha'])

# Helper function to make charts look elite
def style_chart(fig, title):
    fig.update_layout(
        title=dict(text=title, font=dict(size=18, color='#FAFAFA')),
        template='plotly_dark',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        margin=dict(l=0, r=0, t=40, b=0)
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    return fig

with tab1:
    # Area chart with smooth lines
    fig1 = px.area(m, x='day', y='close_price', color='coin_name', log_y=True)
    fig1.update_traces(line=dict(width=2, shape='spline'), fillcolor='rgba(0, 255, 170, 0.1)')
    st.plotly_chart(style_chart(fig1, "Daily Close Price (Log Scale)"), use_container_width=True)
    
    fig2 = px.line(m, x='day', y='ma_7d', color='coin_name')
    fig2.update_traces(line=dict(width=2, shape='spline'))
    st.plotly_chart(style_chart(fig2, "7-Day Moving Average"), use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        fig3 = px.area(m, x='day', y='vol_7d', color='coin_name')
        st.plotly_chart(style_chart(fig3, "Rolling 7-Day Volatility"), use_container_width=True)
    with col2:
        fig4 = px.line(d, x='day', y='drawdown', color='coin_name')
        st.plotly_chart(style_chart(fig4, "Drawdown from Peak"), use_container_width=True)

with tab3:
    pivot = corr.pivot(index='coin_a', columns='coin_b', values='correlation')
    fig5 = px.imshow(pivot, text_auto='.2f', color_continuous_scale='RdBu', zmin=-1, zmax=1)
    st.plotly_chart(style_chart(fig5, "Asset Return Correlation Matrix"), use_container_width=True)

with tab4:
    st.markdown("#### Does High Volume Predict Tomorrow's Price?")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.info("💡 **Insight**\n\nWhen volume spikes >1.5x the average, next-day returns jump to **1.40%** (vs 0.18%), but risk nearly doubles.")
    with col_b:
        fig6 = px.bar(spikes, x='day', y='next_day_return', color='is_volume_spike', color_discrete_map={True: '#00FFAA', False: '#FF4B4B'})
        st.plotly_chart(style_chart(fig6, "Next-Day Return: Normal vs Spike Days"), use_container_width=True)