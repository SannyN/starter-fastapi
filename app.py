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

""" 
{
    "side": "LONG",
    "entry": "63816.2",
    "tp1": "64454.4",
    "tp2": "65092.5",
    "tp3": "65730.7",
    "tp4": "66368.8",
    "winrate": "52%",
    "strategy": "MANUAL",
    "beTargetTrigger": "1",
    "stop": "62810.8"
}


{
    "side": "SHORT",
    "entry": "67023.9",
    "tp1": "66353.7",
    "tp2": "65683.4",
    "tp3": "65013.2",
    "tp4": "64342.9",
    "winrate": "51.03%",
    "strategy": "MANUAL",
    "beTargetTrigger": "1",
    "stop": "67864.7"
}
"""

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
    print("positions")
    print(positions)

    if len(positions["result"]["list"]) > 0:
        print("Cancel all active orders & positions")
        print(positions["result"]["list"])
        Helpers(session).close_position(category=category, symbol=symbol)

    print("webhook")
    print(data)
    return {"nice"}