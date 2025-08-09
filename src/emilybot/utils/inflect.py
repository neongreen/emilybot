import inflect as i

_inflect = i.engine()


def inflect(text: str) -> str:
    """
    Example:

    >>> inflect("I saw no('duck', 5)")
    'I saw 5 ducks'
    """

    return _inflect.inflect(text)  # type: ignore
