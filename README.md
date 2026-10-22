# 🪙 Crypto Analytics Pipeline & Live Dashboard

> **🚀 Live Dashboard:** [https://crypto-analytics-pipeline-mdub9tntzaxthv2yq8qyof.streamlit.app/](https://crypto-analytics-pipeline-mdub9tntzaxthv2yq8qyof.streamlit.app/)

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat&logo=python)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=flat&logo=postgresql)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=flat&logo=streamlit)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-2088FF?style=flat&logo=github-actions)

> *Note: The live app may go to "sleep" after periods of inactivity due to free-tier hosting. If so, simply click "Wake up" on the screen.*

## 📌 Project Overview

This project is a fully automated, end-to-end data pipeline and interactive analytics dashboard. It ingests live cryptocurrency data from the CoinGecko API every hour, processes it through an advanced SQL analytics layer, and serves the insights via a live Streamlit application.

**The Core Business Question:** *Do spikes in trading volume predict the next day's price movement?*

## 💡 Key Findings

- **Volume Spikes are a Bullish Signal**: Across 890 coin-days of data, days with trading volume > 1.5x the 14-day average were followed by an average next-day return of **1.40%**, compared to just **0.18%** on normal days.
- **High Risk, High Reward**: While volume spikes precede higher returns, they also come with significantly higher volatility (5.69% vs 3.17%). 
- **Sentiment Integration**: The pipeline also ingests the Alternative.me Fear & Greed Index, allowing analysts to join price data with market sentiment.

## 🏗️ Architecture

```mermaid
graph LR
    A[CoinGecko API] -->|Python Ingestion| B(Supabase PostgreSQL)
    B -->|Advanced SQL Views| C(Streamlit Dashboard)
    D[Fear & Greed API] -->|Python Ingestion| B
    E[GitHub Actions] -->|Cron Job: Hourly| A