def exponential_fn(base, exponent):
    """
    Calculates the exponential function (base to the power of exponent).

    Args:
        base (int, float): The base number.
        exponent (int, float): The exponent.

    Returns:
        int or float: The result of base ** exponent.

    Raises:
        TypeError: If base or exponent are not numeric types.
    """
    if not isinstance(base, (int, float)):
        raise TypeError("Base must be a numeric type.")
    if not isinstance(exponent, (int, float)):
        raise TypeError("Exponent must be a numeric type.")

    return base ** exponent