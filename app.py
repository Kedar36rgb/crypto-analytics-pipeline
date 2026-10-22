import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import psycopg2
import streamlit as st

st.set_page_config(page_title='Crypto Market Analytics', page_icon='📊', layout='wide')

# ---------- Design tokens ----------
INK, MUTED, LINE, GRID = '#111827', '#6B7280', '#E5E7EB', '#EEF0F3'
UP, DOWN, ACCENT = '#0E9F6E', '#D64545', '#2F4BD8'
FONT = "'IBM Plex Sans', 'Segoe UI', sans-serif"
COIN_COLORS = {
    'Bitcoin': '#E8871E', 'Ethereum': '#5B6EE1', 'Solana': '#0EA5A0', 'Cardano': '#2563A8',
    'XRP': '#475569', 'Dogecoin': '#C9A227', 'Polkadot': '#D6336C', 'Chainlink': '#3B82F6',
    'Avalanche': '#DC4C4C', 'Litecoin': '#8A94A6',
}

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap');
.stApp {{ font-family: {FONT}; background: #F5F6F8; color: {INK}; }}
#MainMenu, footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ max-width: 1320px; padding-top: 2rem; padding-bottom: 3rem; }}
section[data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid {LINE}; }}
section[data-testid="stSidebar"] label p {{ font-weight: 500; color: {INK}; }}
div[data-testid="stVerticalBlockBorderWrapper"] {{ background: #FFFFFF; border-radius: 10px; border-color: {LINE}; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 28px; border-bottom: 1px solid {LINE}; }}
.stTabs [data-baseweb="tab"] {{ padding: 10px 0; font-weight: 500; color: {MUTED}; }}
.stTabs [aria-selected="true"] {{ color: {INK}; }}
.stTabs [data-baseweb="tab-highlight"] {{ background: {ACCENT}; }}
.hdr {{ display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 12px; }}
.hdr h1 {{ font-size: 30px; font-weight: 600; letter-spacing: -0.02em; margin: 0; padding: 0; color: {INK}; }}
.hdr p {{ margin: 4px 0 0; color: {MUTED}; font-size: 15px; }}
.fresh {{ text-align: right; font-size: 13px; color: {MUTED}; line-height: 1.5; }}
.fresh b {{ color: {INK}; font-weight: 500; }}
.kpi {{ background: #fff; border: 1px solid {LINE}; border-radius: 10px; padding: 16px 18px; margin-bottom: 12px; }}
.kpi .name {{ display: flex; align-items: center; gap: 8px; font-size: 14px; color: {MUTED}; font-weight: 500; }}
.kpi .dot {{ width: 9px; height: 9px; border-radius: 50%; }}
.kpi .price {{ font-size: 26px; font-weight: 600; letter-spacing: -0.02em; margin: 6px 0 2px; font-variant-numeric: tabular-nums; }}
.kpi .row {{ display: flex; justify-content: space-between; align-items: center; }}
.pill {{ font-size: 13px; font-weight: 500; padding: 2px 8px; border-radius: 999px; }}
.pill.up {{ color: {UP}; background: #E6F6EF; }}
.pill.down {{ color: {DOWN}; background: #FBEAEA; }}
.pill.flat {{ color: {MUTED}; background: #F1F2F4; }}
.sec {{ font-size: 18px; font-weight: 600; margin: 8px 0 12px; }}
.note {{ font-size: 14px; color: {MUTED}; line-height: 1.6; }}
.insight {{ border-left: 3px solid {ACCENT}; background: #F3F5FF; padding: 14px 16px; border-radius: 0 8px 8px 0; font-size: 15px; line-height: 1.6; }}
</style>
""", unsafe_allow_html=True)


# ---------- Data ----------
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
last_ts = load('SELECT MAX(ts) AS ts FROM crypto_prices')['ts'].iloc[0]

if metrics.empty:
    st.warning('No data yet. Run the pipeline once, then refresh this page.')
    st.stop()

# ---------- Header ----------
st.markdown(f"""
<div class="hdr">
  <div>
    <h1>Crypto Market Analytics</h1>
    <p>Prices, risk and cross-asset behavior, computed in SQL from hourly snapshots.</p>
  </div>
  <div class="fresh">Latest snapshot <b>{pd.to_datetime(last_ts).strftime('%d %b %Y, %H:%M')} UTC</b><br>Refreshed hourly by GitHub Actions</div>
</div>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
st.sidebar.markdown('#### Filters')
coins = sorted(metrics['coin_name'].unique())
defaults = [c for c in ['Bitcoin', 'Ethereum', 'Solana', 'Litecoin'] if c in coins] or coins[:4]
selected = st.sidebar.multiselect('Assets', coins, default=defaults)
min_d, max_d = metrics['day'].min(), metrics['day'].max()
date_range = st.sidebar.date_input('Date range', (min_d, max_d), min_value=min_d, max_value=max_d)

if not selected:
    st.info('Pick at least one asset in the sidebar to see the dashboard.')
    st.stop()
if len(date_range) != 2:
    st.info('Choose both a start and an end date.')
    st.stop()

m = metrics[metrics['coin_name'].isin(selected) & metrics['day'].between(*date_range)].copy()
d = dd[dd['coin_name'].isin(selected) & dd['day'].between(*date_range)].copy()
if m.empty:
    st.info('No data for this selection. Widen the date range.')
    st.stop()

st.sidebar.download_button('Download filtered data (CSV)', m.to_csv(index=False), 'crypto_metrics.csv', 'text/csv')
st.sidebar.caption('Source: CoinGecko API. For analysis practice, not investment advice.')


# ---------- Helpers ----------
def fmt_price(p):
    return f'${p:,.2f}' if p >= 1 else f'${p:,.4f}'


def sparkline(values, color, w=110, h=30):
    vals = [v for v in values if pd.notna(v)]
    if len(vals) < 2:
        return ''
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = ' '.join(f'{i * w / (len(vals) - 1):.1f},{h - 3 - (v - lo) / span * (h - 6):.1f}' for i, v in enumerate(vals))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}"><polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/></svg>'


def style(fig, title, height=380, pct=False):
    fig.update_layout(
        title=dict(text=title, x=0, font=dict(size=16, color=INK)),
        template='plotly_white', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family=FONT, color=MUTED, size=12), height=height,
        margin=dict(l=8, r=8, t=64, b=8), hovermode='x unified',
        legend=dict(orientation='h', y=1.14, x=1, xanchor='right', title=None),
    )
    fig.update_xaxes(showgrid=False, title=None, linecolor=LINE)
    fig.update_yaxes(gridcolor=GRID, title=None, zeroline=False, tickformat='.1%' if pct else None)
    return fig


# ---------- KPI cards ----------
st.markdown('<div class="sec">Market snapshot</div>', unsafe_allow_html=True)
latest = m.sort_values('day').groupby('coin_name').tail(1).sort_values('close_price', ascending=False)
rows = [latest.iloc[i:i + 5] for i in range(0, len(latest), 5)]
for chunk in rows:
    cols = st.columns(5)
    for col, (_, r) in zip(cols, chunk.iterrows()):
        color = COIN_COLORS.get(r['coin_name'], ACCENT)
        ret = r['daily_return']
        if pd.isna(ret) or abs(ret) < 1e-9:
            cls, txt = 'flat', '0.00%'
        else:
            cls, txt = ('up' if ret > 0 else 'down'), f'{ret * 100:+.2f}%'
        hist = m[m['coin_name'] == r['coin_name']].sort_values('day')['close_price'].tail(30)
        col.markdown(
            f'<div class="kpi"><div class="name"><span class="dot" style="background:{color}"></span>{r["coin_name"]}</div>'
            f'<div class="price">{fmt_price(r["close_price"])}</div>'
            f'<div class="row"><span class="pill {cls}">{txt} today</span>{sparkline(hist, color)}</div></div>',
            unsafe_allow_html=True)

colorway = [COIN_COLORS.get(c, ACCENT) for c in sorted(selected)]
cmap = {c: COIN_COLORS.get(c, ACCENT) for c in selected}

tab1, tab2, tab3, tab4 = st.tabs(['Performance', 'Risk', 'Correlation', 'Volume signal'])

# ---------- Performance ----------
with tab1:
    m = m.sort_values('day')
    m['rebased'] = m.groupby('coin_name')['close_price'].transform(lambda s: s / s.iloc[0] * 100)
    with st.container(border=True):
        fig = px.line(m, x='day', y='rebased', color='coin_name', color_discrete_map=cmap)
        fig.update_traces(line=dict(width=2.2))
        fig.add_hline(y=100, line_dash='dot', line_color=LINE)
        st.plotly_chart(style(fig, 'Growth of 100 invested at the start of the period'), use_container_width=True)
    ret_tbl = (m.groupby('coin_name')['close_price'].agg(lambda s: s.iloc[-1] / s.iloc[0] - 1)
               .sort_values().reset_index(name='period_return'))
    with st.container(border=True):
        fig = go.Figure(go.Bar(
            x=ret_tbl['period_return'], y=ret_tbl['coin_name'], orientation='h',
            marker_color=[UP if v >= 0 else DOWN for v in ret_tbl['period_return']],
            text=[f'{v * 100:+.1f}%' for v in ret_tbl['period_return']], textposition='outside'))
        style(fig, 'Return over the selected period', height=max(260, 60 * len(ret_tbl)))
        fig.update_layout(hovermode='closest')
        fig.update_xaxes(tickformat='.0%')
        st.plotly_chart(fig, use_container_width=True)

# ---------- Risk ----------
with tab2:
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        fig = px.line(m, x='day', y='vol_7d', color='coin_name', color_discrete_map=cmap)
        fig.update_traces(line=dict(width=2))
        st.plotly_chart(style(fig, 'Rolling 7-day volatility', pct=True), use_container_width=True)
    with c2, st.container(border=True):
        fig = px.area(d, x='day', y='drawdown', color='coin_name', color_discrete_map=cmap)
        fig.update_traces(line=dict(width=1.5), opacity=0.25)
        st.plotly_chart(style(fig, 'Drawdown from previous peak', pct=True), use_container_width=True)
    risk = m.groupby('coin_name').agg(
        avg_volatility=('vol_7d', 'mean'), best_day=('daily_return', 'max'), worst_day=('daily_return', 'min'))
    risk['max_drawdown'] = d.groupby('coin_name')['drawdown'].min()
    st.markdown('<div class="sec">Risk summary</div>', unsafe_allow_html=True)
    st.dataframe(
        risk.sort_values('max_drawdown')[['avg_volatility', 'max_drawdown', 'best_day', 'worst_day']]
        .style.format('{:.2%}'), use_container_width=True)

# ---------- Correlation ----------
with tab3:
    c = corr[corr['coin_a'].isin(selected) & corr['coin_b'].isin(selected)]
    if len(selected) < 2 or c.empty:
        st.info('Select at least two assets to compare how their daily returns move together.')
    else:
        full = c.pivot(index='coin_a', columns='coin_b', values='correlation')
        names = sorted(set(c['coin_a']) | set(c['coin_b']))
        full = full.reindex(index=names, columns=names)
        full = full.fillna(full.T)
        for n in names:
            full.loc[n, n] = 1.0
        with st.container(border=True):
            fig = px.imshow(full, text_auto='.2f', zmin=-1, zmax=1, color_continuous_scale='RdBu_r', aspect='auto')
            fig.update_layout(coloraxis_colorbar=dict(title=None, thickness=12))
            style(fig, 'Correlation of daily returns', height=460)
            fig.update_layout(hovermode='closest')
            st.plotly_chart(fig, use_container_width=True)
        st.markdown('<div class="note">Values near 1 mean two assets tend to rise and fall together, so holding both adds little diversification. Values near 0 mean their daily moves are mostly independent.</div>', unsafe_allow_html=True)

# ---------- Volume signal ----------
with tab4:
    sp = spikes[spikes['coin_name'].isin(selected) & spikes['day'].between(*date_range)].copy()
    sp['is_volume_spike'] = sp['is_volume_spike'].astype(bool)
    st.markdown('<div class="sec">Does a volume spike predict tomorrow\'s return?</div>', unsafe_allow_html=True)
    if sp['is_volume_spike'].nunique() < 2:
        st.info('Not enough spike and non-spike days in this selection. Widen the date range or add assets.')
    else:
        g = sp.groupby('is_volume_spike')['next_day_return']
        stats = pd.DataFrame({'days': g.count(), 'avg': g.mean(), 'std': g.std(), 'up_share': g.apply(lambda s: (s > 0).mean())})
        s, n = stats.loc[True], stats.loc[False]
        st.markdown(
            f'<div class="insight">Across <b>{int(s["days"])}</b> spike days (volume above 1.5x the 14-day average), the next-day return averaged '
            f'<b>{s["avg"] * 100:.2f}%</b> versus <b>{n["avg"] * 100:.2f}%</b> on normal days. Spike days were followed by a gain '
            f'<b>{s["up_share"] * 100:.0f}%</b> of the time (normal days: {n["up_share"] * 100:.0f}%), with a spread of '
            f'{s["std"] * 100:.2f}% versus {n["std"] * 100:.2f}%. Spike samples are small and this shows association, not cause.</div>',
            unsafe_allow_html=True)
        sp['group'] = sp['is_volume_spike'].map({True: 'Volume spike', False: 'Normal day'})
        c1, c2 = st.columns(2)
        with c1, st.container(border=True):
            fig = go.Figure(go.Bar(
                x=['Normal day', 'Volume spike'], y=[n['avg'], s['avg']],
                marker_color=[LINE, ACCENT], text=[f'{n["avg"] * 100:.2f}%', f'{s["avg"] * 100:.2f}%'], textposition='outside'))
            style(fig, 'Average next-day return', pct=True)
            fig.update_layout(hovermode='closest')
            st.plotly_chart(fig, use_container_width=True)
        with c2, st.container(border=True):
            fig = px.box(sp, x='group', y='next_day_return', color='group', category_orders={'group': ['Normal day', 'Volume spike']},
                         color_discrete_map={'Normal day': '#9CA3AF', 'Volume spike': ACCENT})
            fig.update_layout(showlegend=False)
            style(fig, 'Spread of next-day returns', pct=True)
            fig.update_layout(hovermode='closest')
            st.plotly_chart(fig, use_container_width=True)