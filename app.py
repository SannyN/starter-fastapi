from fastapi import FastAPI, Query
from pybit.unified_trading import HTTP
from pybit.helpers import Helpers
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import os
import decimal
from decimal import *

app = FastAPI()

session = HTTP(
    api_key=os.environ["api_key"],
    api_secret=os.environ["api_secret"],
    testnet=False,
)

category = "linear"

class TakeProfit(BaseModel):
    value: str
    percentage: str

class WebhookData(BaseModel):
    ticker: str
    side: str
    min_winrate: str
    min_order: str
    entry: str
    precision: str
    leverage: str
    tp1: TakeProfit
    tp2: TakeProfit
    tp3: TakeProfit
    tp4: TakeProfit
    winrate: str
    strategy: str
    beTargetTrigger: str
    stop: str
    risk: str
    test: bool | None

app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.post("/webhook")
async def webhook(data: WebhookData, secret: str = Query(None)):
    getcontext().prec = 3
    if os.environ["client_secret"] != secret:
        print("secret")
        return {"message": "nice"}

    print(data)
    # BTCUSDT.P
    symbol = data.ticker.replace(".P", "")
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

    actual_leverage = data.leverage
    dactual_leverage = decimal.Decimal(actual_leverage)

    print("actual_leverage")
    print(actual_leverage)

    dentry = decimal.Decimal(data.entry)
    dwinrate = decimal.Decimal(data.winrate)
    dtp1 = decimal.Decimal(data.tp1.value)
    dtp2 = decimal.Decimal(data.tp2.value)

    dbeTargetTrigger = int(data.beTargetTrigger) - 1
    dmin_winrate = decimal.Decimal(data.min_winrate)
    dmin_order = decimal.Decimal(data.min_order)

    dstop = decimal.Decimal(data.stop)
    distance = (dentry * 100 / dstop if data.side == "LONG" else dstop * 100 / dentry) - 100
    risk = decimal.Decimal(data.risk) / 100
    order_distance = dentry - dstop if data.side == "LONG" else dstop - dentry

    dorder_qty = (balance * risk) / order_distance

    if dorder_qty < dmin_order:
        dorder_qty = dmin_order
        
    print("dorder_qty")
    print(dorder_qty)

    trailingActivationPrices = [data.tp1.value, data.tp2.value, data.tp3.value, data.tp4.value]
    activationPrice = decimal.Decimal(trailingActivationPrices[dbeTargetTrigger])

    print("activationPrice")
    print(activationPrice)
    print(dbeTargetTrigger)

    if data.side == "LONG":
        trailingSL = dentry - dstop
        trailingTP = activationPrice - dentry
        trailing = trailingSL if trailingSL > trailingTP else trailingTP
    else:
        trailingSL = dstop - dentry
        trailingTP = dentry - activationPrice
        trailing = trailingSL if trailingSL > trailingTP else trailingTP

    if dwinrate < dmin_winrate:
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

    try:
        # Place market order
        resp = session.place_order(
            category='linear',
            symbol=symbol,
            side='Buy' if data.side == "LONG" else 'Sell',
            orderType='Market',
            qty=round(dorder_qty, int(data.precision)),
            stopLoss=data.stop,
            slTriggerBy='MarkPrice',
            positionIdx=0
        )
        print(resp)
    except RuntimeError as error:
        print(error)
        print("Failed - continue")
    except:
        print("Failed - continue")

    # Place limit orders
    orders = [data.tp1, data.tp2, data.tp3, data.tp4]

    for order in orders:
        qty_factor = decimal.Decimal(order.percentage) / 100
        price = decimal.Decimal(order.value)

        if qty_factor == 0:
            continue
        
        resp = session.place_order(
            category='linear',
            symbol=symbol,
            side='Buy' if data.side == "SHORT" else 'Sell',
            orderType='Limit',
            qty=round(decimal.Decimal(dorder_qty) * qty_factor, int(data.precision)),
            timeInForce="PostOnly",
            positionIdx=0,
            price=price,
            reduceOnly=True
        )
        print(resp)
        
    resp = session.set_trading_stop(
        category=category,
        symbol=symbol,
        trailingStop=str(trailing),
        activePrice=activationPrice,
        positionIdx=0
    )
    print(resp)

    return {"nice"}
