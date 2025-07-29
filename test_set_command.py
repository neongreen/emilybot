"""Test the .set command functionality."""

import pytest
from emilybot.javascript_executor import parse_javascript_code


def test_parse_javascript_code_plain_backticks():
    """Test parsing JavaScript code with plain triple backticks."""
    raw_code = """```
console.log("Hello World");
```"""
    expected = 'console.log("Hello World");'
    assert parse_javascript_code(raw_code) == expected


def test_parse_javascript_code_with_js_identifier():
    """Test parsing JavaScript code with js language identifier."""
    raw_code = """```js
console.log("Hello World");
```"""
    expected = 'console.log("Hello World");'
    assert parse_javascript_code(raw_code) == expected


def test_parse_javascript_code_with_javascript_identifier():
    """Test parsing JavaScript code with javascript language identifier."""
    raw_code = """```javascript
console.log("Hello World");
```"""
    expected = 'console.log("Hello World");'
    assert parse_javascript_code(raw_code) == expected


def test_parse_javascript_code_no_backticks():
    """Test parsing JavaScript code without backticks."""
    raw_code = 'console.log("Hello World");'
    expected = 'console.log("Hello World");'
    assert parse_javascript_code(raw_code) == expected


def test_parse_javascript_code_multiline():
    """Test parsing multiline JavaScript code."""
    raw_code = """```js
console.log("Line 1");
console.log("Line 2");
console.log("Line 3");
```"""
    expected = """console.log("Line 1");
console.log("Line 2");
console.log("Line 3");"""
    assert parse_javascript_code(raw_code) == expected


def test_parse_javascript_code_empty_after_parsing():
    """Test parsing JavaScript code that becomes empty after parsing."""
    raw_code = """```js
```"""
    expected = ""
    assert parse_javascript_code(raw_code) == expected


def test_parse_javascript_code_with_whitespace():
    """Test parsing JavaScript code with extra whitespace."""
    raw_code = """  ```js
  console.log("Hello World");
  ```  """
    expected = 'console.log("Hello World");'
    assert parse_javascript_code(raw_code) == expected


if __name__ == "__main__":
    pytest.main([__file__])


def test_set_command_validation():
    """Test validation logic for the set command."""
    from emilybot.commands.set import (
        format_not_found_message,
        format_validation_error,
        format_success_message,
    )

    # Test message formatting
    assert "not found" in format_not_found_message("test", ".")
    assert "❌" in format_validation_error("Test error")
    assert "✅" in format_success_message("test", ".run")
    assert "test" in format_success_message("test", ".run")
    assert ".run" in format_success_message("test", ".run")


def test_javascript_code_cleaning_edge_cases():
    """Test edge cases in JavaScript code cleaning."""
    # Test code with only language identifier
    raw_code = """```js
```"""
    expected = ""
    assert parse_javascript_code(raw_code) == expected

    # Test code with content on same line as language identifier
    raw_code = """```js console.log("test");
```"""
    expected = 'console.log("test");'
    assert parse_javascript_code(raw_code) == expected

    # Test code with unknown language identifier (should be preserved)
    raw_code = """```python
console.log("test");
```"""
    expected = """python
console.log("test");"""
    assert parse_javascript_code(raw_code) == expected
