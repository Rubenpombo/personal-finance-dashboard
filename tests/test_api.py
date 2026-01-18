import yfinance as yf
import pandas as pd
import sys
import os

def test_assets_connectivity():
    """Itera sobre los activos del CSV y verifica la conexión con Yahoo Finance."""
    csv_path = "data/activos.csv"
    
    if not os.path.exists(csv_path):
        print(f"ERROR: No se encuentra el archivo {csv_path}")
        return False

    try:
        df_activos = pd.read_csv(csv_path)
    except Exception as e:
        print(f"ERROR: No se pudo leer el CSV de activos: {e}")
        return False

    # Filtramos solo los que deben consultarse vía Yahoo
    activos_yahoo = df_activos[df_activos['fuente'].str.lower() == 'yahoo']
    
    if activos_yahoo.empty:
        print("AVISO: No hay activos configurados con fuente 'yahoo'. Test omitido.")
        return True

    success = True
    print(f"--- Validando {len(activos_yahoo)} activos en Yahoo Finance ---")
    
    for _, row in activos_yahoo.iterrows():
        identificador = row['isin'] # Usamos la columna isin como ticker
        nombre = row['nombre']
        
        try:
            ticker = yf.Ticker(identificador)
            # Intentamos obtener el precio (history es más fiable que .info)
            hist = ticker.history(period="1d")
            
            if not hist.empty:
                precio = hist['Close'].iloc[-1]
                print(f"[OK] {nombre} ({identificador}): {precio:.2f}")
            else:
                print(f"[FALLO] {nombre} ({identificador}): No se encontraron datos.")
                success = False
        except Exception as e:
            print(f"[ERROR] {nombre} ({identificador}): {e}")
            success = False
            
    return success

if __name__ == "__main__":
    if test_assets_connectivity():
        print("--- Todos los activos de Yahoo Finance son válidos ---")
        sys.exit(0)
    else:
        print("--- Error de validación en uno o más activos ---")
        sys.exit(1)