def first[T](iterable: list[T]) -> T | None:
    """Return the first element of a list or None if empty."""
    return iterable[0] if iterable else None
