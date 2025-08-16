# LabResultBot

Telegram-бот: интерпретация анализов (ОАК/БАК) на RU/EN/ES, оплата USDT (CryptoBot) + донаты RUB/USD/EUR (DonationAlerts).

## Быстрый старт
```bash
git clone <repo>
cd labresultbot
python3 -m venv venv && source venv/bin/activate
pip install -U pip && pip install -r requirements.txt
cp .env.example .env  # заполните .env своими ключами
python3 main.py
