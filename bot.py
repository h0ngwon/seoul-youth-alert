"""Seoul youth housing daily digest. Python 3.12+, standard library only."""
import argparse
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://soco.seoul.go.kr"
LIST_URL = BASE + "/youth/bbs/BMSR00015/list.do?menuNo=400008"
API = BASE + "/youth/pgm/home/yohome/bbsListJson.json"
KST = timezone(timedelta(hours=9))
STATE = Path("state.json")


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "tr", "li", "h2"}:
            self.parts.append("\n")
        if tag in {"td", "th"}:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "tr", "li", "h2"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(html):
    parser = TextParser()
    parser.feed(html or "")
    return "\n".join(" ".join(line.split()) for line in "".join(parser.parts).splitlines() if line.strip())


def parse_day(value):
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def read_json(url, payload, retries=3):
    for attempt in range(retries):
        try:
            req = Request(url, data=urlencode(payload).encode(), headers={
                "User-Agent": "SeoulYouthAlert/1.0 (daily personal notice checker)",
                "Referer": LIST_URL,
            })
            with urlopen(req, timeout=30) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError):
            if attempt + 1 == retries:
                raise RuntimeError("서울시 공고 조회 실패: 네트워크 또는 서버 응답 확인 필요") from None
            time.sleep(2 ** attempt)


def fetch_all():
    rows = {}
    page = 1
    total_pages = 1
    while page <= total_pages:
        data = read_json(API, {"bbsId": "BMSR00015", "pageIndex": page,
            "searchAdresGu": "", "searchCondition": "", "searchKeyword": "", "optn2": "", "optn5": ""})
        if not isinstance(data, dict) or not isinstance(data.get("resultList"), list):
            raise RuntimeError("공고 API 형식 변경: resultList 없음")
        total_pages = int(data["pagingInfo"]["totPage"])
        if not 1 <= total_pages <= 500 or not data["resultList"]:
            raise RuntimeError("공고 페이지 수 또는 빈 목록 이상: 알림을 중단합니다")
        added = 0
        for row in data["resultList"]:
            if not all(key in row for key in ("boardId", "nttSj", "optn4")):
                raise RuntimeError("공고 필드 구조 변경")
            key = str(row["boardId"])
            added += key not in rows
            rows[key] = row
        if not added:
            raise RuntimeError("동일 페이지 반복 감지: 전체 조회를 확인할 수 없습니다")
        page += 1
        if page <= total_pages:
            time.sleep(1)
    print(f"조회 완료: {len(rows)}건 / {total_pages}페이지")
    return list(rows.values())


def entry(row, today, days):
    start = parse_day(row.get("optn4"))
    if start is None:
        return None
    remaining = (start - today).days
    if not 0 <= remaining <= days:
        return None
    url = BASE + "/youth/bbs/BMSR00015/view.do?" + urlencode({
        "optn1": row.get("optn1") or "", "boardId": row["boardId"], "menuNo": "400008"})
    label = "오늘 청약신청일" if remaining == 0 else f"청약신청 D-{remaining}"
    return (f"[{label}]\n{plain(row['nttSj'])[:240]}\n"
            f"청약신청일: {start}\n{url}")


def digest(rows, today, days):
    entries = [item for row in rows if (item := entry(row, today, days))]
    header = f"청년안심주택 {today} 일일 알림\n청약신청일이 오늘부터 {days}일 이내인 공고 {len(entries)}건\n목록의 청약신청일 기준입니다. 접수 시각·마감은 원문을 확인하세요.\n"
    unknown = sum(parse_day(row.get("optn4")) is None for row in rows)
    if unknown:
        header += f"날짜 형식 확인이 필요한 공고 {unknown}건은 날짜 필터에서 제외되었습니다.\n"
    messages = []
    current = header
    for item in entries or ["오늘 조건에 맞는 공고가 없습니다.\n" + LIST_URL]:
        if len((current + item).encode("utf-16-le")) // 2 > 3500:
            messages.append(current)
            current = f"청년안심주택 {today} (계속)\n"
        current += "\n" + item + "\n"
    messages.append(current)
    return messages


def send_message(token, chat_id, message):
    req = Request(f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": message,
                         "link_preview_options": {"is_disabled": True}}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=30) as response:
            result = json.load(response)
        if not result.get("ok"):
            raise RuntimeError("텔레그램 API가 전송을 거절했습니다")
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        # Never print the request URL: it contains the bot token.
        # Do not blindly retry an uncertain POST, which could duplicate delivery.
        raise RuntimeError("텔레그램 전송 실패: 토큰·chat_id·봇 시작 여부 확인 필요") from None


def deliver(messages, today, token, chat_id):
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    sent = set(state.get("sent", [])) if state.get("date") == str(today) else set()
    for message in messages:
        key = sha256(message.encode()).hexdigest()
        if key in sent:
            continue
        send_message(token, chat_id, message)
        sent.add(key)
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"date": str(today), "sent": sorted(sent)}, indent=2), encoding="utf-8")
        tmp.replace(STATE)
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", type=date.fromisoformat)
    parser.add_argument("--fixture", type=Path)
    args = parser.parse_args()
    if (args.date or args.fixture) and not args.dry_run:
        parser.error("--date/--fixture는 --dry-run에서만 사용하세요")
    today = args.date or datetime.now(KST).date()
    days = int(os.environ.get("ALERT_DAYS", "7"))
    if not 0 <= days <= 60:
        raise RuntimeError("ALERT_DAYS는 0~60이어야 합니다")
    token, chat_id = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not args.dry_run and (not token or not chat_id):
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID Secrets를 설정하세요")
    rows = json.loads(args.fixture.read_text(encoding="utf-8-sig")) if args.fixture else fetch_all()
    messages = digest(rows, today, days)
    if args.dry_run:
        print("\n\n".join(messages))
    else:
        deliver(messages, today, token, chat_id)
        print("일일 알림 처리 완료")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Unexpected exception messages may contain URLs or credentials.
        print(str(error) if isinstance(error, RuntimeError) else f"실행 실패 ({type(error).__name__})")
        raise SystemExit(1)
