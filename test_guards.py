import unittest

from dingtalk_ai_table.guards import (
    validate_field_batch,
    validate_get_fields_batch,
    validate_get_tables_batch,
    validate_record_batch,
)


class TestBatchValidators(unittest.TestCase):
    def test_empty_record_batch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "批量参数必须是非空数组"):
            validate_record_batch([])

    def test_empty_field_batch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "批量参数必须是非空数组"):
            validate_field_batch([])

    def test_empty_get_tables_batch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "批量参数必须是非空数组"):
            validate_get_tables_batch([])

    def test_empty_get_fields_batch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "批量参数必须是非空数组"):
            validate_get_fields_batch([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
