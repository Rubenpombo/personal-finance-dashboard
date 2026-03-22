import pandas as pd
import json
import os
import market_data
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
PRICES_FILE = os.path.join(DATA_DIR, 'latest_prices.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'precios_historicos.csv')

def rebuild_portfolio():
    """Regenerates cartera.csv based on aportaciones.csv (including INICIAL records)"""
    try:
        # Start empty
        portfolio = {}

        # 1. Process Aportaciones (including INICIAL)
        aportaciones_path = os.path.join(DATA_DIR, "aportaciones.csv")
        if os.path.exists(aportaciones_path):
            df_ops = pd.read_csv(aportaciones_path)
            if not df_ops.empty and 'fecha' in df_ops.columns:
                df_ops['fecha'] = pd.to_datetime(df_ops['fecha'])
                # Order by date, then ensure INICIAL comes first if same date
                df_ops['tipo_rank'] = df_ops['tipo'].apply(lambda x: 0 if str(x).upper() == 'INICIAL' else 1)
                df_ops.sort_values(by=['fecha', 'tipo_rank'], inplace=True)

                for _, op in df_ops.iterrows():
                    asset_id = op['id_activo']
                    tipo = str(op['tipo']).upper().strip()
                    titulos_op = float(op['titulos']) if pd.notnull(op['titulos']) else 0.0
                    cantidad_op = float(op['cantidad_dinero']) if pd.notnull(op['cantidad_dinero']) else 0.0
                    precio_op = float(op['precio_titulo']) if pd.notnull(op['precio_titulo']) else 0.0

                    if asset_id not in portfolio:
                        portfolio[asset_id] = {'participaciones': 0.0, 'precio_medio_compra': 0.0}

                    current = portfolio[asset_id]

                    if tipo == 'INICIAL' or tipo == 'COMPRA':
                        total_cost_old = current['participaciones'] * current['precio_medio_compra']
                        total_cost_new = titulos_op * precio_op
                        new_shares = current['participaciones'] + titulos_op
                        
                        if new_shares > 0:
                            new_avg = (total_cost_old + total_cost_new) / new_shares
                            current['participaciones'] = new_shares
                            current['precio_medio_compra'] = round(new_avg, 2)
                        
                        # Handle CASH impact for COMPRA (INICIAL has no cash impact as it's the starting point)
                        if tipo == 'COMPRA' and 'CASH_DIG' in portfolio:
                            portfolio['CASH_DIG']['participaciones'] -= cantidad_op
                            
                    elif tipo == 'VENTA':
                        current['participaciones'] = max(0.0, current['participaciones'] - titulos_op)
                        if 'CASH_DIG' in portfolio:
                            portfolio['CASH_DIG']['participaciones'] += cantidad_op
                        
                    elif tipo == 'AJUSTE_VALOR':
                        val = cantidad_op if cantidad_op > 0 else titulos_op
                        current['participaciones'] = val
                        current['precio_medio_compra'] = 1.0 # Reset cost basis for cash

        # 3. Save calculated state to cartera.csv
        rows = []
        for asset_id, data in portfolio.items():
            # Only save if there's something relevant (or it was in initial)
            # Keeping 0 balance items is sometimes useful for history, but let's keep it clean
            rows.append({
                'id_activo': asset_id,
                'participaciones': round(data['participaciones'], 6),
                'precio_medio_compra': round(data['precio_medio_compra'], 2)
            })
            
        df_final = pd.DataFrame(rows)
        # Ensure columns order
        df_final = df_final[['id_activo', 'participaciones', 'precio_medio_compra']]
        df_final.to_csv(os.path.join(DATA_DIR, "cartera.csv"), index=False)
        
    except Exception as e:
        print(f"Error rebuilding portfolio: {e}")

# Global cache state
_data_cache = {
    'payload': None,  # (activos, cartera, ingresos, gastos, aportaciones)
    'mtimes': {}      # {file_path: last_mtime}
}

def load_data():
    """Loads all CSV data with an optimization cache based on file modification times."""
    global _data_cache
    
    # Ensure cartera is up to date
    rebuild_portfolio()
    
    # Files to monitor for changes
    paths = {
        'activos': os.path.join(DATA_DIR, "activos.csv"),
        'cartera': os.path.join(DATA_DIR, "cartera.csv"),
        'aportaciones': os.path.join(DATA_DIR, "aportaciones.csv"),
        'ingresos': os.path.join(DATA_DIR, "ingresos.csv"),
        'gastos_var': os.path.join(DATA_DIR, "gastos_variables.csv"),
        'recurrentes': os.path.join(DATA_DIR, "gastos_recurrentes.csv")
    }
    
    # Check if any file has changed since last load
    changed = False
    current_mtimes = {}
    for p in paths.values():
        if os.path.exists(p):
            mtime = os.path.getmtime(p)
            current_mtimes[p] = mtime
            if _data_cache['mtimes'].get(p) != mtime:
                changed = True
    
    # Return from cache if possible
    if not changed and _data_cache['payload'] is not None:
        return _data_cache['payload']

    try:
        activos = pd.read_csv(paths['activos'])
        cartera = pd.read_csv(paths['cartera'])
        
        # Load Income (Optional)
        ingresos_path = paths['ingresos']
        ingresos = pd.read_csv(ingresos_path) if os.path.exists(ingresos_path) else pd.DataFrame(columns=['fecha', 'cantidad', 'concepto', 'categoria'])
        
        # Load variable expenses (Optional)
        gastos_path = paths['gastos_var']
        if os.path.exists(gastos_path):
            gastos = pd.read_csv(gastos_path)
        elif os.path.exists(os.path.join(DATA_DIR, "gastos.csv")):
            gastos = pd.read_csv(os.path.join(DATA_DIR, "gastos.csv"))
        else:
            gastos = pd.DataFrame(columns=['fecha', 'cantidad', 'categoria', 'concepto'])
            
        aportaciones_path = paths['aportaciones']
        aportaciones = pd.read_csv(aportaciones_path) if os.path.exists(aportaciones_path) else pd.DataFrame(columns=['fecha', 'tipo', 'id_activo', 'cantidad_dinero', 'titulos', 'precio_titulo'])

        # Convert dates for standard dataframes
        for df in [ingresos, gastos, aportaciones]:
            if not df.empty and 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'])
        
        # --- PROCESS RECURRENT EXPENSES ---
        recurrentes_path = paths['recurrentes']
        if os.path.exists(recurrentes_path):
            recurrentes = pd.read_csv(recurrentes_path)
            if not recurrentes.empty:
                # Determine date range
                min_date = datetime.now()
                if not ingresos.empty:
                    min_date = min(min_date, ingresos['fecha'].min())
                if not gastos.empty:
                    min_date = min(min_date, gastos['fecha'].min())
                
                # Generate until current month (inclusive)
                end_date = datetime.now()
                
                # Generate dates
                generated_rows = []
                # Create a date range for months
                date_range = pd.period_range(start=min_date, end=end_date, freq='M')
                
                for _, row in recurrentes.iterrows():
                    day = int(row['dia'])
                    for period in date_range:
                        # Handle month length (e.g., day 30 in Feb)
                        try:
                            # Try to create date with preferred day
                            dt = pd.Timestamp(year=period.year, month=period.month, day=day)
                        except ValueError:
                            # If invalid (e.g., Feb 30), take last day of month
                            dt = period.to_timestamp(how='end')
                            
                        generated_rows.append({
                            'fecha': dt,
                            'cantidad': row['cantidad'],
                            'categoria': row['categoria'],
                            'concepto': row['concepto']
                        })
                
                if generated_rows:
                    df_recurrentes = pd.DataFrame(generated_rows)
                    gastos = pd.concat([gastos, df_recurrentes], ignore_index=True)

        # Final processing for all dataframes
        for df in [ingresos, gastos, aportaciones]:
            if not df.empty and 'fecha' in df.columns:
                # Ensure date type again just in case concatenation messed it up
                df['fecha'] = pd.to_datetime(df['fecha'])
                df['periodo'] = df['fecha'].dt.to_period('M') 
                df.sort_values(by='fecha', ascending=True, inplace=True)
        
        # Update cache
        _data_cache['payload'] = (activos, cartera, ingresos, gastos, aportaciones)
        _data_cache['mtimes'] = current_mtimes
        
        return _data_cache['payload']
    except Exception as e:
        print(f"Error loading data: {e}")
        return None, None, None, None, None

def get_latest_prices():
    if os.path.exists(PRICES_FILE):
        try:
            with open(PRICES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_price_history(prices_dict):
    today = datetime.now().strftime('%Y-%m-%d')
    new_rows = []
    for asset_id, price in prices_dict.items():
        new_rows.append({'fecha': today, 'id_activo': asset_id, 'precio': price})
    df_new = pd.DataFrame(new_rows)
    if os.path.exists(HISTORY_FILE):
        try:
            df_hist = pd.read_csv(HISTORY_FILE)
            df_hist = df_hist[df_hist['fecha'] != today]
            df_final = pd.concat([df_hist, df_new], ignore_index=True)
        except:
            df_final = df_new
    else:
        df_final = df_new
    df_final.to_csv(HISTORY_FILE, index=False)

def get_portfolio_history_chart_data():
    """Generates historical portfolio valuation based on historical prices and holdings at each point in time."""
    if not os.path.exists(HISTORY_FILE): return None
    try:
        # 1. Load data
        df_hist = pd.read_csv(HISTORY_FILE)
        _, _, _, _, aportaciones = load_data()
        
        if aportaciones.empty:
            return None
            
        # 2. Pivot historical prices
        df_pivot = df_hist.pivot(index='fecha', columns='id_activo', values='precio').fillna(0)
        dates = df_pivot.index.tolist()
        
        # 3. Calculate shares for each point in time
        total_values = []
        for date_str in dates:
            current_date = pd.to_datetime(date_str)
            
            # Sum up all operations until this date
            mask = aportaciones['fecha'] <= current_date
            df_ops = aportaciones[mask].copy()
            
            if df_ops.empty:
                total_values.append(0.0)
                continue
                
            # Current shares per asset at this point in time
            def calc_shares(row):
                tipo = str(row['tipo']).upper().strip()
                if tipo in ['INICIAL', 'COMPRA']: return row['titulos']
                if tipo == 'VENTA': return -row['titulos']
                return 0.0
                
            df_ops['share_delta'] = df_ops.apply(calc_shares, axis=1)
            shares_at_date = df_ops.groupby('id_activo')['share_delta'].sum().to_dict()
            
            # Calculate total valuation with the prices of THAT date
            daily_total = 0.0
            for asset_id, shares in shares_at_date.items():
                if shares > 0 and asset_id in df_pivot.columns:
                    price = df_pivot.at[date_str, asset_id]
                    daily_total += shares * price
                    
            total_values.append(round(daily_total, 2))
            
        return {'dates': dates, 'values': total_values}
    except Exception as e:
        print(f"Error generating history chart: {e}")
        return None

def refresh_market_data():
    activos, _, _, _, _ = load_data()
    if activos is not None:
        old_prices = get_latest_prices()
        new_prices = market_data.update_prices(activos)
        
        # Fallback: If a price is 0 (not found), use the old price if it exists
        final_prices = {}
        for asset_id, price in new_prices.items():
            if price == 0.0 and asset_id in old_prices and old_prices[asset_id] > 0:
                final_prices[asset_id] = old_prices[asset_id]
                print(f"  -> Using fallback price for {asset_id}: {old_prices[asset_id]}")
            else:
                final_prices[asset_id] = price

        try:
            with open(PRICES_FILE, 'w') as f:
                json.dump(final_prices, f)
            save_price_history(final_prices)
            return True, "Precios actualizados e historial guardado (con fallbacks si fue necesario)."
        except Exception as e:
            return False, f"Error guardando precios: {e}"
    return False, "Error cargando activos."

def get_portfolio_summary():
    activos, cartera, ingresos, gastos, aportaciones = load_data()
    if activos is None: return {}
    prices = get_latest_prices()
    df = pd.merge(cartera, activos, left_on='id_activo', right_on='id', how='left')
    df['precio_actual'] = df['id_activo'].map(prices).fillna(0.0)
    df['valor_mercado'] = (df['participaciones'] * df['precio_actual']).round(2)
    df['coste_total'] = (df['participaciones'] * df['precio_medio_compra']).round(2)
    df['plusvalia'] = (df['valor_mercado'] - df['coste_total']).round(2)
    df['rentabilidad'] = df.apply(lambda row: round(row['plusvalia'] / row['coste_total'] * 100, 2) if row['coste_total'] != 0 else 0, axis=1)
    total_patrimonio = round(df['valor_mercado'].sum(), 2)
    total_inversion = round(df['coste_total'].sum(), 2)
    beneficio_total_abs = round(total_patrimonio - total_inversion, 2)
    
    df['tipo_norm'] = df['tipo'].str.lower().str.strip()
    equity_mask = df['tipo_norm'].str.contains('variable') | df['tipo_norm'].str.contains('stock') | df['tipo_norm'].str.contains('acción')
    equity_value = round(df[equity_mask]['valor_mercado'].sum(), 2)
    valor_riesgo = equity_value
    pct_riesgo = round((valor_riesgo / total_patrimonio * 100) if total_patrimonio > 0 else 0, 2)
    liquidez_value = round(df[df['tipo_norm'] == 'efectivo']['valor_mercado'].sum(), 2)
    
    # Calculate Runway & Savings Rate (Make them optional and 0 if no data)
    flow_data = get_financial_flow(None) 
    forecast = flow_data.get('forecast', {})
    avg_total_expense = forecast.get('weighted_avg_expense', 0) 
    avg_income = forecast.get('avg_income', 0)
    
    runway_months = round((liquidez_value / avg_total_expense) if avg_total_expense > 0 else 0, 2)
    savings_rate = round(((avg_income - avg_total_expense) / avg_income * 100) if avg_income > 0 else 0, 2)
    
    df.sort_values(by='valor_mercado', ascending=False, inplace=True)
    return {
        'total_patrimonio': total_patrimonio, 
        'total_inversion': total_inversion,
        'beneficio_total_abs': beneficio_total_abs,
        'equity_value': equity_value, 
        'stable_value': round(total_patrimonio - equity_value, 2), 
        'rentabilidad_total': round(((total_patrimonio - total_inversion) / total_inversion * 100) if total_inversion > 0 else 0, 2), 
        'pct_riesgo': pct_riesgo, 
        'liquidez': liquidez_value,
        'runway_months': runway_months,
        'savings_rate': savings_rate,
        'df_cartera': df
    }

def fill_missing_months(df_grouped):
    if df_grouped.empty: return df_grouped
    min_date = df_grouped['periodo'].min()
    max_date = df_grouped['periodo'].max()
    full_range = pd.period_range(start=min_date, end=max_date, freq='M')
    df_grouped = df_grouped.set_index('periodo').reindex(full_range, fill_value=0).reset_index()
    df_grouped.rename(columns={'index': 'periodo'}, inplace=True)
    df_grouped['periodo'] = df_grouped['periodo'].astype(str)
    return df_grouped

def get_financial_flow(portfolio_summary=None):
    _, _, ingresos, gastos, _ = load_data()
    if ingresos is None: return {}, {}
    
    # --- 1. PREPARE DATA ---
    today_date = datetime.now()
    
    # Filter for Charts (Only up to current month)
    ingresos_chart = ingresos[ingresos['fecha'] <= today_date].copy()
    gastos_chart = gastos[gastos['fecha'] <= today_date].copy()
    
    # Aggregation for Charts (Aligned)
    ing_m_raw = ingresos_chart.groupby('periodo')['cantidad'].sum().reset_index()
    gas_m_raw = gastos_chart.groupby('periodo')['cantidad'].sum().reset_index()
    
    # Ensure same range for both to allow combined charting
    all_periods = sorted(list(set(ing_m_raw['periodo']) | set(gas_m_raw['periodo'])))
    if all_periods:
        min_p, max_p = all_periods[0], all_periods[-1]
        full_range = pd.period_range(start=min_p, end=max_p, freq='M').astype(str)
        ing_m_chart = ing_m_raw.set_index('periodo').reindex(full_range, fill_value=0).reset_index().rename(columns={'index': 'periodo'})
        gas_total_m_chart = gas_m_raw.set_index('periodo').reindex(full_range, fill_value=0).reset_index().rename(columns={'index': 'periodo'})
    else:
        ing_m_chart = ing_m_raw
        gas_total_m_chart = gas_m_raw

    # --- 2. STATISTICAL ANOMALY DETECTION (Moving Average Approach) ---
    # We identify "extraordinary" expenses using a 12-month rolling window to adapt to current lifestyle.
    if not gastos.empty:
        # Sort by date for proper time series analysis
        df_sorted = gastos.sort_values('fecha').copy()
        
        # Calculate stats per category using a rolling window of 12 months (where possible)
        # For simplicity and given the frequency of use, we'll use the last 12 entries per category 
        # as a proxy for the 'current' behavior.
        def is_anomaly(row):
            cat_mask = df_sorted['categoria'] == row['categoria']
            # Get historical data for this category UP TO this row's date
            cat_history = df_sorted[cat_mask & (df_sorted['fecha'] < row['fecha'])].tail(12)
            
            if len(cat_history) < 3:
                # Fallback for new categories or very few entries
                return row['cantidad'] > 500
                
            mean = cat_history['cantidad'].mean()
            std = cat_history['cantidad'].std()
            
            # Threshold: Mean + 1.5 * StdDev
            threshold = mean + (1.5 * (std if pd.notnull(std) else 0))
            return row['cantidad'] > threshold

        gastos['is_extraordinary'] = gastos.apply(is_anomaly, axis=1)
        
        gas_rec = gastos[~gastos['is_extraordinary']]
        gas_extra = gastos[gastos['is_extraordinary']]
    else:
        gas_rec = pd.DataFrame(columns=['periodo', 'cantidad'])
        gas_extra = pd.DataFrame(columns=['periodo', 'cantidad'])
        
    gas_rec_m = fill_missing_months(gas_rec.groupby('periodo')['cantidad'].sum().reset_index())
    gas_extra_m = fill_missing_months(gas_extra.groupby('periodo')['cantidad'].sum().reset_index())

    # Averages for Forecast (Using last 12 months for better adaptation)
    window_stats = 12
    avg_income = ing_m_chart.tail(window_stats)['cantidad'].mean() if not ing_m_chart.empty else 0
    avg_expense_rec = gas_rec_m.tail(window_stats)['cantidad'].mean() if not gas_rec_m.empty else 0
    
    # Extraordinary expenses: Prorated based on the last 12 months of anomalies
    avg_expense_extra_prorated = (gas_extra_m.tail(window_stats)['cantidad'].sum() / 12) if not gas_extra_m.empty else 0

    
    # Real expected monthly expense
    weighted_avg_expense = avg_expense_rec + avg_expense_extra_prorated
    
    monthly_net_flow_base = avg_income - weighted_avg_expense
    monthly_net_flow_pessimistic = avg_income - (weighted_avg_expense * 1.20) # 20% buffer
    
    months = 6
    current_equity = portfolio_summary.get('equity_value', 0) if portfolio_summary else 0
    current_stable = portfolio_summary.get('stable_value', 0) if portfolio_summary else 0
    
    future_nw_pessimistic = current_stable + (current_equity * 0.90) + (monthly_net_flow_pessimistic * months)
    future_nw_realistic = current_stable + (current_equity * 1.035) + (monthly_net_flow_base * months)
    future_nw_optimistic = current_stable + (current_equity * 1.10) + (monthly_net_flow_base * months)

    today = datetime.now()
    eoy_year = today.year
    months_to_eoy = 12 - today.month
    if months_to_eoy < 0: months_to_eoy = 0
    
    rate_real_monthly = 0.035 / 6
    rate_opt_monthly = 0.10 / 6
    
    nw_pessimistic_eoy = current_stable + (current_equity * 0.90) + (monthly_net_flow_pessimistic * months_to_eoy)
    nw_realistic_eoy = current_stable + (current_equity * (1 + rate_real_monthly * months_to_eoy)) + (monthly_net_flow_base * months_to_eoy)
    nw_optimistic_eoy = current_stable + (current_equity * (1 + rate_opt_monthly * months_to_eoy)) + (monthly_net_flow_base * months_to_eoy)

    return {
        'ingresos_ts': ing_m_chart, 
        'gastos_rec_ts': gas_total_m_chart, 
        'forecast': {
            'avg_income': round(avg_income, 2),
            'avg_expense_rec': round(avg_expense_rec, 2),
            'avg_expense_extra_prorated': round(avg_expense_extra_prorated, 2),
            'weighted_avg_expense': round(weighted_avg_expense, 2),
            'net_flow': round(monthly_net_flow_base, 2),
            'months_6': months,
            'months_eoy': months_to_eoy,
            'eoy_year': eoy_year,
            'scenarios_6m': {
                'pessimistic': round(future_nw_pessimistic, 2),
                'realistic': round(future_nw_realistic, 2),
                'optimistic': round(future_nw_optimistic, 2)
            },
            'scenarios_eoy': {
                'pessimistic': round(nw_pessimistic_eoy, 2),
                'realistic': round(nw_realistic_eoy, 2),
                'optimistic': round(nw_optimistic_eoy, 2)
            }
        }
    }

def get_invested_capital_history():
    """Calculates the history of invested capital (cost basis) over time."""
    _, _, _, _, aportaciones = load_data()
    if aportaciones.empty: return pd.DataFrame(columns=['periodo', 'invertido_acumulado'])
    
    # 1. Process contributions and initial state from aportaciones
    df_ops = aportaciones.copy()
    df_ops['fecha'] = pd.to_datetime(df_ops['fecha'])
    df_ops = df_ops.sort_values('fecha')
    
    # Calculate net flow per operation
    def calc_flow(row):
        tipo = str(row['tipo']).upper().strip()
        if tipo == 'INICIAL' or tipo == 'COMPRA': return row['cantidad_dinero']
        if tipo == 'VENTA': return -row['cantidad_dinero']
        return 0
        
    df_ops['flujo'] = df_ops.apply(calc_flow, axis=1)
    
    # Group by month
    monthly_flow = df_ops.groupby(df_ops['fecha'].dt.to_period('M'))['flujo'].sum().reset_index()
    monthly_flow['periodo'] = monthly_flow['fecha'].astype(str)
    
    # Cumulative sum
    monthly_flow['invertido_acumulado'] = monthly_flow['flujo'].cumsum()
    
    return monthly_flow.set_index('periodo')['invertido_acumulado'].to_dict()

def get_monthly_cashflow_detail(periodo=None, window=1):
    """
    Returns detailed income and expense breakdown for a specific month or a window of months.
    If window > 1, it aggregates the 'window' months ending at 'periodo'.
    """
    _, _, ingresos, gastos, _ = load_data()
    
    if ingresos is None or gastos is None:
        return {'periodo': periodo, 'ingresos': [], 'gastos': [], 'neto': 0}
        
    if periodo is None:
        all_dates = pd.concat([ingresos['fecha'], gastos['fecha']])
        if all_dates.empty:
            return {'periodo': 'N/A', 'ingresos': [], 'gastos': [], 'neto': 0}
        periodo_dt = all_dates.dt.to_period('M').max()
        periodo = periodo_dt.strftime('%Y-%m')
    else:
        periodo_dt = pd.Period(periodo, freq='M')

    # Calculate the start period based on window
    start_period_dt = periodo_dt - (int(window) - 1)
    
    # Filter by period range
    mask_ing = (ingresos['periodo'] >= start_period_dt) & (ingresos['periodo'] <= periodo_dt)
    mask_gas = (gastos['periodo'] >= start_period_dt) & (gastos['periodo'] <= periodo_dt)
    
    df_ing = ingresos[mask_ing].copy()
    df_gas = gastos[mask_gas].copy()
    
    # Label for the UI
    display_period = periodo if int(window) == 1 else f"Últimos {window} meses (hasta {periodo})"

    # Aggregate by category/concept
    ing_grouped = df_ing.groupby('concepto')['cantidad'].sum().reset_index().to_dict('records')
    gas_col = 'categoria' if 'categoria' in df_gas.columns else 'concepto'
    gas_grouped = df_gas.groupby(gas_col)['cantidad'].sum().reset_index().rename(columns={gas_col: 'name', 'cantidad': 'value'}).to_dict('records')
    
    # Raw data for drill-down
    df_gas['fecha_str'] = df_gas['fecha'].dt.strftime('%Y-%m-%d')
    gas_raw = df_gas[['fecha_str', gas_col, 'concepto', 'cantidad']].rename(columns={gas_col: 'categoria'}).to_dict('records')

    # Format for ECharts
    ing_data = [{'name': d['concepto'], 'value': round(d['cantidad'], 2)} for d in ing_grouped]
    gas_data = [{'name': d['name'], 'value': round(d['value'], 2)} for d in gas_grouped]
    
    total_ing = sum(d['value'] for d in ing_data)
    total_gas = sum(d['value'] for d in gas_data)
    
    return {
        'periodo': display_period,
        'raw_periodo': periodo,
        'ingresos': ing_data,
        'gastos': gas_data,
        'gastos_raw': gas_raw,
        'total_ing': round(total_ing, 2),
        'total_gas': round(total_gas, 2),
        'neto': round(total_ing - total_gas, 2)
    }

def get_sankey_data(periodo=None, window=1):
    """Generates nodes and links for a Sankey diagram for a specific month or window."""
    detail = get_monthly_cashflow_detail(periodo, window)
    if not detail['ingresos'] and not detail['gastos']:
        return {'nodes': [], 'links': []}

    # Load investment data for the period
    _, _, _, _, aportaciones = load_data()
    investments_in_period = 0.0
    investments_by_asset = []

    if not aportaciones.empty:
        # Filter aportaciones by period
        if periodo:
            # Handle window
            p_end = pd.Period(periodo, freq='M')
            p_start = p_end - (int(window) - 1)
            mask = (aportaciones['fecha'].dt.to_period('M') >= p_start) & (aportaciones['fecha'].dt.to_period('M') <= p_end)
            df_inv = aportaciones[mask & (aportaciones['tipo'] == 'COMPRA')].copy()
            
            if not df_inv.empty:
                investments_in_period = df_inv['cantidad_dinero'].sum()
                inv_grouped = df_inv.groupby('id_activo')['cantidad_dinero'].sum().reset_index()
                investments_by_asset = inv_grouped.to_dict('records')

    nodes = []
    links = []
    node_names = set()

    def add_node(name):
        if name not in node_names:
            nodes.append({'name': name})
            node_names.add(name)

    # Core Nodes
    main_income_node = "TOTAL INGRESOS"
    main_expense_node = "TOTAL GASTOS"
    pool_node = "TOTAL DISPONIBLE"
    savings_node = "REMANENTE BANCO"
    invested_node = "INVERTIDO (ESTRATEGIA)"

    add_node(main_income_node)
    add_node(pool_node)
    
    # 1. Income Sources -> Total Income -> Pool
    for ing in detail['ingresos']:
        source = ing['name'].upper()
        add_node(source)
        links.append({'source': source, 'target': main_income_node, 'value': round(ing['value'], 2)})

    links.append({'source': main_income_node, 'target': pool_node, 'value': round(detail['total_ing'], 2)})

    # 2. Pool -> Total Expenses
    if detail['total_gas'] > 0:
        add_node(main_expense_node)
        val_to_expenses = min(detail['total_ing'], detail['total_gas'])
        links.append({'source': pool_node, 'target': main_expense_node, 'value': round(val_to_expenses, 2)})

    # 3. Pool -> Investments (Real flows from aportaciones)
    if investments_in_period > 0:
        add_node(invested_node)
        links.append({'source': pool_node, 'target': invested_node, 'value': round(investments_in_period, 2)})
        
        for inv in investments_by_asset:
            asset_node = f"INV: {inv['id_activo']}"
            add_node(asset_node)
            links.append({'source': invested_node, 'target': asset_node, 'value': round(inv['cantidad_dinero'], 2)})

    # 4. Pool -> Savings (Residual after expenses AND real investments)
    # Note: net_flow already subtracted total_gas. We subtract what was actually invested too.
    remanente = detail['neto'] - investments_in_period
    if remanente > 0:
        add_node(savings_node)
        links.append({'source': pool_node, 'target': savings_node, 'value': round(remanente, 2)})
    elif remanente < 0:
        # If we invested more than this month's net flow (drew from old savings)
        add_node("AHORRO PREVIO")
        links.append({'source': "AHORRO PREVIO", 'target': pool_node, 'value': round(abs(remanente), 2)})

    # 5. Total Expenses -> Categories
    for gas in detail['gastos']:
        target = gas['name'].upper()
        add_node(target)
        links.append({'source': main_expense_node, 'target': target, 'value': round(gas['value'], 2)})

    return {'nodes': nodes, 'links': links}

def create_charts(portfolio, flow_data):
    charts = {}
    grid_style = {'left': '3%', 'right': '4%', 'bottom': '3%', 'top': '10%', 'containLabel': True}
    
    # Common tooltip formatter
    tooltip_formatter = "{b0}<br />{c0} €"

    # ... (Ingresos, Gastos, Allocation, Performance logic remains) ...
    if 'ingresos_ts' in flow_data:
        df = flow_data['ingresos_ts']
        charts['ingresos'] = {
            'tooltip': {'trigger': 'axis', 'formatter': tooltip_formatter},
            'grid': grid_style,
            'xAxis': {'type': 'category', 'boundaryGap': False, 'data': df['periodo'].tolist(), 'axisLabel': {'color': '#94a3b8'}},
            'yAxis': {'type': 'value', 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}},
            'series': [{'name': 'Ingresos', 'type': 'line', 'smooth': True, 'data': df['cantidad'].tolist(), 'itemStyle': {'color': '#10b981'}, 'areaStyle': {'color': 'rgba(16, 185, 129, 0.1)'}}]
        }

    if 'gastos_rec_ts' in flow_data:
        df = flow_data['gastos_rec_ts']
        charts['gastos'] = {
            'tooltip': {'trigger': 'axis', 'formatter': tooltip_formatter},
            'grid': grid_style,
            'xAxis': {'type': 'category', 'boundaryGap': False, 'data': df['periodo'].tolist(), 'axisLabel': {'color': '#94a3b8'}},
            'yAxis': {'type': 'value', 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}},
            'series': [{'name': 'Gastos', 'type': 'line', 'smooth': True, 'data': df['cantidad'].tolist(), 'itemStyle': {'color': '#ef4444'}, 'areaStyle': {'color': 'rgba(239, 68, 68, 0.1)'}}]
        }

    if 'df_cartera' in portfolio:
        df = portfolio['df_cartera']
        df_pos = df[df['valor_mercado'] > 0]
        data_structure = []
        for tipo, group in df_pos.groupby('tipo'):
            children = []
            for _, row in group.iterrows():
                children.append({'name': row['id_activo'], 'value': round(row['valor_mercado'], 2)})
            data_structure.append({'name': tipo, 'children': children})
        charts['allocation'] = {
            'tooltip': {'trigger': 'item'},
            'grid': {'top': 0, 'bottom': 0, 'left': 0, 'right': 0},
            'series': {'type': 'sunburst', 'data': data_structure, 'radius': ['0%', '100%'], 'center': ['50%', '50%'], 'itemStyle': {'borderWidth': 1, 'borderColor': '#fff'}, 'label': {'rotate': 'radial', 'minAngle': 5}}
        }
        df_perf = df.sort_values('plusvalia', ascending=True)
        series_data = []
        for _, row in df_perf.iterrows():
            series_data.append({'value': round(row['plusvalia'], 2), 'itemStyle': {'color': '#34d399' if row['plusvalia'] >= 0 else '#f87171'}, 'rentabilidad': round(row['rentabilidad'], 2), 'valor_mercado': round(row['valor_mercado'], 2), 'nombre_completo': row['nombre']})
        charts['performance'] = {
            'grid': {'left': '1%', 'right': '4%', 'bottom': '3%', 'top': '0%', 'containLabel': True},
            'xAxis': {'type': 'value', 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}},
            'yAxis': {'type': 'category', 'data': df_perf['nombre'].tolist(), 'axisLabel': {'color': '#475569', 'width': 160, 'overflow': 'truncate'}},
            'series': [{'type': 'bar', 'data': series_data, 'barWidth': '12px', 'itemStyle': {'borderRadius': 6}}]
        }
        
    history_data = get_portfolio_history_chart_data()
    # Merge invested capital data
    invested_data = get_invested_capital_history()
    
    if history_data:
        # Align dates: history_data['dates'] is the master timeline (daily prices)
        # We need to map invested capital to these dates
        
        invested_series = []
        current_inv = 0
        sorted_inv_dates = sorted(invested_data.keys())
        
        # Get initial invested (if dates start before history)
        if sorted_inv_dates:
             current_inv = invested_data[sorted_inv_dates[0]]

        for date in history_data['dates']:
            # If we have an exact match or update in invested_data, update current_inv
            # Simple forward fill logic
            # Find the latest date in invested_data <= date
            # Since history_data dates are strings YYYY-MM-DD
            
            # Efficient enough for small datasets:
            valid_dates = [d for d in sorted_inv_dates if d <= date]
            if valid_dates:
                current_inv = invested_data[valid_dates[-1]]
            
            invested_series.append(round(current_inv, 2))
            
        # Calculate Profit (Value - Invested)
        profit_series = []
        for val, inv in zip(history_data['values'], invested_series):
            profit_series.append(round(max(0, val - inv), 2))

        charts['history'] = {
            'tooltip': {'trigger': 'axis', 'formatter': '{b0}<br />Total: {c0} €'}, # Simplified tooltip
            'legend': {'data': ['Capital Invertido', 'Plusvalía'], 'bottom': 0},
            'grid': grid_style,
            'xAxis': {'type': 'category', 'boundaryGap': False, 'data': history_data['dates'], 'axisLabel': {'color': '#94a3b8'}},
            'yAxis': {'type': 'value', 'scale': True, 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}},
            'series': [
                {
                    'name': 'Capital Invertido',
                    'type': 'line',
                    'stack': 'Total',
                    'smooth': True,
                    'lineStyle': {'width': 0},
                    'showSymbol': False,
                    'areaStyle': {'opacity': 0.8, 'color': '#94a3b8'}, # Gray for base capital
                    'itemStyle': {'color': '#94a3b8'},
                    'data': invested_series
                },
                {
                    'name': 'Plusvalía',
                    'type': 'line',
                    'stack': 'Total',
                    'smooth': True,
                    'lineStyle': {'width': 0},
                    'showSymbol': False,
                    'areaStyle': {'opacity': 0.8, 'color': '#10b981'}, # Green for profit
                    'itemStyle': {'color': '#10b981'},
                    'data': profit_series
                }
            ]
        }
    
    # Combined Cashflow Chart (Income vs Expenses vs Net)
    if 'ingresos_ts' in flow_data and 'gastos_rec_ts' in flow_data:
        ing_df = flow_data['ingresos_ts']
        gas_df = flow_data['gastos_rec_ts']
        
        # Calculate net flow
        net_flow_data = (ing_df['cantidad'] - gas_df['cantidad']).round(2).tolist()
        
        charts['cashflow'] = {
            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
            'legend': {'data': ['Ingresos', 'Gastos', 'Flujo Neto'], 'bottom': 0},
            'grid': grid_style,
            'xAxis': {
                'type': 'category', 
                'data': ing_df['periodo'].tolist(), 
                'axisLabel': {'color': '#94a3b8'}
            },
            'yAxis': {
                'type': 'value', 
                'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#f1f5f9'}}
            },
            'series': [
                {
                    'name': 'Ingresos', 
                    'type': 'bar', 
                    'barGap': '0%',
                    'data': ing_df['cantidad'].tolist(), 
                    'itemStyle': {'color': '#10b981', 'opacity': 0.7, 'borderRadius': [4, 4, 0, 0]}
                },
                {
                    'name': 'Gastos', 
                    'type': 'bar', 
                    'data': gas_df['cantidad'].tolist(), 
                    'itemStyle': {'color': '#ef4444', 'opacity': 0.7, 'borderRadius': [4, 4, 0, 0]}
                },
                {
                    'name': 'Flujo Neto', 
                    'type': 'line', 
                    'smooth': True, 
                    'data': net_flow_data, 
                    'itemStyle': {'color': '#3b82f6'}, 
                    'lineStyle': {'width': 3},
                    'symbolSize': 8
                }
            ]
        }
        
    return charts

def get_expense_breakdown():
    _, _, _, gastos, _ = load_data()
    if gastos is None or gastos.empty: return []
    
    today_date = datetime.now()
    # Filter expenses for the last 6 months
    start_date = today_date - pd.DateOffset(months=6)
    
    # Filter expenses: > start_date AND <= today_date
    df = gastos[(gastos['fecha'] > start_date) & (gastos['fecha'] <= today_date)].copy()
    
    if df.empty: return []
    
    # Calculate number of distinct months in the dataset
    num_months = df['periodo'].nunique()
    if num_months < 1: num_months = 1
    
    # Group by category
    if 'categoria' in df.columns:
        grouped = df.groupby('categoria')['cantidad'].sum().reset_index()
        # Calculate monthly average
        grouped['cantidad'] = grouped['cantidad'] / num_months
        
        # Sort for better visualization
        grouped.sort_values('cantidad', ascending=False, inplace=True)
        
        data = []
        for _, row in grouped.iterrows():
            data.append({
                'name': row['categoria'],
                'value': round(row['cantidad'], 2)
            })
        return data
    else:
        return []

def get_upcoming_expenses():
    _, _, _, gastos, _ = load_data()
    if gastos is None or gastos.empty: return []
    
    today_date = datetime.now()
    # Filter expenses strictly after today
    df = gastos[gastos['fecha'] > today_date].copy()
    
    if df.empty: return []
    
    df.sort_values('fecha', ascending=True, inplace=True)
    
    upcoming = []
    for _, row in df.iterrows():
        upcoming.append({
            'fecha': row['fecha'].strftime('%Y-%m-%d'),
            'concepto': row['concepto'],
            'cantidad': row['cantidad'],
            'categoria': row['categoria']
        })
    return upcoming