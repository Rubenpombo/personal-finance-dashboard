import requests
from bs4 import BeautifulSoup
import time
import random
import re

def get_price_quefondos(isin):
    """Scrapes QueFondos for the fund price."""
    url = f"https://www.quefondos.com/es/fondos/ficha/index.html?isin={isin}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Pattern: <span class="floatright">110,020000 EUR</span>
            # Find all spans with class 'floatright'
            spans = soup.find_all('span', class_='floatright')
            
            for s in spans:
                text = s.text.strip()
                if "EUR" in text or "USD" in text:
                    # Extract number: "110,020000 EUR" -> 110.02
                    # Regex to find number at start
                    match = re.search(r'([\d\.,]+)', text)
                    if match:
                        num_str = match.group(1)
                        # European format: 1.234,56 -> 1234.56
                        # Remove dots (thousands), replace comma with dot
                        clean_num = num_str.replace('.', '').replace(',', '.')
                        try:
                            return float(clean_num)
                        except:
                            continue
    except Exception as e:
        print(f"QueFondos Error ({isin}): {e}")
    return None

def get_fund_price(isin):
    # Strategy: Currently using QueFondos scraper as it proved more reliable than APIs for this specific set of ISINs.
    # Wrapper for the best available method
    return get_price_quefondos(isin)

def update_prices(activos_df):
    prices = {}
    for _, row in activos_df.iterrows():
        asset_id = row['id']
        isin = row['isin']
        tipo = str(row['tipo']).lower()
        
        if 'efectivo' in tipo or 'cash' in str(isin).lower():
            prices[asset_id] = 1.0
            continue
            
        print(f"Fetching {row['nombre']} ({isin})...")
        p = get_fund_price(isin)
        
        if p:
            prices[asset_id] = p
            print(f"  -> Found: {p}")
        else:
            prices[asset_id] = 0.0
            print("  -> Not found")
            
        time.sleep(random.uniform(0.5, 1.5))
        
    return prices