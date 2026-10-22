name: Crypto Live Pipeline

on:
  schedule:
    - cron: '5 * * * *' # Runs at minute 5 of every hour
  workflow_dispatch: # Allows you to run it manually for testing

jobs:
  fetch-data:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install Dependencies
        run: pip install -r requirements.txt

      # --- DEBUG STEP ADDED HERE ---
      - name: Check Secret Length
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: |
          echo "The length of the DATABASE_URL secret is: ${#DATABASE_URL} characters."
          if [ ${#DATABASE_URL} -lt 50 ]; then
            echo "❌ ERROR: The secret seems too short! Did you paste the connection string correctly in GitHub Settings?"
            exit 1
          else
            echo "✅ The secret length looks correct."
          fi
      # -----------------------------

      - name: Run Extraction Script
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: python src/fetch_data.py