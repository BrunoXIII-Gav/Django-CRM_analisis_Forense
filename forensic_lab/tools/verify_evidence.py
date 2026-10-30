import argparse
from case_io import case_path, verify


def main():
    parser = argparse.ArgumentParser()
    for arg in ("root", "case", "operator"):
        parser.add_argument("--" + arg, required=True)
    args = parser.parse_args()
    try:
        entries = verify(case_path(args.root, args.case), args.operator)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, str(error) + "\n")
    print(f"original: OK; trabajo: OK; {len(entries)} files each")


if __name__ == "__main__":
    main()
