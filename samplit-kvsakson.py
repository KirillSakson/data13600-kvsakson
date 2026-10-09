# randomly sample a line (preserving order) with 1% probability from the given file

import random
import sys


def main():
    if len(sys.argv) != 2:
        print(f"Use the script as follows: {sys.argv[0]} <filename>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r") as file:
            for line in file:
                if random.random() < 0.01:
                    sys.stdout.write(line)
    except OSError as e:
        print(f"Error: can't read '{path}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
