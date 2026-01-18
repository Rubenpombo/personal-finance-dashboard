import warnings
# Suppress the pyarrow deprecation warning from pandas
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pandas")

import pandas as pd
import sys
import os

def check_integrity():
    print("--- Verificando integridad de datos ---")
    data_dir = "data"
    
    activos_path = os.path.join(data_dir, "activos.csv")
    aportaciones_path = os.path.join(data_dir, "aportaciones.csv")
    saldo_path = os.path.join(data_dir, "saldo_inicial.csv")
    
    if not os.path.exists(activos_path):
        print(f"ERROR CRÍTICO: No se encuentra {activos_path}")
        return False
        
    try:
        df_activos = pd.read_csv(activos_path)
        valid_ids = set(df_activos['id'].astype(str).str.strip().unique())
    except Exception as e:
        print(f"ERROR: No se pudo leer activos.csv: {e}")
        return False

    errors_found = False

    # Check Aportaciones
    if os.path.exists(aportaciones_path):
        try:
            df_ops = pd.read_csv(aportaciones_path)
            if not df_ops.empty:
                op_ids = set(df_ops['id_activo'].astype(str).str.strip().unique())
                diff = op_ids - valid_ids
                if diff:
                    print(f"❌ ERROR: IDs en 'aportaciones.csv' no definidos en 'activos.csv': {diff}")
                    errors_found = True
                else:
                    print("✅ Aportaciones: Todos los IDs son válidos.")
            else:
                print("✅ Aportaciones: Archivo vacío (sin operaciones).")
        except Exception as e:
            print(f"⚠️ Error leyendo aportaciones.csv: {e}")

    # Check Saldo Inicial
    if os.path.exists(saldo_path):
        try:
            df_saldo = pd.read_csv(saldo_path)
            if not df_saldo.empty:
                saldo_ids = set(df_saldo['id_activo'].astype(str).str.strip().unique())
                diff = saldo_ids - valid_ids
                if diff:
                    print(f"❌ ERROR: IDs en 'saldo_inicial.csv' no definidos en 'activos.csv': {diff}")
                    errors_found = True
                else:
                    print("✅ Saldo Inicial: Todos los IDs son válidos.")
            else:
                print("✅ Saldo Inicial: Sin datos.")
        except Exception as e:
            print(f"⚠️ Error leyendo saldo_inicial.csv: {e}")

    if not errors_found:
        print("--- Integridad correcta ---\n")
        return True
    else:
        print("\n⚠️  SE HAN DETECTADO ERRORES DE INTEGRIDAD.")
        print("El sistema podría fallar o ignorar datos.")
        return True

if __name__ == "__main__":
    check_integrity()
