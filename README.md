# Binance Futures Testnet 

A Python CLI tool to place Market, Limit, and Stop-Limit orders on Binance USDT-M Futures Testnet.

---

## Project Files

```
client.py --  Handles API calls, request signing, error handling
main.py   --  CLI interface, input validation, output formatting
test_mock.py  --  Test suite (no API keys needed)
requirements.txt --  Dependencies
logs/
    ├── market_order.log
    ├── limit_order.log
    └── stop_limit_order.log
```

---

## Step 1 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 2 — Get Testnet API Keys

1. Go to https://testnet.binancefuture.com
2. Log in with Google / Apple / Telegram
3. Click **API Key** → **Generate**
4. Copy your API Key and Secret

---

## Step 3 — Set Your Credentials

**Mac / Linux:**
```bash
export BINANCE_API_KEY=your_api_key
export BINANCE_API_SECRET=your_api_secret
```

**Windows:**
```cmd
set BINANCE_API_KEY=your_api_key
set BINANCE_API_SECRET=your_api_secret
```

---

## Step 4 — Run Tests (No API Keys Needed)

```bash
python3 test_mock.py
```

Output:
```
 Valid MARKET BUY — passed
 Valid LIMIT SELL — passed
 Valid STOP-LIMIT SELL — passed
 Invalid side caught — passed
 LIMIT without price caught — passed
 Market BUY order mock — passed
 Limit SELL order mock — passed
 Stop-Limit SELL order mock — passed
...
 All 16 tests passed!
```

---

## Step 5 — Place Orders

**Market BUY:**
```bash
python3 main.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

**Limit SELL:**
```bash
python3 main.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 2000
```

**Stop-Limit SELL:**
```bash
python3 main.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.01 --stop-price 65000 --price 64800
```

---

## Sample Output

```
───────────────────────────────────────
    ORDER REQUEST SUMMARY
───────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
───────────────────────────────────────

───────────────────────────────────────
    ORDER RESPONSE
───────────────────────────────────────
  Order ID    : 3198452761
  Status      : FILLED
  Executed Qty: 0.001
  Avg Price   : 84321.50
───────────────────────────────────────
    Order placed successfully!
───────────────────────────────────────
```

---

## Logs

Every order is automatically logged to `binance_futures.log`. Sample logs for all three order types are in the `logs/` folder.

---

## Assumptions

- Works on Binance **Testnet only** — no real money involved (`https://testnet.binancefuture.com`)
- `timeInForce` defaults to `GTC` (Good Till Cancelled) for Limit and Stop-Limit orders
- Minimum BTC quantity is `0.001` — follows Binance's own symbol rules
- Stop-Limit needs both `--stop-price` (trigger price) and `--price` (limit execution price)
- Python 3.8 or higher is required
