# Financial Tracker Requirements

## 1. Project Overview
A privacy-first, lightweight, personal finance dashboard designed to run locally. The application visualizes portfolio performance, cash flow, and provides financial forecasting based on local CSV data.

## 2. Core Principles
*   **Privacy First:** No data leaves the local machine (except for fetching public asset prices). No databases, no cloud sync, no tracking.
*   **Local Execution:** Runs entirely on `localhost`.
*   **Professional Aesthetic:** Clean, minimalist interface using Bootstrap 5. **No emojis** in the UI.
*   **Lightweight:** Minimal dependencies. No Docker required.
*   **Manual Control:** Data is managed via simple CSV files, allowing easy monthly updates by the user.

## 3. Data Management
The system reads directly from a `data/` directory containing:
*   `activos.csv`: Asset definitions (ID, Name, ISIN, Type).
*   `cartera.csv`: Current holdings (Asset ID, Shares, Buy Price).
*   `ingresos.csv`: Historical income logs.
*   `gastos.csv`: Historical expense logs (Categorized, with "Extraordinary" flag).
*   `aportaciones.csv`: Investment contributions.

**Sorting:** All data tables displayed in the UI must be sorted by date (Newest to Oldest).

## 4. Market Data
*   **Identifier:** Assets are queried using their **ISIN**.
*   **Provider:** Primary attempt using `investpy` (Investing.com).
*   **Mechanism:** On-demand update via a button in the UI. Prices are cached locally to prevent redundant API calls.

## 5. Visualization & Dashboard
### Current Status
*   **Asset Allocation:** Pie chart showing portfolio distribution by type.
*   **Portfolio Details:** Table showing Shares, Current Price, Market Value, and Return (%).

### Cash Flow Analysis
*   **Income Chart:** Independent line chart for monthly income evolution.
*   **Expense Chart:** Independent line chart for monthly expense evolution.
    *   *Reasoning:* Separating them prevents scale distortion (e.g., high income flattening the visualization of variable expenses).

### Forecasting (6-Month Horizon)
The application must calculate and visualize projections for the next 6 months:
1.  **Income Estimation:** Projected based on the average of the last X months or recurring entries.
2.  **Expense Estimation:** Projected based on the average of **recurring** expenses (excluding those marked as "Extraordinary").
3.  **Net Worth (Patrimonio) Estimation:**
    *   *Formula:* `Current Net Worth + (Avg. Recurring Income - Avg. Recurring Expenses) * Months`.
    *   *Constraint:* Extraordinary income/expenses must be excluded from the growth projection to provide a realistic baseline trend.

## 6. Technical Stack
*   **Backend:** Python (Flask).
*   **Frontend:** HTML5, Bootstrap 5 (Jinja2 Templates).
*   **Charts:** Plotly (Python-generated JSON).
*   **Data Processing:** Pandas.
*   **Environment:** Python Virtual Environment (`.venv`).
