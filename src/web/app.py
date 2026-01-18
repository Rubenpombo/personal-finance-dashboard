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
    
    forecast = flow_data.get('forecast', {})
    
    return render_template('dashboard.html', 
                           portfolio=portfolio, 
                           forecast=forecast,
                           charts=charts)

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