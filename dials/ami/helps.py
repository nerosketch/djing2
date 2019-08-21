def safe_float(fl: float) -> float:
    try:
        return 0.0 if not fl else float(fl)
    except (ValueError, OverflowError):
        return 0.0


def safe_int(i: int) -> int:
    try:
        return 0 if not i else int(i)
    except (ValueError, OverflowError):
        return 0
