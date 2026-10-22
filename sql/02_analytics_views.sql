-- 1. Daily Closing Prices
CREATE OR REPLACE VIEW daily_prices AS
SELECT DISTINCT ON (coin_id, ts::date)
coin_id, coin_name,
ts::date AS day,
price_usd AS close_price,
volume_24h
FROM crypto_prices
ORDER BY coin_id, ts::date, ts DESC;

-- 2. Daily Returns and Volume Change (Window Functions)
CREATE OR REPLACE VIEW daily_returns AS
SELECT
coin_id, coin_name, day, close_price, volume_24h,
close_price / NULLIF(LAG(close_price) OVER w, 0) - 1 AS daily_return,
volume_24h / NULLIF(LAG(volume_24h) OVER w, 0) - 1 AS volume_change
FROM daily_prices
WINDOW w AS (PARTITION BY coin_id ORDER BY day);

-- 3. Rolling 7-day Volatility and Moving Average
CREATE OR REPLACE VIEW rolling_metrics AS
SELECT
coin_id, coin_name, day, close_price, daily_return,
STDDEV(daily_return) OVER (PARTITION BY coin_id ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS vol_7d,
AVG(close_price) OVER (PARTITION BY coin_id ORDER BY day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7d
FROM daily_returns;

-- 4. Drawdown from Running Peak (CTE + Window Function)
CREATE OR REPLACE VIEW drawdowns AS
WITH peaks AS (
    SELECT coin_id, coin_name, day, close_price,
    MAX(close_price) OVER (PARTITION BY coin_id ORDER BY day) AS running_peak
    FROM daily_prices
)
SELECT coin_id, coin_name, day, close_price, running_peak,
close_price / running_peak - 1 AS drawdown
FROM peaks;

-- 5. Volume Spike Analysis (To answer your main question!)
CREATE OR REPLACE VIEW volume_spike_analysis AS
WITH base AS (
    SELECT coin_id, coin_name, day, daily_return, volume_24h,
    AVG(volume_24h) OVER (PARTITION BY coin_id ORDER BY day ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS avg_vol_14d,
    LEAD(daily_return) OVER (PARTITION BY coin_id ORDER BY day) AS next_day_return
    FROM daily_returns
)
SELECT *,
volume_24h > 1.5 * avg_vol_14d AS is_volume_spike
FROM base
WHERE avg_vol_14d IS NOT NULL;

-- 6. Pairwise Return Correlation
CREATE OR REPLACE VIEW return_correlations AS
SELECT a.coin_name AS coin_a, b.coin_name AS coin_b,
CORR(a.daily_return, b.daily_return) AS correlation,
COUNT(*) AS n_days
FROM daily_returns a
JOIN daily_returns b ON a.day = b.day AND a.coin_id < b.coin_id
WHERE a.daily_return IS NOT NULL AND b.daily_return IS NOT NULL
GROUP BY a.coin_name, b.coin_name;

-- 7. Sentiment Join (Joining our two datasets!)
CREATE OR REPLACE VIEW returns_with_sentiment AS
SELECT r.coin_name, r.day, r.daily_return, f.value AS fear_greed, f.label
FROM daily_returns r
JOIN fear_greed f ON f.day = r.day;