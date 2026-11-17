from importlib.metadata import version


def main() -> int:
    print(f"campermit {version('campermit')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
