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
    
    def df_to_html(df, sort_col=None):
        if df is None or df.empty: return None
        if sort_col and sort_col in df.columns:
            df = df.sort_values(by=sort_col, ascending=False)
        return df.to_html(classes="table table-striped table-sm", index=False, float_format=lambda x: "{:,.2f}".format(x))

    tables = {
        'Cartera': df_to_html(logic.get_portfolio_summary().get('df_cartera')),
        'Aportaciones': df_to_html(aportaciones, sort_col='fecha'),
        'Ingresos': df_to_html(ingresos, sort_col='fecha'),
        'Gastos': df_to_html(gastos, sort_col='fecha')
    }
    
    # Assets for the dropdown
    assets_list = []
    if activos is not None:
        assets_list = activos[['id', 'nombre']].to_dict('records')
        
    return render_template('data.html', 
                           tables=tables, 
                           assets=assets_list, 
                           now_date=pd.Timestamp.now().strftime('%Y-%m-%d'))

@app.route('/add-contribution', methods=['POST'])
def add_contribution():
    from flask import request
    data = {
        'fecha': request.form.get('fecha'),
        'tipo': request.form.get('tipo'),
        'id_activo': request.form.get('id_activo'),
        'cantidad_dinero': request.form.get('cantidad_dinero'),
        'titulos': request.form.get('titulos'),
        'precio_titulo': request.form.get('precio_titulo')
    }
    notas = request.form.get('notas') or 'Manual'
    
    success, message, is_duplicate = logic.add_contribution(data, notas=notas)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('data_view'))

@app.route('/add-transfer', methods=['POST'])
def add_transfer():
    from flask import request
    data = {
        'fecha': request.form.get('fecha'),
        'id_origen': request.form.get('id_origen'),
        'id_destino': request.form.get('id_destino'),
        'cantidad_dinero': request.form.get('cantidad_dinero'),
        'titulos_origen': request.form.get('titulos_origen'),
        'precio_origen': request.form.get('precio_origen'),
        'titulos_destino': request.form.get('titulos_destino'),
        'precio_destino': request.form.get('precio_destino'),
        'notas': request.form.get('notas')
    }
    
    success, message = logic.add_transfer(data)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
        
    return redirect(url_for('data_view'))

@app.route('/import-myinvestor', methods=['POST'])
def import_myinvestor():
    from flask import request, session
    
    # Check if this is a confirmation of a preview
    if request.form.get('confirm') == 'true':
        data = {
            'fecha': request.form.get('fecha'),
            'tipo': request.form.get('tipo'),
            'id_activo': request.form.get('id_activo'),
            'cantidad_dinero': request.form.get('cantidad_dinero'),
            'titulos': request.form.get('titulos'),
            'precio_titulo': request.form.get('precio_titulo')
        }
        force = request.form.get('force') == 'true'
        success, message, is_duplicate = logic.import_myinvestor_data(data, force=force)
        
        if success:
            flash(message, 'success')
            session.pop('import_preview', None)
        elif is_duplicate:
            flash(message, 'warning')
            session['import_preview'] = data # Keep preview to show the 'Force' button
            session['import_is_duplicate'] = True
        else:
            flash(message, 'danger')
        return redirect(url_for('data_view'))

    # Initial parsing / Preview
    subject = request.form.get('subject')
    if not subject:
        flash("El asunto está vacío", "warning")
        return redirect(url_for('data_view'))
        
    data, error = logic.parse_myinvestor_subject(subject)
    if error:
        flash(error, 'danger')
        return redirect(url_for('data_view'))
    
    # Save to session to show preview in data_view
    session['import_preview'] = data
    session.pop('import_is_duplicate', None)
    return redirect(url_for('data_view'))

@app.route('/cancel-import')
def cancel_import():
    from flask import session
    session.pop('import_preview', None)
    session.pop('import_is_duplicate', None)
    return redirect(url_for('data_view'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)