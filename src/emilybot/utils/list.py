from typing import Callable, Iterable


def first[T](iterable: list[T]) -> T | None:
    """Return the first element of a list or None if empty."""
    return iterable[0] if iterable else None


def sorted_by_order[T, K](
    xs: Iterable[T],
    *,
    key: Callable[[T], K],
    key_order: list[K],
) -> list[T]:
    """Return a sorted list where elements from `order` come first and in the given order, followed by the rest."""

    # Separate elements that are in the order list from those that aren't
    in_order: list[T] = []
    rest: list[T] = []

    # Create a mapping of key values to their position in key_order for efficient lookup
    order_index = {value: i for i, value in enumerate(key_order)}

    # Separate elements based on whether their key is in key_order
    for item in xs:
        item_key = key(item)
        if item_key in order_index:
            in_order.append(item)
        else:
            rest.append(item)

    # Sort in_order elements by their position in key_order
    in_order.sort(key=lambda item: order_index[key(item)])

    # Sort the rest normally by their key
    rest.sort(key=key)  # type: ignore

    # Combine the results
    return in_order + rest
