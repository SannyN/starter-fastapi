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
    testnet=os.environ["testnet"] == "true",
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
    max_order: str | None
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
        balance = decimal.Decimal(walletBalance["result"]["list"][0]["walletBalance"])
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
    dmax_order = decimal.Decimal(data.max_order) if data.max_order is not None else 0

    dstop = decimal.Decimal(data.stop)
    distance = (dentry * 100 / dstop if data.side == "LONG" else dstop * 100 / dentry) - 100
    risk = decimal.Decimal(data.risk) / 100
    order_distance = dentry - dstop if data.side == "LONG" else dstop - dentry

    print("order_distance")
    print(order_distance)
    print("balance")
    print(balance)
    print("risk")
    print(risk)
    print("dmin_order")
    print(dmin_order)

    dorder_qty = (balance * risk) / order_distance

    if dorder_qty < dmin_order:
        dorder_qty = dmin_order

    if dmax_order > 0 and dorder_qty > dmax_order:
        dorder_qty = dmax_order
        
    print("dorder_qty")
    print(dorder_qty)

    trailingActivationPrices = [data.tp1.value, data.tp2.value, data.tp3.value, data.tp4.value]
    activationPrice = decimal.Decimal(trailingActivationPrices[dbeTargetTrigger])

    print("activationPrice")
    print(activationPrice)
    print(dbeTargetTrigger)

    withTrailing = data.beTargetTrigger != "WITHOUT"

    if withTrailing:
        if data.side == "LONG":
            trailing = activationPrice - dentry
        else:
            trailing =  dentry - activationPrice

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
            category=category,
            symbol=symbol,
            buyLeverage=str(actual_leverage),
            sellLeverage=str(actual_leverage)
        )
        print(resp)
    except RuntimeError as error:
        print(error)
        print("Failed - continue set_leverage")
    except:
        print("Failed - continue set_leverage")

    
    print("market order qty:")
    print(round(float(dorder_qty), int(data.precision)))
    # Place market order
    resp = session.place_order(
        category='linear',
        symbol=symbol,
        side='Buy' if data.side == "LONG" else 'Sell',
        orderType='Market',
        qty=round(float(dorder_qty), int(data.precision)),
        stopLoss=data.stop,
        slTriggerBy='MarkPrice',
        positionIdx=0
    )

    # Place limit orders
    orders = [data.tp1, data.tp2, data.tp3, data.tp4]

    for order in orders:
        qty_factor = decimal.Decimal(order.percentage) / 100
        price = decimal.Decimal(order.value)

        if qty_factor == 0:
            continue
        
        print("limit market order qty:")
        print(round(float(dorder_qty*qty_factor), int(data.precision)))
        resp = session.place_order(
            category='linear',
            symbol=symbol,
            side='Buy' if data.side == "SHORT" else 'Sell',
            orderType='Limit',
            qty=round(float(dorder_qty*qty_factor), int(data.precision)),
            timeInForce="PostOnly",
            positionIdx=0,
            price=price,
            reduceOnly=True
        )
        print(resp)
        
    if withTrailing:
        print("with trailing:")
        print(trailing)
        resp = session.set_trading_stop(
            category=category,
            symbol=symbol,
            trailingStop=str(trailing),
            activePrice=str(activationPrice),
            positionIdx=0
        )
        print(resp)

    return {"nice"}
