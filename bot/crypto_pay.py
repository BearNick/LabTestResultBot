import requests
from typing import Optional, Dict, Any
from bot.config import CRYPTO_PAY_TOKEN, CRYPTO_API_BASE

HEADERS = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}

def create_invoice(amount: float, asset: str, description: str = "", payload: str = "") -> Optional[Dict[str, Any]]:
    """
    Создать инвойс. Возвращает dict с полями:
    - invoice_id (int)
    - pay_url (str)
    - status (active/paid/expired)
    """
    url = f"{CRYPTO_API_BASE}/createInvoice"
    data = {
        "asset": asset,          # USDT/TON/BTC/ETH/...
        "amount": str(amount),   # строкой
        "description": description,
        "payload": payload,      # любой ваш идентификатор, например tg_user_id
        "allow_comments": False,
        "allow_anonymous": True
    }
    r = requests.post(url, headers=HEADERS, json=data, timeout=20)
    r.raise_for_status()
    js = r.json()
    if js.get("ok"):
        return js["result"]
    return None

def get_invoice(invoice_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить статус инвойса. Возвращает dict (invoice) или None.
    """
    url = f"{CRYPTO_API_BASE}/getInvoices"
    params = {"invoice_ids": str(invoice_id)}
    r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    r.raise_for_status()
    js = r.json()
    if js.get("ok") and js["result"]["items"]:
        return js["result"]["items"][0]
    return None
