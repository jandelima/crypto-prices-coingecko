from flask import Flask, render_template, request, redirect, url_for
import requests
import csv
import os
import time
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

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

def save_coins(coins_list):
    with open(COINS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['TokenID', 'Symbol', 'Price']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
        writer.writeheader()
        for coin in coins_list:
            writer.writerow(coin)

def atualizar_precos():
    coins_list = load_coins()
    
    # Adiciona uma moeda temporária para evitar problemas com ids vazios
    temp_coin_id = f"temp_{int(time.time())}"
    temp_coin = {'TokenID': temp_coin_id, 'Symbol': 'TEMP', 'Price': 'N/A'}
    coins_list.append(temp_coin)
    save_coins(coins_list)
    
    coins_list = load_coins()
    coin_ids_str = ','.join(coin['TokenID'] for coin in coins_list)
    
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": coin_ids_str
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        for coin in coins_list:
            found = False
            for coin_data in data:
                if coin_data.get("id") == coin["TokenID"]:
                    current_price = coin_data.get("current_price")
                    coin["Price"] = str(current_price).replace('.', ',') if current_price is not None else "N/A"
                    coin["Symbol"] = coin_data.get("symbol", "N/A").upper()
                    found = True
                    break
            if not found:
                coin["Price"] = "N/A"
                coin["Symbol"] = "N/A"
        save_coins(coins_list)
    else:
        print("Erro na atualização dos dados:", response.status_code, response.text)
    
    # Remove a moeda temporária
    coins_list = load_coins()
    coins_list = [coin for coin in coins_list if not coin['TokenID'].startswith("temp_")]
    save_coins(coins_list)


scheduler = BackgroundScheduler()
scheduler.add_job(func=atualizar_precos, trigger="interval", seconds=40)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

@app.route('/')
def index():
    return render_template('index.html', coins=load_coins())

@app.route('/add', methods=['POST'])
def add_coin():
    coin_id = request.form.get('coin_id')
    if coin_id:
        coin_id = coin_id.strip().lower()
        coins_list = load_coins()
        if not any(c['TokenID'] == coin_id for c in coins_list):
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false"
            response = requests.get(url)
            if response.status_code == 200:
                coin_data = response.json()
                Symbol = coin_data.get('symbol', 'N/A').upper()
            else:
                Symbol = 'N/A'
            new_coin = {'TokenID': coin_id, 'Symbol': Symbol, 'Price': 'N/A'}
            coins_list.append(new_coin)
            save_coins(coins_list)
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_data():
    atualizar_precos()
    return redirect(url_for('index'))

@app.route('/delete/<coin_id>', methods=['POST'])
def delete_coin(coin_id):
    coins_list = load_coins()
    coins_list = [coin for coin in coins_list if coin['TokenID'] != coin_id]
    save_coins(coins_list)
    return redirect(url_for('index'))

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    with app.app_context():
        atualizar_precos()  # Atualiza os preços automaticamente ao iniciar o app
    app.run(host="0.0.0.0", port=port, debug=True)
