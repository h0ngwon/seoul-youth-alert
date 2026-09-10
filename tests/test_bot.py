from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import bot


def row(content, start="2026-09-10"):
    return {"boardId": 6665, "nttSj": "테스트 공고", "optn1": "2026-09-10",
            "optn4": start, "content": content}


class BotTests(unittest.TestCase):
    def test_today_included(self):
        self.assertIn("오늘 청약신청일", bot.entry(row(""), date(2026, 9, 10), 7))

    def test_seven_days_inclusive(self):
        self.assertIn("D-7", bot.entry(row("", "2026-09-17"), date(2026, 9, 10), 7))
        self.assertIsNone(bot.entry(row("", "2026-09-18"), date(2026, 9, 10), 7))

    def test_past_excluded_even_if_body_says_open(self):
        self.assertIsNone(bot.entry(row("청약신청: 2026.09.09 ~ 09.15", "2026-09-09"), date(2026, 9, 10), 7))

    def test_uses_application_date_not_posted_date(self):
        item = row("", "2026-09-15")
        item["optn1"] = "2026-08-01"
        self.assertIn("D-5", bot.entry(item, date(2026, 9, 10), 7))

    def test_invalid_dates_reported(self):
        for value in ["", None, "수시모집", "2026-02-30"]:
            self.assertIsNone(bot.entry(row("", value), date(2026, 9, 10), 7))
        self.assertIn("날짜 형식 확인이 필요한 공고 1건", bot.digest([row("", "미정")], date(2026, 9, 10), 7)[0])

    def test_long_digest_split(self):
        items = [row("<p>청약신청: ‘26.09.10 ~ 09.14</p>") for _ in range(50)]
        messages = bot.digest(items, date(2026, 9, 10), 7)
        self.assertGreater(len(messages), 1)
        self.assertTrue(all(len(m.encode("utf-16-le")) // 2 < 4096 for m in messages))

    def test_success_saved_failed_delivery_not_saved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(bot, "STATE", Path(directory) / "state.json"), patch.object(bot.time, "sleep"):
            with patch.object(bot, "send_message", side_effect=[None, RuntimeError("failure")]):
                with self.assertRaises(RuntimeError):
                    bot.deliver(["one", "two"], date(2026, 9, 10), "token", "chat")
            with patch.object(bot, "send_message") as send:
                bot.deliver(["one", "two"], date(2026, 9, 10), "token", "chat")
                send.assert_called_once_with("token", "chat", "two")
            with patch.object(bot, "send_message") as send:
                bot.deliver(["one", "two"], date(2026, 9, 11), "token", "chat")
                self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
