"""Validation utilities for Discord memory bot."""

import re

from emilybot.utils.inflect import inflect


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


# Validation constraints
MIN_LENGTH = 2
MAX_LENGTH = 100


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
        >>> validate_path("foo")
        'foo'
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

    # Split on slashes and check for empty components
    components: list[str] = normalized_path.split("/")

    # Validate each component
    for i, component in enumerate(components):
        is_last_component = i == len(components) - 1

        # Skip empty last component if trailing slash is allowed
        if not component and is_last_component and allow_trailing_slash:
            continue

        # Check that component doesn't start with underscore
        if component.startswith("_"):
            raise ValidationError(
                f"Commands and subcommands cannot start with underscore, got {repr(component)}"
            )

        # Apply validation rules to each component
        if check_component_length:
            if len(component) < MIN_LENGTH:
                raise ValidationError(
                    inflect(
                        f"Command and subcommand names must be at least no('character', {MIN_LENGTH}) long, got {repr(component)}"
                    )
                )

            if len(component) > MAX_LENGTH:
                raise ValidationError(
                    f"Command and subcommand names cannot exceed {MAX_LENGTH} characters, got {repr(component)}"
                )

        # All components must start with a letter or digit
        if not re.match(r"^[a-zA-Z0-9]", component):
            raise ValidationError(
                f"Command and subcommand names must start with a letter or digit, got {repr(component)}"
            )

        # All components must end with a letter or digit
        if not re.match(r".*[a-zA-Z0-9]$", component):
            raise ValidationError(
                f"Command and subcommand names must end with a letter or digit, got {repr(component)}"
            )

        # All components must contain only alphanumeric characters, underscores, or hyphens
        if not re.match(r"^[a-zA-Z0-9_-]+$", component):
            raise ValidationError(
                f"Command and subcommand names can only contain letters, digits, underscores, or hyphens, got {repr(component)}"
            )

        # Component cannot be just a number
        if re.match(r"^\d+$", component):
            raise ValidationError(
                f"Command and subcommand names cannot be just a number, got {repr(component)}"
            )

        # Only the first component can start with a number
        if i > 0 and re.match(r"^\d", component):
            raise ValidationError(
                f"Subcommand names cannot start with a number, got {repr(component)}"
            )

    return normalized_path
