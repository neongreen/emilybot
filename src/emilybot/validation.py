"""Validation utilities for Discord memory bot."""

from typing import Literal, assert_never
import re

from emilybot.utils.inflect import inflect


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class AliasValidator:
    """Validator for alias format and constraints."""

    # Alias constraints from requirements
    MIN_LENGTH = 2
    MAX_LENGTH = 100
    VALID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-./]+$")

    @staticmethod
    def validate_alias(
        alias: str, purpose: Literal["create", "lookup", "lookup_no_endslash"]
    ) -> None:
        """
        Validate alias format and length.

        Args:
            alias: The alias to validate
            purpose: `create` allows only aliases that can be created; `lookup` also allows things like `dir/`;
              `lookup_no_endslash` is for lookups that cannot handle dirs

        Raises:
            ValidationError: If alias is invalid
        """
        if not alias:
            raise ValidationError("Alias cannot be empty")

        if len(alias) < AliasValidator.MIN_LENGTH:
            raise ValidationError(
                inflect(
                    f"Alias must be at least no('character', {AliasValidator.MIN_LENGTH}) long"
                )
            )

        if len(alias) > AliasValidator.MAX_LENGTH:
            raise ValidationError(
                f"Alias cannot exceed {AliasValidator.MAX_LENGTH} characters"
            )

        if not AliasValidator.VALID_PATTERN.match(alias):
            raise ValidationError(
                "Alias can only contain alphanumeric characters, underscores, dashes, dots, and slashes"
            )

        match purpose:
            case "create" | "lookup_no_endslash":
                if not re.match(r"^[a-zA-Z0-9_].*[a-zA-Z0-9_]$", alias):
                    raise ValidationError(
                        "Alias must start and end with a letter, digit, or _"
                    )
            case "lookup":
                if not re.match(r"^[a-zA-Z0-9_].*$", alias):
                    raise ValidationError("Alias must start with a letter, digit, or _")
                if not re.match(r"^.*[a-zA-Z0-9_/]$", alias):
                    raise ValidationError(
                        "Alias to lookup must end with a letter, digit, _, or /"
                    )
            case _:
                assert_never(purpose)
