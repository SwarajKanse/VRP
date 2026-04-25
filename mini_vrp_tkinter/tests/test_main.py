from unittest import TestCase

from mini_vrp_tkinter.main import next_order_id


class MainTests(TestCase):
    def test_next_order_id_skips_removed_slots(self) -> None:
        self.assertEqual(
            next_order_id(["order-1", "order-3", "order-4"]),
            "order-5",
        )

    def test_next_order_id_ignores_nonstandard_ids(self) -> None:
        self.assertEqual(
            next_order_id(["custom-a", "order-2", "order-7"]),
            "order-8",
        )
