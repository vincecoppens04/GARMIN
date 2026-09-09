import unittest
from tests.test_models import (
    test_day_record_creation_and_properties,
    test_activity_record_creation_and_supabase_dict,
    test_user_baselines_from_row,
)
from tests.test_calculators import (
    test_sleep_ledger_and_bedtime,
    test_activity_strain,
    test_target_strain_window,
    test_workout_prescriber,
    test_caffeine_clearance,
    test_circadian_windows,
    test_acwr,
    test_training_monotony,
)

class TestDomainModels(unittest.TestCase):
    def test_day_record_lifecycle(self):
        test_day_record_creation_and_properties()

    def test_activity_record_serialization(self):
        test_activity_record_creation_and_supabase_dict()

    def test_user_baselines_hydration(self):
        test_user_baselines_from_row()

class TestDomainCalculators(unittest.TestCase):
    def test_sleep_ledger_and_bedtime(self):
        test_sleep_ledger_and_bedtime()

    def test_activity_strain(self):
        test_activity_strain()

    def test_target_strain_window(self):
        test_target_strain_window()

    def test_workout_prescriber(self):
        test_workout_prescriber()

    def test_caffeine_clearance(self):
        test_caffeine_clearance()

    def test_circadian_windows(self):
        test_circadian_windows()

    def test_acwr(self):
        test_acwr()

    def test_training_monotony(self):
        test_training_monotony()

if __name__ == "__main__":
    unittest.main(verbosity=2)
