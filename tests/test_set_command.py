"""Test the .set command functionality."""

from emilybot.javascript_executor import extract_js_code


def test_extract_js_code_plain_backticks():
    """Test parsing JavaScript code with plain triple backticks."""
    raw_code = """```
console.log("Hello World");
```"""
    expected = 'console.log("Hello World");'
    assert extract_js_code(raw_code) == expected


def test_extract_js_code_with_js_identifier():
    """Test parsing JavaScript code with js language identifier."""
    raw_code = """```js
console.log("Hello World");
```"""
    expected = 'console.log("Hello World");'
    assert extract_js_code(raw_code) == expected


def test_extract_js_code_with_javascript_identifier():
    """Test parsing JavaScript code with javascript language identifier."""
    raw_code = """```javascript
console.log("Hello World");
```"""
    expected = 'console.log("Hello World");'
    assert extract_js_code(raw_code) == expected


def test_extract_js_code_no_backticks():
    """Test parsing JavaScript code without backticks."""
    raw_code = 'console.log("Hello World");'
    expected = 'console.log("Hello World");'
    assert extract_js_code(raw_code) == expected


def test_extract_js_code_multiline():
    """Test parsing multiline JavaScript code."""
    raw_code = """```js
console.log("Line 1");
console.log("Line 2");
console.log("Line 3");
```"""
    expected = """console.log("Line 1");
console.log("Line 2");
console.log("Line 3");"""
    assert extract_js_code(raw_code) == expected


def test_extract_js_code_empty_after_parsing():
    """Test parsing JavaScript code that becomes empty after parsing."""
    raw_code = """```js
```"""
    expected = ""
    assert extract_js_code(raw_code) == expected


def test_extract_js_code_with_whitespace():
    """Test parsing JavaScript code with extra whitespace."""
    raw_code = """  ```js
  console.log("Hello World");
  ```  """
    expected = 'console.log("Hello World");'
    assert extract_js_code(raw_code) == expected
