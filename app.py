from fastapi import FastAPI, Query
from pybit.unified_trading import HTTP
from pybit.helpers import Helpers
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import os
import decimal

app = FastAPI()

session = HTTP(
    api_key=os.environ["api_key"],
    api_secret=os.environ["api_secret"],
    testnet=False,
)

symbol = "BTCUSDT"
category = "linear"

class WebhookData(BaseModel):
    side: str
    entry: str
    tp1: str
    tp2: str
    tp3: str
    tp4: str
    winrate: str
    strategy: str
    beTargetTrigger: str
    stop: str

def calculate_order_qty(balance, stoploss_percent, leverage):
    return balance * stoploss_percent / (100 * leverage)

def calculate_leverage(order_qty, balance, stoploss_percent):
    return order_qty * 100 * stoploss_percent / balance

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.post("/webhook")
async def webhook(data: WebhookData, secret: str = Query(None)):
    if os.environ["client_secret"] != secret:
        print("secret")
        return {"message": "nice"}

    stoploss_percent = 10  # 10% Stoploss

    # Get account balance
    
    walletBalance = session.get_wallet_balance(
                        accountType="UNIFIED",
                        coin="USDT",
                    )
    print(walletBalance)
    if walletBalance["retMsg"] == "OK":
        balance = decimal.Decimal(walletBalance["result"]["list"][0]["totalEquity"])
    else:
        print("Failed to get account info")
        return {"message": "Failed to get account info"}
    
    print("Balance")
    print(balance)

    # Calculate leverage based on the stoploss percentage
    #leverage = decimal.Decimal(100 / (stoploss_percent * 10))  # Formula for linear contracts
    #print("leverage")
    #print(leverage)


    # Calculate actual leverage based on the calculated order quantity
    actual_leverage = "17.5" # calculate_leverage(balance, order_qty, stoploss_percent)
    dactual_leverage = decimal.Decimal(actual_leverage)

    print("actual_leverage")
    print(actual_leverage)

    dentry = decimal.Decimal(data.entry)
    dwinrate = decimal.Decimal(data.winrate)
    dtp1 = decimal.Decimal(data.tp1)
    dstop = decimal.Decimal(data.stop)
    distance = (dentry * 100 / dstop if data.side == "LONG" else dstop * 100 / dentry) - 100
    risk = 0.1

    dorder_qty = (balance * risk) / distance
    print("dorder_qty")
    print(dorder_qty)

    if data.side == "LONG":
        trailingSL = dentry - dstop
        trailingTP1 = dtp1 - dentry
        trailing = trailingSL if trailingSL > trailingTP1 else trailingTP1
    else:
        trailingSL = dstop - dentry
        trailingTP1 = dentry - dtp1
        trailing = trailingSL if trailingSL > trailingTP1 else trailingTP1

    if dwinrate < 50:
        print("Winrate low")
        return {"message": "Winrate too low"}

    if distance > 3:
        print("Distance too high")
        return {"message": "Distance too high"}

    print(balance)

    print("Cancel all active orders & positions")
    Helpers(session).close_position(category=category, symbol=symbol)

    try:
        resp = session.set_leverage(
            category=categoy,
            symbol=symbol,
            buyLeverage=str(actual_leverage),
            sellLeverage=str(actual_leverage),
        )
        print(resp)
    except RuntimeError as error:
        print(error)
        print("Failed - continue")
    except:
        print("Failed - continue")

    # Place market order
    resp = session.place_order(
        category='linear',
        symbol=symbol,
        side='Buy' if data.side == "LONG" else 'Sell',
        orderType='Market',
        qty=str(dorder_qty),
        stopLoss=data.stop,
        slTriggerBy='MarkPrice',
        positionIdx=0
    )
    print(resp)

    # Place limit orders
    orders = [(0.4, data.tp1), (0.3, data.tp2), (0.2, data.tp3)]
    for qty_factor, price in orders:
        resp = session.place_order(
            category='linear',
            symbol=symbol,
            side='Buy' if data.side == "SHORT" else 'Sell',
            orderType='Limit',
            qty=str(dorder_qty * qty_factor),
            timeInForce="PostOnly",
            positionIdx=0,
            price=price,
            reduceOnly=True
        )
        print(resp)

    # Set trading stop
    resp = session.set_trading_stop(
        category=category,
        symbol=symbol,
        trailingStop=str(trailing),
        activePrice=data.tp1,
        positionIdx=0
    )
    print(resp)

    print(data)
    return {"nice"}
