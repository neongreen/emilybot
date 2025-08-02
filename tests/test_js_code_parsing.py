#!/usr/bin/env python3
"""Unit tests for JavaScript code parsing functionality."""

import unittest

from emilybot.execute.javascript_executor import extract_js_code


class TestCodeParsing(unittest.TestCase):
    """Test cases for JavaScript code parsing functionality."""

    def test_plain_code_without_backticks(self):
        """Test parsing plain JavaScript code without backticks."""
        input_code = "console.log('hello');"
        expected = "console.log('hello');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_plain_triple_backticks(self):
        """Test parsing code wrapped in plain triple backticks."""
        input_code = "```\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_js_language_identifier(self):
        """Test parsing code with 'js' language identifier."""
        input_code = "```js\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_javascript_language_identifier(self):
        """Test parsing code with 'javascript' language identifier."""
        input_code = "```javascript\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_multiline_code_with_backticks(self):
        """Test parsing multi-line JavaScript code with backticks."""
        input_code = "```js\nconsole.log('line 1');\nconsole.log('line 2');\n```"
        expected = "console.log('line 1');\nconsole.log('line 2');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_code_with_extra_whitespace(self):
        """Test parsing code with extra whitespace around backticks."""
        input_code = "  ```js  \n  console.log('hello');  \n  ```  "
        expected = "console.log('hello');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_empty_language_identifier(self):
        """Test parsing code with empty language identifier line."""
        input_code = "```\nconsole.log('hello');\n```"
        expected = "console.log('hello');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_language_identifier_on_separate_line(self):
        """Test parsing code with language identifier on separate line."""
        input_code = "```js\nconsole.log('hello');\nconsole.log('world');\n```"
        expected = "console.log('hello');\nconsole.log('world');"
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)

    def test_empty_code_block(self):
        """Test parsing empty code block."""
        input_code = "```js\n```"
        expected = ""
        result = extract_js_code(input_code)
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
        result = extract_js_code(input_code)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
