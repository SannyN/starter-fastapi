from fastapi import FastAPI, Body, Query
from fastapi.responses import FileResponse
from fastapi.middleware.gzip import GZipMiddleware
from pybit.unified_trading import HTTP
from pybit.helpers import Helpers
from pydantic import BaseModel

import json
import decimal

import os

from pydantic import BaseModel

app = FastAPI()


app.add_middleware(GZipMiddleware, minimum_size=1000)

session = HTTP(
    api_key=os.environ["api_key"],
    api_secret=os.environ["api_secret"],
    testnet=False,
)


class Item(BaseModel):
    item_id: int


@app.get("/")
async def root():
    return {"message": "Hello World"}

symbol="BTCUSDT"
category="linear"

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


# Changing mode and leverage: 
def set_mode():
    try:
        resp = session.switch_margin_mode(
            category='linear',
            symbol=symbol,
            tradeMode=mode,
            buyLeverage=leverage,
            sellLeverage=leverage
        )
        print(resp)
    except Exception as err:
        print(err)


@app.post("/webhook")
async def webhook(data: WebhookData, secret: str = Query(None)):
    if os.environ["client_secret"] != secret:
        print("secret")
        return {"nice"}


    leverage = "17.5"
    order_qty = "0.01"
    dorder_qty = 0.01

    dentry = decimal.Decimal(data.entry)
    dwinrate = decimal.Decimal(data.winrate)
    dstop = decimal.Decimal(data.stop)
    distance = (dentry * 100 / dstop if data.side == "LONG" else dstop * 100 / dentry) - 100
    trailing = dentry - dstop if data.side == "LONG" else dstop - dentry


    print("Winrate")
    print(data.winrate)
    print("Distance")
    print(distance)
    print("Trailing")
    print(trailing)

    if dwinrate < 50:
        print("Winrate low")
        return {"nice"}

    if distance > 3:
        print("distance to high")
        return {"nice"}
    
    print("Cancel all active orders & positions")
    Helpers(session).close_position(category=category, symbol=symbol)

    resp = session.place_order(
        category='linear',
        symbol=symbol,
        side='Buy' if data.side == "LONG" else 'Sell',
        orderType='Market',
        qty=order_qty,
        stopLoss=data.stop,
        slTriggerBy='MarkPrice'
    )

    print(resp)

    resp = session.place_order(
        category='linear',
        symbol=symbol,
        side='Buy' if data.side == "SHORT" else 'Sell',
        orderType='Limit',
        qty=dorder_qty*0.4,
        timeInForce="PostOnly",
        positionIdx=0,
        price=data.tp1,
        reduceOnly=True
    )
    
    print(resp)

    resp = session.place_order(
            category='linear',
            symbol=symbol,
            side='Buy' if data.side == "SHORT" else 'Sell',
            orderType='Limit',
            qty=dorder_qty*0.3,
            timeInForce="PostOnly",
            positionIdx=0,
            price=data.tp2,
            reduceOnly=True
    )

    print(resp)

    resp = session.place_order(
            category='linear',
            symbol=symbol,
            side='Buy' if data.side == "SHORT" else 'Sell',
            orderType='Limit',
            qty=dorder_qty*0.2,
            timeInForce="PostOnly",
            positionIdx=0,
            price=data.tp3,
            reduceOnly=True
    )

    print(resp)

    resp = session.set_trading_stop(
    category=category,
    symbol=symbol,
    trailingStop=str(trailing),
    activePrice=data.tp1,
    positionIdx=0
    )

    """

    print(resp)

    resp = session.set_trading_stop(
    
            )
    
    """

    print(data)
    return {"nice"}