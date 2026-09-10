"""Run locally after sending /start to your bot. Token is entered invisibly."""
from getpass import getpass
import json
from urllib.request import urlopen

token = getpass("BotFather token (hidden): ")
try:
    with urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=30) as response:
        data = json.load(response)
    chats = {item["message"]["chat"]["id"] for item in data.get("result", [])
             if "message" in item and item["message"]["chat"]["type"] == "private"}
    if not chats:
        print("봇과 개인 대화에서 /start를 보낸 다음 다시 실행하세요. 기존 webhook 사용 봇은 새 봇을 만드세요.")
    for chat_id in sorted(chats):
        print(f"Private chat ID: {chat_id}")
except Exception:
    print("조회 실패. 토큰 및 네트워크를 확인하세요.")
    raise SystemExit(1)
