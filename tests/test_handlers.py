import unittest
from types import SimpleNamespace
from typing import Any, cast

from handlers import (
    MAX_PASSAGE_RESPONSE_MESSAGES,
    REQUEST_THROTTLE_MIN_INTERVAL_SECONDS,
    REQUEST_THROTTLE_WINDOW_SECONDS,
    count_passage_result_messages,
    enforce_request_throttle,
    get_request_throttle_retry_after,
    record_request_timestamp,
)


class HandlerGuardrailTests(unittest.TestCase):
    def test_count_passage_result_messages_counts_split_messages(self):
        paragraph = "x" * 3000
        count = count_passage_result_messages(
            [("John 3:16 NIV\n\n" + paragraph + "\n\n" + paragraph, None)]
        )
        self.assertEqual(2, count)

    def test_count_passage_result_messages_counts_parallel_chunks(self):
        paragraph = "x" * 3000
        count = count_passage_result_messages(
            [
                ("John 3:16 NIV\n\n" + paragraph + "\n\n" + paragraph, None),
                ("John 3:16 NRSVue\n\n" + paragraph + "\n\n" + paragraph, None),
                ("John 3:16 WLC\n\n" + paragraph + "\n\n" + paragraph, None),
            ]
        )
        self.assertGreater(count, MAX_PASSAGE_RESPONSE_MESSAGES)

    def test_count_passage_result_messages_collapses_small_parallel_responses(self):
        count = count_passage_result_messages(
            [
                ("John 3:16 NIV\n\nFor God so loved the world.", "https://niv"),
                ("John 3:16 NRSVue\n\nFor God so loved the world.", "https://nrsvue"),
            ]
        )
        self.assertEqual(1, count)

    def test_request_throttle_enforces_min_interval(self):
        user_data: dict[str, object] = {}
        chat_data: dict[str, object] = {}
        record_request_timestamp(user_data, chat_data, now=100.0)
        retry_after = get_request_throttle_retry_after(user_data, chat_data, now=100.5)
        assert retry_after is not None
        self.assertGreaterEqual(retry_after, 0.4)
        self.assertLessEqual(retry_after, REQUEST_THROTTLE_MIN_INTERVAL_SECONDS)

    def test_request_throttle_enforces_window_limit(self):
        user_data: dict[str, object] = {}
        chat_data: dict[str, object] = {}
        for timestamp in (100.0, 102.0, 104.0, 106.0):
            record_request_timestamp(user_data, chat_data, now=timestamp)
        retry_after = get_request_throttle_retry_after(user_data, chat_data, now=107.0)
        assert retry_after is not None
        self.assertGreater(retry_after, 0.0)
        self.assertLessEqual(retry_after, REQUEST_THROTTLE_WINDOW_SECONDS)

    def test_admin_user_is_exempt_from_throttle(self):
        update = cast(Any, SimpleNamespace(effective_user=SimpleNamespace(id=123)))
        context = cast(
            Any,
            SimpleNamespace(
                application=SimpleNamespace(
                    bot_data={"config": SimpleNamespace(admin_ids=frozenset({123}))}
                ),
                user_data={},
                chat_data={},
            ),
        )
        result = __import__("asyncio").run(
            enforce_request_throttle(update, context, silent=True)
        )
        self.assertTrue(result)
        self.assertEqual({}, context.user_data)
        self.assertEqual({}, context.chat_data)


if __name__ == "__main__":
    unittest.main()
