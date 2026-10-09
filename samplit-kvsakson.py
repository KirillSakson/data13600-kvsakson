# randomly sample 1% of the lines of a file preserving order

import random
import sys


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <filename>", file=sys.stderr)
        sys.exit(1)

    filename = sys.argv[1]
    try:
        with open(filename, "r") as f:
            for line in f:
                if random.random() < 0.01:
                    sys.stdout.write(line)
    except OSError as e:
        print(f"Error: cannot read '{filename}': {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
