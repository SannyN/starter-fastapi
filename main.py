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
    ticker: str | None
    side: str | None
    min_winrate: str | None
    entry: str | None
    leverage: str | None
    tp1: TakeProfit | None
    tp2: TakeProfit | None
    tp3: TakeProfit | None
    tp4: TakeProfit | None
    winrate: str | None
    strategy: str | None
    beTargetTrigger: str | None
    stop: str | None
    risk: str | None
    betargetHit: bool | None
    betargetStoplos: str | None


app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.post("/webhook")
async def webhook(data: WebhookData, secret: str = Query(None)):
    if os.environ["client_secret"] != secret:
        print("secret")
        return {"message": "nice"}

    print(data)
    # BTCUSDT.P
    symbol = data.ticker.replace(".P", "")

    if data.betargetHit:
        print(session.set_trading_stop(category=category, symbol=symbol, stopLos=data.betargetStoplos, positionIdx=0, tpslMode="Full"))

    # Get account balance

    wallet_type = "UNIFIED"

    if os.environ["testnet"] == "false":
        wallet_type = "CONTRACT"
    
    walletBalance = session.get_wallet_balance(
                        accountType=wallet_type,
                        coin="USDT"
                    )
    print(walletBalance)
    if walletBalance["retMsg"] == "OK":
        balance = decimal.Decimal(walletBalance["result"]["list"][0]["coin"][0]["walletBalance"])
    else:
        print("Failed to get account info")
        return {"message": "Failed to get account info"}
    
    print("Balance")
    print(balance)

    print("data.leverage")
    print(data.leverage)

    try:
        resp = session.set_leverage(
            category=category,
            symbol=symbol,
            buyLeverage=str(data.leverage),
            sellLeverage=str(data.leverage)
        )
        print(resp)
    except RuntimeError as error:
        print(error)
        print("Failed - continue set_leverage")
    except:
        print("Failed - continue set_leverage")

    try:        
        print(session.switch_position_mode(
                category=category,
                symbol=symbole,
                mode=0))
    except RuntimeError as error:
        print(error)
        print("Failed - continue switch_position_mode")
    except:
        print("Failed - continue switch_position_mode")

    instruments = session.get_instruments_info(category=category, symbol=symbol)
    print(instruments)
    qtyStep = instruments["result"]["list"][0]["lotSizeFilter"]["qtyStep"]
    minOrderQty = instruments["result"]["list"][0]["lotSizeFilter"]["minOrderQty"]
    maxOrderQty = instruments["result"]["list"][0]["lotSizeFilter"]["maxMktOrderQty"]

    if qtyStep == "0.001":
        precision = 3
    if qtyStep == "0.01":
        precision = 2
    if qtyStep == "0.1":
        precision = 1
    if qtyStep == "1":
        precision = 0
    if qtyStep == "10":
        precision = -1 
    if qtyStep == "100":
        precision = -2
    if qtyStep == "1000":
        precision = -3

    dentry = decimal.Decimal(data.entry)
    dwinrate = decimal.Decimal(data.winrate)

    dbeTargetTrigger = int(data.beTargetTrigger) - 1
    dmin_winrate = decimal.Decimal(data.min_winrate)
    dmin_order = decimal.Decimal(minOrderQty)
    dmax_order = decimal.Decimal(maxOrderQty) if maxOrderQty is not None else 0

    dstop = decimal.Decimal(data.stop)
    drisk = decimal.Decimal(data.risk)
    risk = (drisk if drisk < 1 else 1) / 100
    order_distance = dentry - dstop if data.side == "LONG" else dstop - dentry

    print("order_distance")
    print(order_distance)
    print("balance")
    print(balance)
    print("risk")
    print(risk)
    print("dmin_order")
    print(dmin_order)
    print("dmax_order")
    print(dmax_order)

    dorder_qty = (balance * decimal.Decimal(risk)) / order_distance

    if dorder_qty < dmin_order:
        dorder_qty = dmin_order

    if dmax_order > 0 and dorder_qty > dmax_order:
        dorder_qty = dmax_order
        
    print("dorder_qty")
    print(dorder_qty)

    print("dorder_qty")
    print(dbeTargetTrigger)

    if dwinrate < dmin_winrate:
        print("Winrate low")
        return {"message": "Winrate too low"}

    print(balance)

    print("Cancel all active orders & positions")
    Helpers(session).close_position(category=category, symbol=symbol)


    
    print("market order qty:")
    print(round(float(dorder_qty), int(precision)))
    # Place market order
    resp = session.place_order(
        category=category,
        symbol=symbol,
        side='Buy' if data.side == "LONG" else 'Sell',
        orderType='Market',
        qty=round(float(dorder_qty), int(precision)),
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
        print(round(float(dorder_qty*qty_factor), int(precision)))
        resp = session.place_order(
            category=category,
            symbol=symbol,
            side='Buy' if data.side == "SHORT" else 'Sell',
            orderType='Limit',
            qty=round(float(dorder_qty*qty_factor), int(precision)),
            timeInForce="PostOnly",
            positionIdx=0,
            price=price,
            reduceOnly=True
        )
        print(resp)
        
    return {"nice"}
