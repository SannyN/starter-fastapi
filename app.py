from fastapi import FastAPI, Body
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

print(session.get_positions(category="linear", symbol="BTCUSDT"))

class Item(BaseModel):
    item_id: int


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.post("/webhook")
async def webhook(data: str = Body()):
    print("webhook")
    print(data)
    return {"nice"}