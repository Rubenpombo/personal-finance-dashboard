import pandas as pd
import json
import os
import market_data
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
PRICES_FILE = os.path.join(DATA_DIR, 'latest_prices.json')
HISTORY_FILE = os.path.join(DATA_DIR, 'precios_historicos.csv')

def rebuild_portfolio():
    """Regenerates cartera.csv based on saldo_inicial.csv and aportaciones.csv"""
    try:
        # 1. Load Initial State
        initial_path = os.path.join(DATA_DIR, "saldo_inicial.csv")
        if not os.path.exists(initial_path):
            print("No saldo_inicial.csv found. Creating empty portfolio.")
            return

        df_portfolio = pd.read_csv(initial_path)
        # Convert to dictionary for easier processing: {id_activo: {'participaciones': x, 'precio_medio': y}}
        portfolio = {}
        for _, row in df_portfolio.iterrows():
            portfolio[row['id_activo']] = {
                'participaciones': float(row['participaciones']),
                'precio_medio_compra': float(row['precio_medio_compra'])
            }

        # 2. Process Aportaciones
        aportaciones_path = os.path.join(DATA_DIR, "aportaciones.csv")
        if os.path.exists(aportaciones_path):
            df_ops = pd.read_csv(aportaciones_path)
            if not df_ops.empty and 'fecha' in df_ops.columns:
                df_ops['fecha'] = pd.to_datetime(df_ops['fecha'])
                df_ops.sort_values('fecha', inplace=True)

                for _, op in df_ops.iterrows():
                    asset_id = op['id_activo']
                    tipo = str(op['tipo']).upper().strip()
                    titulos_op = float(op['titulos']) if pd.notnull(op['titulos']) else 0.0
                    cantidad_op = float(op['cantidad_dinero']) if pd.notnull(op['cantidad_dinero']) else 0.0
                    precio_op = float(op['precio_titulo']) if pd.notnull(op['precio_titulo']) else 0.0

                    # Calculate price if missing but we have amount and shares
                    if precio_op == 0 and titulos_op > 0 and cantidad_op > 0:
                        precio_op = cantidad_op / titulos_op

                    if asset_id not in portfolio:
                        portfolio[asset_id] = {'participaciones': 0.0, 'precio_medio_compra': 0.0}

                    current = portfolio[asset_id]

                    if tipo == 'COMPRA':
                        total_cost_old = current['participaciones'] * current['precio_medio_compra']
                        total_cost_new = titulos_op * precio_op
                        new_shares = current['participaciones'] + titulos_op
                        
                        if new_shares > 0:
                            new_avg = (total_cost_old + total_cost_new) / new_shares
                            current['participaciones'] = new_shares
                            current['precio_medio_compra'] = new_avg
                            
                    elif tipo == 'VENTA':
                        current['participaciones'] = max(0.0, current['participaciones'] - titulos_op)
                        # Average price usually doesn't change on sell (FIFO/Weighted implies cost basis per share stays)
                        
                    elif tipo == 'AJUSTE_VALOR':
                        # For Cash or manual overrides. 'titulos' or 'cantidad_dinero' acts as the new balance.
                        # For cash, participaciones == currency units.
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
                'precio_medio_compra': round(data['precio_medio_compra'], 4)
            })
            
        df_final = pd.DataFrame(rows)
        # Ensure columns order
        df_final = df_final[['id_activo', 'participaciones', 'precio_medio_compra']]
        df_final.to_csv(os.path.join(DATA_DIR, "cartera.csv"), index=False)
        
    except Exception as e:
        print(f"Error rebuilding portfolio: {e}")

def load_data():
    # Ensure cartera is up to date before loading
    rebuild_portfolio()
    
    try:
        activos = pd.read_csv(os.path.join(DATA_DIR, "activos.csv"))
        cartera = pd.read_csv(os.path.join(DATA_DIR, "cartera.csv"))
        ingresos = pd.read_csv(os.path.join(DATA_DIR, "ingresos.csv"))
        
        # Load variable expenses
        gastos_path = os.path.join(DATA_DIR, "gastos_variables.csv")
        if os.path.exists(gastos_path):
            gastos = pd.read_csv(gastos_path)
        else:
            # Fallback for backward compatibility if user hasn't renamed yet
            gastos = pd.read_csv(os.path.join(DATA_DIR, "gastos.csv"))
            
        aportaciones = pd.read_csv(os.path.join(DATA_DIR, "aportaciones.csv"))

        # Convert dates for standard dataframes
        for df in [ingresos, gastos, aportaciones]:
            if not df.empty and 'fecha' in df.columns:
                df['fecha'] = pd.to_datetime(df['fecha'])
        
        # --- PROCESS RECURRENT EXPENSES ---
        recurrentes_path = os.path.join(DATA_DIR, "gastos_recurrentes.csv")
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
                            'concepto': row['concepto'],
                            'extraordinario': 'NO'
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
        
        return activos, cartera, ingresos, gastos, aportaciones
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
    if not os.path.exists(HISTORY_FILE): return None
    try:
        df_hist = pd.read_csv(HISTORY_FILE)
        cartera = pd.read_csv(os.path.join(DATA_DIR, "cartera.csv"))
        df_pivot = df_hist.pivot(index='fecha', columns='id_activo', values='precio').fillna(0)
        shares_map = cartera.set_index('id_activo')['participaciones'].to_dict()
        total_values = []
        dates = df_pivot.index.tolist()
        for date in dates:
            daily_total = 0
            for asset_id in df_pivot.columns:
                daily_total += df_pivot.at[date, asset_id] * shares_map.get(asset_id, 0)
            total_values.append(round(daily_total, 2))
        return {'dates': dates, 'values': total_values}
    except Exception as e:
        print(f"Error generating history chart: {e}")
        return None

def refresh_market_data():
    activos, _, _, _, _ = load_data()
    if activos is not None:
        new_prices = market_data.update_prices(activos)
        try:
            with open(PRICES_FILE, 'w') as f:
                json.dump(new_prices, f)
            save_price_history(new_prices)
            return True, "Precios actualizados e historial guardado."
        except Exception as e:
            return False, f"Error guardando precios: {e}"
    return False, "Error cargando activos."

def get_portfolio_summary():
    activos, cartera, ingresos, gastos, aportaciones = load_data()
    if activos is None: return {}
    prices = get_latest_prices()
    df = pd.merge(cartera, activos, left_on='id_activo', right_on='id', how='left')
    df['precio_actual'] = df['id_activo'].map(prices).fillna(0.0)
    df['valor_mercado'] = df['participaciones'] * df['precio_actual']
    df['coste_total'] = df['participaciones'] * df['precio_medio_compra']
    df['plusvalia'] = df['valor_mercado'] - df['coste_total']
    df['rentabilidad'] = df.apply(lambda row: (row['plusvalia'] / row['coste_total'] * 100) if row['coste_total'] != 0 else 0, axis=1)
    total_patrimonio = df['valor_mercado'].sum()
    total_inversion = df['coste_total'].sum()
    df['tipo_norm'] = df['tipo'].str.lower().str.strip()
    equity_mask = df['tipo_norm'].str.contains('variable') | df['tipo_norm'].str.contains('stock') | df['tipo_norm'].str.contains('acción')
    equity_value = df[equity_mask]['valor_mercado'].sum()
    valor_riesgo = equity_value
    pct_riesgo = (valor_riesgo / total_patrimonio * 100) if total_patrimonio > 0 else 0
    liquidez_value = df[df['tipo_norm'] == 'efectivo']['valor_mercado'].sum()
    
    # Calculate Runway & Savings Rate
    # Get averages from financial flow logic (reuse internal logic briefly or call helper)
    flow_data = get_financial_flow(None) # Pass None as portfolio not needed for averages
    forecast = flow_data.get('forecast', {})
    avg_total_expense = forecast.get('weighted_avg_expense', 0) 
    avg_income = forecast.get('avg_income', 0)
    
    runway_months = (liquidez_value / avg_total_expense) if avg_total_expense > 0 else 999.9
    savings_rate = ((avg_income - avg_total_expense) / avg_income * 100) if avg_income > 0 else 0
    
    df.sort_values(by='valor_mercado', ascending=False, inplace=True)
    return {
        'total_patrimonio': total_patrimonio, 
        'equity_value': equity_value, 
        'stable_value': total_patrimonio - equity_value, 
        'rentabilidad_total': ((total_patrimonio - total_inversion) / total_inversion * 100) if total_inversion > 0 else 0, 
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
    
    # Aggregation for Charts
    ing_m_chart = fill_missing_months(ingresos_chart.groupby('periodo')['cantidad'].sum().reset_index())
    gas_total_m_chart = fill_missing_months(gastos_chart.groupby('periodo')['cantidad'].sum().reset_index())

    # --- 2. FORECAST CALCULATION (Uses ALL data, including future) ---
    # Total Income (All time)
    ing_m_all = fill_missing_months(ingresos.groupby('periodo')['cantidad'].sum().reset_index())
    
    # Split Expenses (All time)
    if 'extraordinario' in gastos.columns:
        gastos['extraordinario_norm'] = gastos['extraordinario'].astype(str).str.upper().str.strip()
        gas_rec = gastos[gastos['extraordinario_norm'] == 'NO']
        gas_extra = gastos[gastos['extraordinario_norm'] != 'NO']
    else:
        gas_rec = gastos
        gas_extra = pd.DataFrame(columns=['periodo', 'cantidad'])
        
    gas_rec_m = fill_missing_months(gas_rec.groupby('periodo')['cantidad'].sum().reset_index())
    gas_extra_m = fill_missing_months(gas_extra.groupby('periodo')['cantidad'].sum().reset_index())

    # Averages
    # Regular expenses: last 6 months mean
    last_n_rec = 6
    avg_income = ing_m_all.tail(last_n_rec)['cantidad'].mean() if not ing_m_all.empty else 0
    avg_expense_rec = gas_rec_m.tail(last_n_rec)['cantidad'].mean() if not gas_rec_m.empty else 0
    
    # Extraordinary expenses: sum of last 12 months divided by 12 (prorated annual cost)
    last_n_extra = 12
    avg_expense_extra_prorated = (gas_extra_m.tail(last_n_extra)['cantidad'].sum() / 12) if not gas_extra_m.empty else 0
    
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
            'avg_income': avg_income,
            'avg_expense_rec': avg_expense_rec,
            'avg_expense_extra_prorated': avg_expense_extra_prorated,
            'weighted_avg_expense': weighted_avg_expense,
            'net_flow': monthly_net_flow_base,
            'months_6': months,
            'months_eoy': months_to_eoy,
            'eoy_year': eoy_year,
            'scenarios_6m': {
                'pessimistic': future_nw_pessimistic,
                'realistic': future_nw_realistic,
                'optimistic': future_nw_optimistic
            },
            'scenarios_eoy': {
                'pessimistic': nw_pessimistic_eoy,
                'realistic': nw_realistic_eoy,
                'optimistic': nw_optimistic_eoy
            }
        }
    }

def get_invested_capital_history():
    """Calculates the history of invested capital based on saldo_inicial + aportaciones."""
    try:
        # 1. Initial Capital (from saldo_inicial)
        initial_path = os.path.join(DATA_DIR, "saldo_inicial.csv")
        initial_capital = 0.0
        if os.path.exists(initial_path):
            df_init = pd.read_csv(initial_path)
            # Coste = participaciones * precio_medio_compra
            initial_capital = (df_init['participaciones'] * df_init['precio_medio_compra']).sum()

        # 2. Process Aportaciones cronologically
        history = {} # {date_str: capital}
        # Start with initial capital today (or from the past? We assume initial is the base)
        # To make it plotable, we need dates.
        # We will assume 'saldo_inicial' applies from the earliest date in aportaciones, or today if empty.
        
        current_capital = initial_capital
        
        aportaciones_path = os.path.join(DATA_DIR, "aportaciones.csv")
        ops = []
        if os.path.exists(aportaciones_path):
            df_ops = pd.read_csv(aportaciones_path)
            if not df_ops.empty:
                df_ops['fecha'] = pd.to_datetime(df_ops['fecha'])
                df_ops.sort_values('fecha', inplace=True)
                ops = df_ops.to_dict('records')

        # Create a timeline
        if not ops:
            return {datetime.now().strftime('%Y-%m-%d'): initial_capital}

        # We need a continuous daily series or at least points where it changed
        # Let's return just the change points, the chart can step-line it
        time_series = {}
        
        # Base date: slightly before first operation or today
        # For simplicity, let's just track the cumulative sum at each operation date
        
        for op in ops:
            date_str = op['fecha'].strftime('%Y-%m-%d')
            tipo = str(op['tipo']).upper().strip()
            amount = float(op['cantidad_dinero'])
            
            if tipo == 'COMPRA':
                current_capital += amount
            elif tipo == 'VENTA':
                # On sell, we remove the COST BASIS of the sold shares, not the sale amount (which includes profit)
                # But we don't track cost basis per transaction easily here without full replay.
                # Simplified: remove the sale amount (cash out) - this is 'Net Invested Capital'
                current_capital -= amount 
            elif tipo == 'AJUSTE_VALOR':
                pass # Adjustments to value (like cash update) don't necessarily mean capital injection, but...
                # If cash increases, it's usually income -> capital injection? 
                # Let's assume AJUSTE_VALOR in CASH is a capital movement for now.
                if 'CASH' in str(op['id_activo']).upper():
                     # This is hard. Let's ignore adjustments for 'Invested Capital' metric for now 
                     # to keep it strictly about "Money put into markets".
                     pass

            time_series[date_str] = current_capital
            
        return time_series
    except Exception as e:
        print(f"Error calculating invested history: {e}")
        return {}

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