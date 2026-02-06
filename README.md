# Personal Wealth Management System (Personal Finance)

[🇪🇸 Versión en Español](README_ES.md)

A **private, local, and modern** financial dashboard designed to give you total control over your net worth, savings, and investments. Your data is yours and lives exclusively on your machine.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)

---

## 🚀 Quick Start

### 1. Installation
```bash
# 1. Clone the repository
git clone https://github.com/your-username/personal-finance.git
cd personal-finance

# 2. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Prepare your data (See CSV Structure below)
# Create the data/ folder and your base CSV files.

# 4. Start the application
./run.sh
```
Open your browser at `http://localhost:8501`.

---

## 📐 CSV File Structure (Configuration)

To start, create these files in the `/data` folder. Ensure you respect the **exact headers**.

### 1. Wealth Configuration
**`data/activos.csv`** (Your product catalog)
| Column | Description | Example |
| :--- | :--- | :--- |
| `id` | Unique ID (Key for everything). | `SP500_ETF` |
| `nombre` | Readable name. | `Vanguard S&P 500 UCITS ETF` |
| `isin` | ISIN (funds) or 'CASH' (money). | `IE00B3XXRP09` |
| `tipo` | `Efectivo`, `Renta Variable`, `Renta Fija`. | `Renta Variable` |
| `fuente` | `quefondos` (auto) or `manual`. | `quefondos` |

**`data/saldo_inicial.csv`** (Your starting point)
| Column | Description | Example |
| :--- | :--- | :--- |
| `id_activo` | Must match `id` in activos.csv. | `BBVA_CASH` |
| `participaciones` | Total quantity or money amount. | `2500.50` |
| `precio_medio_compra` | Historical average cost (use `1` for cash). | `1` |

**`data/aportaciones.csv`** (Your investment movements)
| Column | Description | Example |
| :--- | :--- | :--- |
| `fecha` | Date (YYYY-MM-DD). | `2026-02-15` |
| `tipo` | `COMPRA` (Buy), `VENTA` (Sell) or `AJUSTE_VALOR`. | `COMPRA` |
| `id_activo` | ID of the asset. | `MSCI_WORLD` |
| `cantidad_dinero` | Total money invested/received. | `1000` |
| `titulos` | Number of shares. | `10.5` |
| `precio_titulo` | Price per share. | `95.23` |

---

### 2. Savings Configuration (Flow)
**`data/ingresos.csv`**
| Column | Example |
| :--- | :--- |
| `fecha` | `2026-01-30` |
| `cantidad` | `2100.50` |
| `concepto` | `January Salary` |
| `categoria` | `Salary` |

**`data/gastos_variables.csv`** (Day-to-day expenses)
| Column | Description | Example |
| :--- | :--- | :--- |
| `fecha` | Date. | `2026-02-05` |
| `cantidad` | Amount. | `55.20` |
| `categoria` | Grouping for charts. | `Groceries` |
| `concepto` | Detail. | `Walmart` |
| `extraordinario` | `NO` (regular) or `SÍ` (unexpected/annual). | `NO` |

**`data/gastos_recurrentes.csv`** (Automatic monthly fixed costs)
| Column | Description | Example |
| :--- | :--- | :--- |
| `dia` | Day of the month charged. | `5` |
| `cantidad` | Fixed amount. | `12.99` |
| `categoria` | Category. | `Subscriptions` |
| `concepto` | Name. | `Netflix` |

---

## 📂 Auto-Generated Files (Do Not Edit)
The system will generate or overwrite these files:
*   `data/cartera.csv`: Calculated current portfolio state.
*   `data/precios_historicos.csv`: History of prices downloaded from the web.

---

## ✅ Key Features
*   **Total Privacy:** Works 100% offline. No data leaves your machine.
*   **Auto Tracking:** Fund price updates via web scraping (optional).
*   **Health Analysis:** "Runway" calculation (freedom months) and Savings Rate based on real expenses.
*   **Scenarios:** Future projections (Pessimistic/Realistic/Optimistic) to help you plan.

---

## 🧠 Intelligent Tools

*   **Automated Portfolio Reconstruction**: Rebuilds your entire financial state from raw transaction history.
*   **Auto-Market Data**: Integrated scraper fetches latest fund NAVs via ISIN.
*   **Smart Recurring Expenses**: Automatically projects fixed costs for accurate cash flow without manual entry.
*   **Expense Prorating**: Smooths out annual spikes (like insurance) to reveal your true monthly savings rate.
*   **Multi-Scenario Forecasting**: Projects 6-month and EOY net worth using 3 adjustable growth models.
*   **Advanced Visualization**: Interactive Sunburst and Area charts for deep portfolio insights.