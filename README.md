# 서울 청년안심주택 텔레그램 알림

GitHub Actions가 매일 한국시간 오전 9시 17분에 공고를 조회하고 내 텔레그램으로 일일 요약을 보냅니다. 컴퓨터나 브라우저를 켜둘 필요가 없습니다. Python 3.12 표준 라이브러리만 사용합니다.

## 알림 기준

- 목록의 **청약신청일(`optn4`)이 오늘부터 7일 이내**인 공고만 알려줍니다. 오늘과 7일 뒤를 모두 포함합니다.
- 신청일이 지난 공고는 제외합니다. 아직 접수 중이더라도 신청일이 지났으면 제외됩니다. 마감 알림은 이 버전의 범위에 포함하지 않습니다.
- 조건에 해당하는 동안 같은 공고를 매일 요약에 넣습니다. 공고명, 신청일, D-day, 원문 링크를 보냅니다.
- 날짜가 비어 있거나 형식이 달라 판독할 수 없는 공고는 제외하고 그 건수를 알림에 표시합니다.
- 모든 목록 페이지를 순서대로 조회하고 요청 사이에 1초 간격을 둡니다. 빈 응답이나 구조 변경은 정상적인 '공고 없음'으로 처리하지 않고 실행 실패로 남깁니다.
- 해당 공고가 없더라도 정상 확인 메시지를 보냅니다. 긴 요약은 여러 메시지로 나눕니다.
- `state.json`에 전송한 메시지 해시를 저장해 같은 날 같은 내용 재전송을 줄입니다. 다음 날에는 다시 알립니다. 전송 직후 실행이 중단되거나 상태 저장이 실패하면 중복될 수 있습니다.

## 1. 텔레그램 봇 준비

1. 텔레그램에서 공식 [@BotFather](https://t.me/BotFather)를 열고 `/newbot`을 입력합니다.
2. 봇 이름과 `bot`으로 끝나는 사용자 이름을 정해 토큰을 발급받습니다.
3. 생성한 봇의 개인 채팅을 열고 **시작(Start)** 또는 `/start`를 보냅니다.
4. Python이 설치된 내 컴퓨터에서 `python get_chat_id.py`를 실행합니다. 토큰은 화면에 표시되지 않게 입력되며 파일에 저장하지 않습니다. 출력된 개인 채팅 ID를 사용합니다. 여러 ID가 보이면 본인 채팅을 확인하세요.

토큰은 저장소 코드나 채팅 메시지에 붙여 넣지 말고 다음 단계의 GitHub Secrets에 입력하세요.

## 2. GitHub 저장소에 코드 올리기

알림 전용 저장소를 만들고 이 폴더의 **내용**을 저장소 최상위에 올립니다. 기존 프로젝트 안의 하위 폴더로 올리면 이 workflow가 자동 실행되지 않습니다.

```text
저장소 루트/
  .github/workflows/daily.yml
  bot.py
  get_chat_id.py
  tests/test_bot.py
  README.md
  .gitignore
```

GitHub 웹에서 **Add file → Upload files**로 파일을 올릴 수 있습니다. `.github` 폴더가 누락되지 않았는지 확인하세요. 필요하면 **Add file → Create new file**에서 `.github/workflows/daily.yml` 경로를 직접 입력해 만듭니다. 파일은 기본 브랜치(보통 `main`)에 있어야 합니다.

## 3. 비밀값 2개 설정

저장소 **Settings → Secrets and variables → Actions → New repository secret**에 다음을 각각 추가합니다.

| Name | Secret 값 |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | BotFather에서 받은 토큰 |
| `TELEGRAM_CHAT_ID` | 본인과 봇의 개인 채팅 ID |

Workflow는 상태 파일 저장을 위해 `contents: write`를 요청합니다. 조직 정책이 쓰기를 제한하거나 기본 브랜치가 직접 커밋을 막으면 상태 저장 단계가 실패합니다. 전용 저장소 사용이 간단하며 기존 저장소의 보호 규칙을 해제할 필요는 없습니다. 이 경우 상태 저장 방식을 별도로 바꿔야 합니다.

## 4. 첫 실행 확인

1. **Actions → Seoul youth housing daily alert → Run workflow**를 엽니다.
2. 기본 선택된 `dry_run`을 유지하고 실행하면 텔레그램 발송 없이 조회 결과를 로그에서 확인합니다.
3. 확인 후 다시 Run workflow를 열어 `dry_run`을 해제하고 실행합니다.
4. 텔레그램 수신과 Actions 전체 단계 성공을 확인합니다. 이후에는 매일 자동 실행됩니다.

현재 코드를 받은 것만으로는 GitHub 실행이나 텔레그램 연결이 활성화되지 않습니다. 위 설정과 첫 실행이 필요합니다.

## 시간·기간 바꾸기

`.github/workflows/daily.yml`의 `ALERT_DAYS: '7'`을 바꾸면 임박 기준이 바뀝니다. `cron: '17 0 * * *'`은 UTC 00:17, 한국시간 09:17입니다. 예를 들어 매일 한국시간 20:17은 `17 11 * * *`입니다.

GitHub 예약 실행은 부하에 따라 지연되거나 누락될 수 있어 정시 실행을 보장하지 않습니다. 공개 저장소는 60일 동안 활동이 없으면 예약 실행이 비활성화될 수 있습니다. 상태 저장 커밋만 믿지 말고 알림이 오지 않으면 Actions를 확인하세요. 비공개 저장소는 계정의 Actions 사용량 한도가 적용되므로 Billing에서 확인할 수 있습니다.

## 로컬 검증

```shell
python -m unittest discover -s tests -v
python bot.py --dry-run
```

실패 시 Actions 로그에서 실패 단계를 확인하세요. 네트워크/JSON 형식 문제는 공고 조회 단계, 토큰·개인 채팅 시작 문제는 전송 단계에서 확인할 수 있습니다. 실패한 실행 알림은 GitHub 알림 설정을 통해 받을 수 있습니다. 텔레그램 자체가 고장 나면 같은 경로로 장애 알림을 보장할 수 없습니다.

## 확인한 자료

- [서울시 모집공고](https://soco.seoul.go.kr/youth/bbs/BMSR00015/list.do?menuNo=400008)
- [GitHub 예약 실행](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Telegram 봇 만들기](https://core.telegram.org/bots/tutorial)
- [Telegram sendMessage](https://core.telegram.org/bots/api#sendmessage)
