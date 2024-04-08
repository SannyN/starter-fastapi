from fastapi import FastAPI, Body, Query
from fastapi.responses import FileResponse
from pybit.unified_trading import HTTP

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


@app.post("/webhook")
async def webhook(data: str = Body(), secret: str = Query(None)):
    if os.environ["client_secret"] != secret: return {"nice"}

    print(session.get_positions(category="linear", symbol="BTCUSDT"))

    print("webhook")
    print(data)
    return {"nice"}