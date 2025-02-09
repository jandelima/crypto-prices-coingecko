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
                if not row.get('Token ID', '').strip():
                    continue
                coin_id = row['Token ID'].strip().lower()
                Symbol = row['Symbol'].strip()
                Price = row['Price'].strip()
                coins.append({'Token ID': coin_id, 'Symbol': Symbol, 'Price': Price})
    return coins

def save_coins():
    with open(COINS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['Token ID', 'Symbol', 'Price']
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
        if not any(c['Token ID'] == coin_id for c in coins):
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false"
            response = requests.get(url)
            if response.status_code == 200:
                coin_data = response.json()
                Symbol = coin_data.get('Symbol', 'N/A').upper()
            else:
                Symbol = 'N/A'
            new_coin = {'Token ID': coin_id, 'Symbol': Symbol, 'Price': 'N/A'}
            coins.append(new_coin)
            save_coins()
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_Prices():
    if coins:
        # Concatena os IDs das moedas para a requisição
        coin_ids_str = ','.join(coin['Token ID'] for coin in coins)
        url = "https://api.coingecko.com/api/v3/simple/Price"
        params = {
            "ids": coin_ids_str,
            "vs_currencies": "usd",
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for coin in coins:
                cid = coin['Token ID']
                if cid in data and 'usd' in data[cid]:
                    coin['Price'] = data[cid]['usd']
                else:
                    coin['Price'] = "N/A"
            save_coins()
        else:
            # Em caso de erro, imprime os detalhes para facilitar a depuração
            print("Erro na atualização dos preços:", response.status_code, response.text)
    return redirect(url_for('index'))

@app.route('/delete/<coin_id>', methods=['POST'])
def delete_coin(coin_id):
    global coins
    coins = [coin for coin in coins if coin['Token ID'] != coin_id]
    save_coins()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
