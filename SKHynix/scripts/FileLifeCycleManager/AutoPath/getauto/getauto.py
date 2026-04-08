#!/usr/bin/env python3

import argparse
import os
import sys

BASE_DIR = "/etc/auto"   # 필요시 수정

def read_auto_file(target, base_dir):
    file_path = os.path.join(base_dir, target)

    if not os.path.exists(file_path):
        print(f"getauto: {target}: not found", file=sys.stderr)
        sys.exit(1)

    with open(file_path) as f:
        return [line.strip() for line in f if line.strip()]


def filter_lines(lines, alias=None, path=None, keyword=None):
    result = []

    for line in lines:

        # header 항상 포함
        if line.startswith("==="):
            result.append(line)
            continue

        # 필터 없는 경우 전체 출력
        if not alias and not path and not keyword:
            result.append(line)
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        line_alias = parts[0]
        line_path = parts[1].split(":")[-1]

        # alias 필터
        if alias and alias == line_alias:
            result.append(line)
            continue

        # path 필터
        if path and path == line_path:
            result.append(line)
            continue

        # keyword 필터 (부분 검색)
        if keyword and keyword.lower() in line.lower():
            result.append(line)

    return result


def main():
    parser = argparse.ArgumentParser(
        description="getauto: auto map 조회 도구",
        epilog="""
예시:
  getauto auto.DRAM
  getauto auto.DRAM --alias fg02_sim
  getauto auto.DRAM --path /fg2
  getauto auto.DRAM --search vol2
"""
    )

    # 필수 인자
    parser.add_argument(
        "target",
        help="auto 파일 이름 (예: auto.DRAM)"
    )

    # 옵션
    parser.add_argument(
        "--alias",
        help="alias 이름으로 조회 (정확 일치)"
    )

    parser.add_argument(
        "--path",
        help="junction path로 조회 (정확 일치)"
    )

    parser.add_argument(
        "--search",
        help="문자열 검색 (부분 일치)"
    )

    parser.add_argument(
        "--base-dir",
        default=BASE_DIR,
        help="auto 파일 경로 (기본: /etc/auto)"
    )

    args = parser.parse_args()

    lines = read_auto_file(args.target, args.base_dir)

    filtered = filter_lines(
        lines,
        alias=args.alias,
        path=args.path,
        keyword=args.search
    )

    for line in filtered:
        print(line)


if __name__ == "__main__":
    main()