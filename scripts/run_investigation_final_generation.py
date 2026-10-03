"""Run the frozen 384-position final generation. Does not score or replay."""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from investigation_final_offline.execute import resume, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key-file', default=str(ROOT / 'api_key.txt'))
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.resume:
        resume(args.key_file)
    else:
        run(args.key_file)


if __name__ == '__main__':
    main()
