from flask import Flask, render_template, request, redirect, url_for
import requests
import csv
import os

app = Flask(__name__)

COINS_FILE = 'coins.csv'

def load_coins():
    """Carrega os dados do CSV e retorna uma lista de dicionários."""
    coins = []
    if os.path.exists(COINS_FILE):
        with open(COINS_FILE, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='|')
            for row in reader:
                # Ignora linhas sem o 'id da moeda'
                if not row.get('id da moeda', '').strip():
                    continue
                coin_id = row['id da moeda'].strip().lower()
                simbolo = row['simbolo'].strip()
                price = row['price'].strip()
                coins.append({'id da moeda': coin_id, 'simbolo': simbolo, 'price': price})
    return coins

def save_coins():
    """Salva a lista de moedas no CSV."""
    with open(COINS_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id da moeda', 'simbolo', 'price']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='|')
        writer.writeheader()
        for coin in coins:
            writer.writerow(coin)

# Carrega os dados do CSV ao iniciar a aplicação
coins = load_coins()

@app.route('/')
def index():
    return render_template('index.html', coins=coins)

@app.route('/add', methods=['POST'])
def add_coin():
    coin_id = request.form.get('coin_id')
    if coin_id:
        coin_id = coin_id.strip().lower()
        if not any(c['id da moeda'] == coin_id for c in coins):
            # Tenta buscar os detalhes da moeda para obter o símbolo via API
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}?localization=false"
            response = requests.get(url)
            if response.status_code == 200:
                coin_data = response.json()
                simbolo = coin_data.get('symbol', 'N/A').upper()
            else:
                simbolo = 'N/A'
            # Adiciona a moeda com preço inicial "N/A"
            new_coin = {'id da moeda': coin_id, 'simbolo': simbolo, 'price': 'N/A'}
            coins.append(new_coin)
            save_coins()
    return redirect(url_for('index'))

@app.route('/update', methods=['POST'])
def update_prices():
    if coins:
        # Concatena os IDs das moedas para a requisição
        coin_ids_str = ','.join(coin['id da moeda'] for coin in coins)
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_ids_str,
            "vs_currencies": "usd",
        }
        # Faz a requisição passando os parâmetros corretamente
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            for coin in coins:
                cid = coin['id da moeda']
                # Se o coin foi encontrado na resposta, atualiza o preço; caso contrário, define "N/A"
                if cid in data and 'usd' in data[cid]:
                    coin['price'] = data[cid]['usd']
                else:
                    coin['price'] = "N/A"
            save_coins()
        else:
            # Em caso de erro, imprime os detalhes para facilitar a depuração
            print("Erro na atualização dos preços:", response.status_code, response.text)
    return redirect(url_for('index'))

@app.route('/delete/<coin_id>', methods=['POST'])
def delete_coin(coin_id):
    global coins
    coins = [coin for coin in coins if coin['id da moeda'] != coin_id]
    save_coins()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
