MIN_SERIAL_LENGTH = 12
MIN_DISTINCT_CHARS = 4
KNOWN_PLACEHOLDERS = {"0123456789ABCDEF"}


def is_trusted_serial(serial: str | None) -> bool:
    if not serial:
        return False
    if not serial.isascii() or not serial.isprintable():
        return False
    if len(serial) < MIN_SERIAL_LENGTH:
        return False
    if len(set(serial)) < MIN_DISTINCT_CHARS:
        return False
    return serial.upper() not in KNOWN_PLACEHOLDERS
