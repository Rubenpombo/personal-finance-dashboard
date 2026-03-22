from flask import Flask, render_template, redirect, url_for, flash
import logic
import pandas as pd

app = Flask(__name__)
app.secret_key = 'secure_key_dashboard'

@app.route('/')
def index():
    portfolio = logic.get_portfolio_summary()
    flow_data = logic.get_financial_flow(portfolio_summary=portfolio) 
    charts = logic.create_charts(portfolio, flow_data)
    
    # Available periods for the selector
    ing_ts = flow_data.get('ingresos_ts', pd.DataFrame())
    gas_ts = flow_data.get('gastos_rec_ts', pd.DataFrame())
    
    available_periods = []
    if not ing_ts.empty or not gas_ts.empty:
        p_list = sorted(list(set(ing_ts['periodo'].tolist()) | set(gas_ts['periodo'].tolist())), reverse=True)
        available_periods = p_list
    
    # Monthly detail for the latest month by default
    monthly_detail = logic.get_monthly_cashflow_detail()
    sankey_data = logic.get_sankey_data()

    # Get monthly investment history for the table
    _, _, _, _, aportaciones = logic.load_data()
    if not aportaciones.empty:
        # Group by month and sum quantity
        monthly_inv = aportaciones.groupby(aportaciones['fecha'].dt.to_period('M'))['cantidad_dinero'].sum().reset_index()
        monthly_inv['periodo'] = monthly_inv['fecha'].astype(str)
        monthly_inv = monthly_inv.sort_values('fecha', ascending=False).head(12) # Last 12 months
        monthly_investments = monthly_inv.to_dict('records')
    else:
        monthly_investments = []

    forecast = flow_data.get('forecast', {})
    
    return render_template('dashboard.html', 
                           portfolio=portfolio, 
                           forecast=forecast,
                           charts=charts,
                           monthly_investments=monthly_investments,
                           available_periods=available_periods,
                           monthly_detail=monthly_detail,
                           sankey_data=sankey_data)

@app.route('/api/monthly-detail/<period>')
def api_monthly_detail(period):
    from flask import request
    window = request.args.get('window', 1, type=int)
    detail = logic.get_monthly_cashflow_detail(periodo=period, window=window)
    sankey = logic.get_sankey_data(periodo=period, window=window)
    return {'detail': detail, 'sankey': sankey}

@app.route('/detail')
def detail():
    portfolio = logic.get_portfolio_summary()
    expenses_data = logic.get_expense_breakdown()
    upcoming_expenses = logic.get_upcoming_expenses()
    
    return render_template('detail.html', 
                           portfolio=portfolio,
                           expenses_data=expenses_data,
                           upcoming_expenses=upcoming_expenses)

@app.route('/update-prices', methods=['POST'])
def update_prices():
    success, message = logic.refresh_market_data()
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('index'))

@app.route('/data')
def data_view():
    activos, cartera, ingresos, gastos, aportaciones = logic.load_data()
    
    def df_to_html(df):
        if df is None or df.empty: return None
        return df.to_html(classes="table table-striped table-sm", index=False, float_format=lambda x: "{:,.2f}".format(x))

    tables = {
        'Cartera': df_to_html(logic.get_portfolio_summary().get('df_cartera')),
        'Ingresos': df_to_html(ingresos),
        'Gastos': df_to_html(gastos)
    }
    return render_template('data.html', tables=tables)

if __name__ == '__main__':
    app.run(debug=True, port=5000)