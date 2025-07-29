#!/usr/bin/env python3
"""Unit tests for JavaScript code parsing functionality."""

import unittest
import sys
import uuid
from pathlib import Path

# Add src to path so we can import emilybot modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from emilybot.javascript_executor import (
    parse_javascript_code,
    create_context_from_entry,
)
from emilybot.database import Entry


class TestCodeParsing(unittest.TestCase):
    """Test cases for JavaScript code parsing functionality."""

    def test_plain_code_without_backticks(self):
        """Test parsing plain JavaScript code without backticks."""
        input_code = "console.log('hello');"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_plain_triple_backticks(self):
        """Test parsing code wrapped in plain triple backticks."""
        input_code = "```\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_js_language_identifier(self):
        """Test parsing code with 'js' language identifier."""
        input_code = "```js\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_javascript_language_identifier(self):
        """Test parsing code with 'javascript' language identifier."""
        input_code = "```javascript\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_multiline_code_with_backticks(self):
        """Test parsing multi-line JavaScript code with backticks."""
        input_code = "```js\nconsole.log('line 1');\nconsole.log('line 2');\n```"
        expected = "console.log('line 1');\nconsole.log('line 2');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_extra_whitespace(self):
        """Test parsing code with extra whitespace around backticks."""
        input_code = "  ```js  \n  console.log('hello');  \n  ```  "
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_empty_language_identifier(self):
        """Test parsing code with empty language identifier line."""
        input_code = "```\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_language_identifier_on_same_line_js(self):
        """Test parsing code with 'js' identifier on same line as code."""
        input_code = "```js console.log('hello');\n```"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_language_identifier_on_same_line_javascript(self):
        """Test parsing code with 'javascript' identifier on same line as code."""
        input_code = "```javascript console.log('hello');\n```"
        expected = "console.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_language_identifier_on_separate_line(self):
        """Test parsing code with language identifier on separate line."""
        input_code = "```js\nconsole.log('hello');\nconsole.log('world');\n```"
        expected = "console.log('hello');\nconsole.log('world');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_empty_code_block(self):
        """Test parsing empty code block."""
        input_code = "```js\n```"
        expected = ""
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_code_block_with_only_language_identifier(self):
        """Test parsing code block with only language identifier."""
        input_code = "```\njs\n```"
        expected = ""
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_complex_multiline_code(self):
        """Test parsing complex multi-line JavaScript code."""
        input_code = """```javascript
function greet(name) {
    console.log('Hello, ' + name + '!');
}
greet(context.name);
```"""
        expected = """function greet(name) {
    console.log('Hello, ' + name + '!');
}
greet(context.name);"""
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_backticks_inside_strings(self):
        """Test parsing code that contains backticks inside string literals."""
        input_code = "```js\nconsole.log('This has ``` inside');\n```"
        expected = "console.log('This has ``` inside');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_case_insensitive_language_identifiers(self):
        """Test that language identifiers are case insensitive."""
        test_cases = [
            ("```JS\nconsole.log('hello');\n```", "console.log('hello');"),
            ("```JavaScript\nconsole.log('hello');\n```", "console.log('hello');"),
            ("```JAVASCRIPT\nconsole.log('hello');\n```", "console.log('hello');"),
        ]

        for input_code, expected in test_cases:
            with self.subTest(input_code=input_code):
                result = parse_javascript_code(input_code)
                self.assertEqual(result, expected)

    def test_edge_case_no_closing_backticks(self):
        """Test edge case where opening backticks exist but no closing backticks."""
        input_code = "```js\nconsole.log('hello');"
        expected = "```js\nconsole.log('hello');"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_edge_case_only_opening_backticks(self):
        """Test edge case with only opening backticks."""
        input_code = "```"
        expected = "```"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)

    def test_edge_case_only_closing_backticks(self):
        """Test edge case with only closing backticks."""
        input_code = "console.log('hello');\n```"
        expected = "console.log('hello');\n```"
        result = parse_javascript_code(input_code)
        self.assertEqual(result, expected)


class TestContextCreation(unittest.TestCase):
    """Test cases for context object generation from Entry data."""

    def test_basic_context_creation(self):
        """Test creating context from a basic Entry object."""
        entry = Entry(
            id=uuid.uuid4(),
            server_id=12345,
            user_id=67890,
            created_at="2025-01-29T12:00:00Z",
            name="test-entry",
            content="This is test content",
            promoted=False,
            run=None,
        )

        context = create_context_from_entry(entry)

        expected_context = {
            "content": "This is test content",
            "name": "test-entry",
            "created_at": "2025-01-29T12:00:00Z",
            "user_id": 67890,
        }

        self.assertEqual(context, expected_context)

    def test_context_creation_with_none_server_id(self):
        """Test creating context from Entry with None server_id (DM entry)."""
        entry = Entry(
            id=uuid.uuid4(),
            server_id=None,
            user_id=98765,
            created_at="2025-01-29T15:30:45Z",
            name="dm-entry",
            content="Direct message content",
            promoted=True,
            run="console.log('test');",
        )

        context = create_context_from_entry(entry)

        expected_context = {
            "content": "Direct message content",
            "name": "dm-entry",
            "created_at": "2025-01-29T15:30:45Z",
            "user_id": 98765,
        }

        self.assertEqual(context, expected_context)

    def test_context_creation_with_special_characters(self):
        """Test creating context from Entry with special characters in content."""
        entry = Entry(
            id=uuid.uuid4(),
            server_id=54321,
            user_id=11111,
            created_at="2025-01-29T08:15:30Z",
            name="special-chars",
            content="Content with 'quotes', \"double quotes\", and \n newlines \t tabs",
            promoted=False,
            run=None,
        )

        context = create_context_from_entry(entry)

        expected_context = {
            "content": "Content with 'quotes', \"double quotes\", and \n newlines \t tabs",
            "name": "special-chars",
            "created_at": "2025-01-29T08:15:30Z",
            "user_id": 11111,
        }

        self.assertEqual(context, expected_context)

    def test_context_creation_with_empty_content(self):
        """Test creating context from Entry with empty content."""
        entry = Entry(
            id=uuid.uuid4(),
            server_id=99999,
            user_id=22222,
            created_at="2025-01-29T20:45:15Z",
            name="empty-content",
            content="",
            promoted=False,
            run=None,
        )

        context = create_context_from_entry(entry)

        expected_context = {
            "content": "",
            "name": "empty-content",
            "created_at": "2025-01-29T20:45:15Z",
            "user_id": 22222,
        }

        self.assertEqual(context, expected_context)

    def test_context_creation_with_long_content(self):
        """Test creating context from Entry with very long content."""
        long_content = "This is a very long content string. " * 100
        entry = Entry(
            id=uuid.uuid4(),
            server_id=77777,
            user_id=33333,
            created_at="2025-01-29T14:20:10Z",
            name="long-content",
            content=long_content,
            promoted=True,
            run=None,
        )

        context = create_context_from_entry(entry)

        expected_context = {
            "content": long_content,
            "name": "long-content",
            "created_at": "2025-01-29T14:20:10Z",
            "user_id": 33333,
        }

        self.assertEqual(context, expected_context)

    def test_context_excludes_internal_fields(self):
        """Test that context only includes the expected fields and excludes internal ones."""
        entry = Entry(
            id=uuid.uuid4(),
            server_id=88888,
            user_id=44444,
            created_at="2025-01-29T16:10:25Z",
            name="test-exclusion",
            content="Test content",
            promoted=True,
            run="console.log('test');",
        )

        context = create_context_from_entry(entry)

        # Verify only expected keys are present
        expected_keys = {"content", "name", "created_at", "user_id"}
        actual_keys = set(context.keys())
        self.assertEqual(actual_keys, expected_keys)

        # Verify internal fields are not included
        self.assertNotIn("id", context)
        self.assertNotIn("server_id", context)
        self.assertNotIn("promoted", context)
        self.assertNotIn("run", context)


if __name__ == "__main__":
    unittest.main()
