import os, time, threading, traceback, requests
from flask import Flask
from collections import deque

app = Flask(__name__)
@app.route("/")
def home():
    return "Bot ULTRA DEMO funcionando!"

SYMBOL = "BTCUSDT"
CAPITAL_INICIAL = 1000.0
PORCENTAJE_POR_OPERACION = 0.30
TAKE_PROFIT = 0.004  # +0.4%
STOP_LOSS = 0.0025   # -0.25%

saldo_usdt = CAPITAL_INICIAL
btc_en_cartera = 0.0
precio_entrada = 0.0
en_operacion = False
num_ops = 0
chat_ids = set()

def get_klines(limit=100):
    try:
        url = f"https://data-api.binance.vision/api/v3/klines?symbol={SYMBOL}&interval=1m&limit={limit}"
        r = requests.get(url, timeout=10)
        data = r.json()
        return [float(c[4]) for c in data]
    except Exception as e:
        print(f"Error klines: {e}")
        return []

def ema(data, periodo):
    if len(data) < periodo: return None
    k = 2 / (periodo + 1)
    v = sum(data[:periodo]) / periodo
    for p in data[periodo:]:
        v = p * k + v * (1 - k)
    return v

def rsi(data, periodo=14):
    if len(data) < periodo + 1: return 50
    gains, losses = [], []
    for i in range(1, periodo+1):
        diff = data[-i] - data[-i-1]
        gains.append(max(diff, 0)); losses.append(max(-diff, 0))
    avg_gain = sum(gains)/periodo; avg_loss = sum(losses)/periodo
    if avg_loss == 0: return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_precio():
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={SYMBOL}", timeout=10)
        return float(r.json()["price"])
    except:
        return None

bot_app = None
async def enviar_a_todos(texto):
    global bot_app
    if not bot_app: return
    for cid in list(chat_ids):
        try:
            await bot_app.bot.send_message(chat_id=cid, text=texto)
        except Exception as e:
            print(f"Error enviar: {e}")

def loop_trading():
    global saldo_usdt, btc_en_cartera, precio_entrada, en_operacion, num_ops
    import asyncio
    time.sleep(10)
    print("Loop ULTRA iniciado")
    while True:
        try:
            closes = get_klines(100)
            if len(closes) < 60:
                time.sleep(30); continue
            precio = closes[-1]
            ema5 = ema(closes, 5); ema9 = ema(closes, 9)
            rsi_val = rsi(closes)
            ema5_prev = ema(closes[:-1], 5); ema9_prev = ema(closes[:-1], 9)
            cruce_alcista = ema5_prev <= ema9_prev and ema5 > ema9
            cruce_bajista = ema5_prev >= ema9_prev and ema5 < ema9
            print(f"ULTRA BTC {precio:.2f} EMA5 {ema5:.2f} EMA9 {ema9:.2f} RSI {rsi_val:.1f} EnOper: {en_operacion}")
            if not en_operacion:
                # ULTRA: compra con solo cruce, casi sin filtro
                if cruce_alcista and rsi_val < 80:
                    monto = saldo_usdt * PORCENTAJE_POR_OPERACION
                    btc_en_cartera = monto / precio
                    saldo_usdt -= monto
                    precio_entrada = precio
                    en_operacion = True
                    num_ops += 1
                    msg = f"⚡ COMPRA ULTRA DEMO #{num_ops}\nPrecio: {precio:.2f}\nMonto: {monto:.2f} USDT\nRSI: {rsi_val:.1f}\nEMA5 cruzó EMA9"
                    asyncio.run(enviar_a_todos(msg))
            else:
                pnl_pct = (precio - precio_entrada) / precio_entrada
                if pnl_pct >= TAKE_PROFIT or pnl_pct <= -STOP_LOSS or cruce_bajista:
                    venta = btc_en_cartera * precio
                    saldo_usdt += venta
                    motivo = "TP +0.4%" if pnl_pct >= TAKE_PROFIT else "SL -0.25%" if pnl_pct <= -STOP_LOSS else "Cruce Bajista"
                    msg = f"💥 VENTA ULTRA DEMO\nMotivo: {motivo}\nEntrada: {precio_entrada:.2f} -> Salida: {precio:.2f}\nPnL: {pnl_pct*100:.2f}%\nSaldo: {saldo_usdt:.2f} USDT\nOps totales: {num_ops}"
                    asyncio.run(enviar_a_todos(msg))
                    btc_en_cartera = 0; en_operacion = False; precio_entrada = 0
            time.sleep(30) # Revisa cada 30 seg
        except Exception as e:
            print(f"Error loop: {e}"); traceback.print_exc()
            time.sleep(30)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=loop_trading, daemon=True).start()
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not TOKEN:
        print("FALTA TOKEN")
        while True: time.sleep(60)
    try:
        from telegram import Update
        from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_ids.add(update.effective_chat.id)
            await update.message.reply_text(f"⚡ Bot ULTRA DEMO activado\nSaldo demo: {saldo_usdt:.2f} USDT\nEstrategia: Scalping 1m EMA 5/9 + TP 0.4% / SL 0.25%\nOpera casi todo el tiempo\nComandos:\n/balance - ver saldo\n/precio - precio BTC\n/estado - ver estado")
        async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
            chat_ids.add(update.effective_chat.id)
            precio = get_precio() or 0
            valor_btc = btc_en_cartera * precio
            total = saldo_usdt + valor_btc
            await update.message.reply_text(f"💰 BALANCE ULTRA DEMO\nUSDT: {saldo_usdt:.2f}\nBTC: {btc_en_cartera:.6f} (~{valor_btc:.2f} USDT)\nTotal: {total:.2f} USDT\nPnL total: {total - CAPITAL_INICIAL:.2f} USDT\nOps: {num_ops}\nEn operación: {'SI' if en_operacion else 'NO'}")
        async def precio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            p = get_precio()
            await update.message.reply_text(f"BTC/USDT: {p:.2f} USDT" if p else "Error precio")
        async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
            closes = get_klines(100)
            if closes:
                await update.message.reply_text(f"📊 ESTADO ULTRA\nPrecio: {closes[-1]:.2f}\nEMA5: {ema(closes,5):.2f}\nEMA9: {ema(closes,9):.2f}\nRSI: {rsi(closes):.1f}\nEn operación: {'SI @ '+str(precio_entrada) if en_operacion else 'NO'}")
            else:
                await update.message.reply_text("No puedo obtener datos")
        bot_app = ApplicationBuilder().token(TOKEN).build()
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(CommandHandler("balance", balance))
        bot_app.add_handler(CommandHandler("precio", precio_cmd))
        bot_app.add_handler(CommandHandler("estado", estado))
        print("Bot ULTRA iniciado")
        bot_app.run_polling()
    except Exception as e:
        print(f"ERROR BOT: {e}"); traceback.print_exc()
        while True: time.sleep(60)
