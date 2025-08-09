"""Validation utilities for Discord memory bot."""

import re

from emilybot.utils.inflect import inflect


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


# Validation constraints
MIN_LENGTH = 2
MAX_LENGTH = 100
VALID_PATTERN = re.compile(r"^[a-zA-Z0-9_/\-]+$")


def get_path_components(
    path: str, *, normalize_dots: bool = False, normalize_dashes: bool = False
) -> list[str]:
    """
    Get path components by splitting on slashes, with optional normalization.

    Args:
        path: The path string to split
        normalize_dots: Whether to normalize dots (replace with slashes)
        normalize_dashes: Whether to normalize dashes (replace with underscores)

    Returns:
        List of path components

    Examples:
        >>> get_path_components("foo/bar")
        ['foo', 'bar']
        >>> get_path_components("foo.bar", normalize_dots=True)
        ['foo', 'bar']
        >>> get_path_components("foo-bar", normalize_dashes=True)
        ['foo_bar']
    """
    normalized_path = path

    if normalize_dots:
        normalized_path = normalized_path.replace(".", "/")

    if normalize_dashes:
        normalized_path = normalized_path.replace("-", "_")

    # Split on slashes and filter out empty components
    components = [comp for comp in normalized_path.split("/") if comp]

    return components


def get_top_level_name(
    path: str, *, normalize_dots: bool = False, normalize_dashes: bool = False
) -> str:
    """
    Get the top-level name from a path.

    Args:
        path: The path string
        normalize_dots: Whether to normalize dots (replace with slashes)
        normalize_dashes: Whether to normalize dashes (replace with underscores)

    Returns:
        The top-level component of the path

    Examples:
        >>> get_top_level_name("foo/bar")
        'foo'
        >>> get_top_level_name("foo.bar", normalize_dots=True)
        'foo'
        >>> get_top_level_name("foo")
        'foo'
    """
    components = get_path_components(
        path, normalize_dots=normalize_dots, normalize_dashes=normalize_dashes
    )
    return components[0] if components else ""


def has_trailing_slash(path: str) -> bool:
    """
    Check if a path has a trailing slash.

    Args:
        path: The path string

    Returns:
        True if the path ends with a slash, False otherwise

    Examples:
        >>> has_trailing_slash("foo/")
        True
        >>> has_trailing_slash("foo")
        False
        >>> has_trailing_slash("foo/bar/")
        True
    """
    return path.endswith("/")


def is_child_path(
    parent: str,
    child: str,
    *,
    normalize_dots: bool = False,
    normalize_dashes: bool = False,
) -> bool:
    """
    Check if a path is a child of another path.

    Args:
        parent: The parent path
        child: The child path to check
        normalize_dots: Whether to normalize dots (replace with slashes)
        normalize_dashes: Whether to normalize dashes (replace with underscores)

    Returns:
        True if child is a direct child of parent, False otherwise

    Examples:
        >>> is_child_path("foo", "foo/bar")
        True
        >>> is_child_path("foo", "foo/bar/baz")
        False
        >>> is_child_path("foo", "bar")
        False
        >>> is_child_path("foo", "foo.bar", normalize_dots=True)
        True
    """
    parent_components = get_path_components(
        parent, normalize_dots=normalize_dots, normalize_dashes=normalize_dashes
    )
    child_components = get_path_components(
        child, normalize_dots=normalize_dots, normalize_dashes=normalize_dashes
    )

    if len(child_components) != len(parent_components) + 1:
        return False

    return child_components[: len(parent_components)] == parent_components


def validate_path(
    path: str,
    *,
    allow_trailing_slash: bool = False,
    normalize_dots: bool = False,
    normalize_dashes: bool = False,
    check_component_length: bool = True,
) -> str:
    """
    Validate path components by splitting on slashes and checking each component.

    Args:
        path: The path string to validate
        allow_trailing_slash: Whether to allow trailing slashes
        normalize_dots: Whether to normalize dots (replace with slashes)
        normalize_dashes: Whether to normalize dashes (replace with underscores)
        check_component_length: Whether to check component length constraints

    Returns:
        The normalized path string

    Raises:
        ValidationError: If any path component is invalid

    Examples:
        >>> validate_path("user/data")  # Valid path
        'user/data'
        >>> validate_path("dir/", allow_trailing_slash=True)  # Valid - empty last component allowed
        'dir/'
        >>> validate_path("user//data")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ValidationError: Path components cannot be empty
        >>> validate_path("_user/data")  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ValidationError: Path components cannot start with underscore
        >>> validate_path("user/data/", allow_trailing_slash=True)
        'user/data/'
        >>> validate_path("a", check_component_length=True)  # doctest: +IGNORE_EXCEPTION_DETAIL
        Traceback (most recent call last):
        ValidationError: Path component must be at least no('character', 2) long
        >>> validate_path("foo.bar", normalize_dots=True)
        'foo/bar'
        >>> validate_path("foo-bar", normalize_dashes=True)
        'foo_bar'
    """
    if not path:
        raise ValidationError("Path cannot be empty")

    # Apply normalizations
    normalized_path = path

    if normalize_dots:
        normalized_path = normalized_path.replace(".", "/")

    if normalize_dashes:
        normalized_path = normalized_path.replace("-", "_")

    # Check for consecutive slashes (which create empty components)
    if "//" in normalized_path:
        raise ValidationError("Path components cannot be empty")

    # Split on slashes and filter out empty strings (but keep track of trailing slash)
    components: list[str] = normalized_path.split("/")
    has_trailing_slash = normalized_path.endswith("/")

    # Remove empty components from the middle, but preserve the last one if it's empty due to trailing slash
    filtered_components: list[str] = []
    for i, component in enumerate(components):
        if component or (i == len(components) - 1 and has_trailing_slash):
            filtered_components.append(component)

    # Validate each component
    for i, component in enumerate(filtered_components):
        is_last_component = i == len(filtered_components) - 1

        # Check if component is empty (only allowed for last component if allow_trailing_slash is True)
        if not component:
            if allow_trailing_slash and is_last_component:
                continue  # Allow empty last component when trailing slash is allowed
            else:
                raise ValidationError("Path components cannot be empty")

        # Check that component doesn't start with underscore
        if component.startswith("_"):
            raise ValidationError("Path components cannot start with underscore")

        # Apply validation rules to each component
        if check_component_length:
            if len(component) < MIN_LENGTH:
                raise ValidationError(
                    inflect(
                        f"Path component must be at least no('character', {MIN_LENGTH}) long"
                    )
                )

            if len(component) > MAX_LENGTH:
                raise ValidationError(
                    f"Path component cannot exceed {MAX_LENGTH} characters"
                )

        if not VALID_PATTERN.match(component):
            raise ValidationError(
                "Path components can only contain alphanumeric characters and `_`, `-`, or `/`"
            )

        # All components must start with a letter or digit
        if not re.match(r"^[a-zA-Z0-9].*", component):
            raise ValidationError("Path components must start with a letter or digit")

    return normalized_path
