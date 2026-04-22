# 💰 Personal Wealth Management
> **Private, Local, and Intelligent Financial Ecosystem.**

[![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue.svg?style=for-the-badge&logo=python)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-black.svg?style=for-the-badge&logo=flask)](https://flask.palletsprojects.com/)

A professional-grade financial engine for net worth, savings, and investment tracking. All logic executes locally; your data never leaves your infrastructure.

---

## 🖼️ Feature Spotlight

### 📊 Holistic Net Worth Tracking
<img src="imgs/expenses.png" alt="Main Dashboard" width="900">

Real-time visibility into **Net Worth**, **Invested Capital**, and **Absolute Gains**. The engine calculates your **Financial Runway** based on your weighted average lifestyle.

### 📈 Precision Asset Allocation
<img src="imgs/Inversiones.png" alt="Asset Allocation" width="900">

Visualize risk exposure through interactive Sunburst charts. The system monitors performance at the individual asset level, tracking weighted average costs and real-time ROI.

### 💸 Cashflow & Savings Intelligence
<img src="imgs/flujo_caja.png" alt="Cashflow Analysis" width="900">

Prorates annual spikes to reveal your **True Monthly Savings Rate**. Utilizes predictive models to project wealth trajectory over 6-month and EOY horizons.

*Data shown in screenshots is artificial.*

---

## 🚀 Deployment

```bash
git clone https://github.com/Rubenpombo/personal-finance.git
cd personal-finance

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

./run.sh
```
> **Default endpoint:** `http://localhost:8501`

---

## 📐 Data Architecture
Initialize your workspace by copying files from `/data_template` into a new `/data` directory.

<details>
<summary><b>📂 Portfolio Configuration (activos.csv, aportaciones.csv)</b></summary>

### `activos.csv` (Asset Catalog)
| Column | Description | Supported Values / Example |
| :--- | :--- | :--- |
| `id` | Unique identifier (Primary Key). | `SP500_VANGUARD` |
| `nombre` | Human-readable name. | `Vanguard S&P 500 UCITS ETF` |
| `isin` | Asset ISIN or 'CASH'. | `IE00B3XXRP09`, `CASH` |
| `tipo` | Asset class for allocation logic. | `Equity`, `Fixed Income`, `Cash`, `Commodities` |
| `fuente` | Valuation source. | `quefondos` (Automatic scraping), `manual` |
| `precio_actual`| Last known price (used if manual). | `115.42` |

### `aportaciones.csv` (Transactions)
| Column | Description | Example |
| :--- | :--- | :--- |
| `fecha` | Operation date (YYYY-MM-DD). | `2026-02-15` |
| `tipo` | Transaction nature. | `COMPRA`, `VENTA`, `INICIAL`, `AJUSTE_VALOR` |
| `id_activo` | Target asset ID (from catalog). | `MSCI_WORLD` |
| `cantidad_dinero` | Gross amount moved. | `1000.00` |
| `titulos` | Number of units/shares. | `10.5` |
| `precio_titulo` | Execution price per unit. | `95.23` |
| `notas` | Optional metadata. | `Monthly savings plan` |
</details>

<details>
<summary><b>📂 Cashflow Tracking (ingresos.csv, gastos_variables.csv, gastos_recurrentes.csv)</b></summary>

### `ingresos.csv` (Income Log)
| Column | Description | Example |
| :--- | :--- | : :--- |
| `fecha` | Received date. | `2026-01-30` |
| `cantidad` | Net amount. | `2500.00` |
| `concepto` | Description. | `Payroll` |
| `categoria` | Grouping. | `Salary` |

### `gastos_variables.csv` (Variable Expenses)
| Column | Description | Example |
| :--- | :--- | :--- |
| `fecha` | Expense date. | `2026-02-05` |
| `cantidad` | Amount. | `55.20` |
| `categoria` | Visualization tag. | `Food` |
| `concepto` | Detail. | `Supermarket` |

### `gastos_recurrentes.csv` (Fixed Monthly Commitments)
| Column | Description | Example |
| :--- | :--- | :--- |
| `dia` | Day of month (1-31). | `5` |
| `cantidad` | Fixed monthly amount. | `12.99` |
| `categoria` | Projection tag. | `Subscriptions` |
| `concepto` | Name. | `Netflix` |
</details>

---

## 📂 System Artifacts
*   `data/cartera.csv`: Current calculated state (Snapshot).
*   `data/latest_prices.json`: Cached market valuations.
*   `data/precios_historicos.csv`: Time-series market data.

---

## 🛠 Tech Stack
- **Engine:** Python 3.12 / Pandas
- **Interface:** Flask / Bootstrap 5
- **Data Viz:** ECharts.js
- **Automation:** Local Scrapers

---
Developed by [Rubenpombo](https://github.com/Rubenpombo)
