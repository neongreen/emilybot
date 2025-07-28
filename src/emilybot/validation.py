"""Validation utilities for Discord memory bot."""

import re


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class AliasValidator:
    """Validator for alias format and constraints."""

    # Alias constraints from requirements
    MIN_LENGTH = 1
    MAX_LENGTH = 100
    VALID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-./]+$")

    @staticmethod
    def validate_alias(alias: str) -> None:
        """
        Validate alias format and length.

        Args:
            alias: The alias to validate

        Raises:
            ValidationError: If alias is invalid
        """
        if not alias:
            raise ValidationError("Alias cannot be empty")

        if len(alias) < AliasValidator.MIN_LENGTH:
            raise ValidationError(
                f"Alias must be at least {AliasValidator.MIN_LENGTH} character long"
            )

        if len(alias) > AliasValidator.MAX_LENGTH:
            raise ValidationError(
                f"Alias cannot exceed {AliasValidator.MAX_LENGTH} characters"
            )

        if not AliasValidator.VALID_PATTERN.match(alias):
            raise ValidationError(
                "Alias can only contain alphanumeric characters, underscores, dashes, dots, and slashes"
            )

        if not re.match(r".*[\w-]$", alias) or not re.match(r"^[\w-].*", alias):
            raise ValidationError(
                "Alias must start and end with a letter, number, or _"
            )


class ContentValidator:
    """Validator for content constraints."""

    # Content constraints from requirements
    MIN_LENGTH = 1
    MAX_LENGTH = 1000

    @staticmethod
    def validate_content(content: str) -> None:
        """
        Validate content length and emptiness.

        Args:
            content: The content to validate

        Raises:
            ValidationError: If content is invalid
        """
        if not content or not content.strip():
            raise ValidationError("Content cannot be empty")

        if len(content) < ContentValidator.MIN_LENGTH:
            raise ValidationError(
                f"Content must be at least {ContentValidator.MIN_LENGTH} character long"
            )

        if len(content) > ContentValidator.MAX_LENGTH:
            raise ValidationError(
                f"Content cannot exceed {ContentValidator.MAX_LENGTH} characters"
            )
