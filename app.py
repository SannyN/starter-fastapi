from fastapi import FastAPI, Body, Query
from fastapi.responses import FileResponse
from pybit.unified_trading import HTTP
from pybit.helpers import Helpers
import json

import os

from pydantic import BaseModel

app = FastAPI()

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
async def webhook(data: str = Body(), secret: str = Query(None)):
    if os.environ["client_secret"] != secret: return {"nice"}

    positions = session.get_positions(category=category, symbol=symbol)

    if len(positions["result"]["list"]) > 0:
        print(positions["result"]["list"])
        print("Cancel all active orders & positions")
        Helpers(session).close_position(category=category, symbol=symbol)

    print("webhook")
    print(data)
    return {"nice"}