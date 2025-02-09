from flask import Flask, render_template, request, redirect, url_for
import requests
import csv
import os

app = Flask(__name__)

COINS_FILE = 'coins.csv'

def load_coins():
    coins = []
    if os.path.exists(COINS_FILE):
        with open(COINS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            for row in reader:
                if not row.get('TokenID', '').strip():
                    continue
                coin_id = row['TokenID'].strip().lower()
                Symbol = row['Symbol'].strip()
                Price = row['Price'].strip()
                coins.append({'TokenID': coin_id, 'Symbol': Symbol, 'Price': Price})
    return coins

def save_coins():
    with open(COINS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['TokenID', 'Symbol', 'Price']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
        writer.writeheader()
        for coin in coins:
            writer.writerow(coin)

coins = load_coins()

@app.route('/')
def index():
    return render_template('index.html', coins=coins)

@app.route('/add', methods=['POST'])
def add_coin():
    coin_id = request.form.get('coin_id')
    if coin_id:
        coin_id = coin_id.strip().lower()
        if not any(c['TokenID'] == coin_id for c in coins):
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false"
            response = requests.get(url)
            if response.status_code == 200:
                coin_data = response.json()
                Symbol = coin_data.get('symbol', 'N/A').upper()
            else:
                Symbol = 'N/A'
            new_coin = {'TokenID': coin_id, 'Symbol': Symbol, 'Price': 'N/A'}
            coins.append(new_coin)
            save_coins()
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_data():
    if coins:
        coin_ids_str = ','.join(coin['TokenID'] for coin in coins)
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "ids": coin_ids_str,
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json() 
            for coin in coins:
                for coin_data in data:
                    if coin_data.get("id") == coin["TokenID"]:
                        current_price = coin_data.get("current_price")
                        if current_price is not None:
                            coin["Price"] = str(current_price).replace('.', ',')
                        else:
                            coin["Price"] = "N/A"
                        coin["Symbol"] = coin_data.get("symbol", "N/A").upper()
                        break
                else:
                    coin["Price"] = "N/A"
                    coin["Symbol"] = "N/A"
            save_coins()
        else:
            print("Erro na atualização dos dados:", response.status_code, response.text)
    return redirect(url_for('index'))



@app.route('/delete/<coin_id>', methods=['POST'])
def delete_coin(coin_id):
    global coins
    coins = [coin for coin in coins if coin['TokenID'] != coin_id]
    save_coins()
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

