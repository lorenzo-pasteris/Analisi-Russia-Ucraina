import unittest

import pandas as pd

from fetch_war import add_daily_deltas


class DailyDeltaTest(unittest.TestCase):
    def test_negative_revision_is_preserved(self):
        result = add_daily_deltas(pd.DataFrame({"drones": [100, 98, 103]}), ["drones"])
        self.assertEqual(result.daily_drones.iloc[1:].tolist(), [-2, 5])


if __name__ == "__main__":
    unittest.main()
