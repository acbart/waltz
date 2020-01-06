import sys
from waltz.command_line import parse_command_line


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = parse_command_line(args)


if __name__ == '__main__':
    main()
