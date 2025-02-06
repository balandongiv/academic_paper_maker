import unittest
from research_filter.agent_helper import parse_ai_output
import json
class TestParseAIOutput(unittest.TestCase):
    def setUp(self):
        self.column_name = "test_column"

    def test_valid_json_string(self):
        # Test case for a valid JSON string
        ai_output = '{"key": "value"}'
        expected_output = {"key": "value"}
        result = parse_ai_output(ai_output, self.column_name)
        self.assertEqual(result, expected_output)

    def test_boolean_true(self):
        # Test case for 'True' as a string
        ai_output = "True"
        expected_output =  {self.column_name: ai_output}
        result = parse_ai_output(ai_output, self.column_name)
        json_path="test.json"
        with open(json_path, "w") as f:
            json.dump(ai_output, f, indent=2)


        self.assertEqual(result, expected_output)

    def test_boolean_false(self):
        # Test case for 'False' as a string
        ai_output = "False"
        expected_output =  {self.column_name: ai_output}
        result = parse_ai_output(ai_output, self.column_name)

        json_path="test.json"
        with open(json_path, "w") as f:
            json.dump(ai_output, f, indent=2)

        self.assertEqual(result, expected_output)

    # def test_null_value(self):
    #     # Test case for 'null' as a string
    #     ai_output = "null"
    #     expected_output = None
    #     result = parse_ai_output(ai_output, self.column_name)
    #     self.assertEqual(result, expected_output)

    def test_invalid_json_string(self):
        # Test case for an invalid JSON string
        ai_output = "'Invalid'"
        expected_output = {
            self.column_name: {
                "error_msg": "Error parsing JSON: 'Invalid'"
            }
        }
        result = parse_ai_output(ai_output, self.column_name)
        self.assertEqual(result, expected_output)

    def test_non_json_string(self):
        # Test case for a non-JSON string
        ai_output = "Just a string"
        expected_output = {
            self.column_name: {
                "error_msg": "Error parsing JSON: Just a string"
            }
        }
        result = parse_ai_output(ai_output, self.column_name)
        self.assertEqual(result, expected_output)

    def test_already_parsed_dict(self):
        # Test case for input that's already a dictionary
        ai_output = {"already": "parsed"}
        expected_output = {"already": "parsed"}


        result = parse_ai_output(ai_output, self.column_name)
        self.assertEqual(result, expected_output)

    def test_empty_string(self):
        # Test case for an empty string
        ai_output = ""
        expected_output = {
            self.column_name: {
                "error_msg": "Error parsing JSON: "
            }
        }
        result = parse_ai_output(ai_output, self.column_name)
        self.assertEqual(result, expected_output)

    def test_generic_exception(self):
        # Test case for a generic exception (e.g., unhandled data type)
        class Unserializable:
            pass

        ai_output = Unserializable()
        result = parse_ai_output(ai_output, self.column_name)
        self.assertIn("Unexpected error", result[self.column_name]["error_msg"])

if __name__ == "__main__":
    unittest.main()
