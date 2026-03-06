#!/usr/bin/env python3
"""
01_fetch_investors.py
giantsight.com 메인 페이지 RSC 데이터에서 투자자 목록을 수집합니다.
"""

import sys
import json
import subprocess
import argparse
from pathlib import Path

BASE_URL = "https://giantsight.com"

def fetch_investors_rsc(year: str, quarter: str) -> str:
    """메인 페이지 RSC 엔드포인트에서 원본 텍스트를 가져옵니다."""
    url = f"{BASE_URL}/ko?_rsc=analyse1"
    result = subprocess.run(
        ["curl", "-s", url, "-H", "RSC: 1", "-H", "Accept: text/x-component",
         "-H", "User-Agent: Mozilla/5.0 (compatible; GuruTracker/1.0)"],
        capture_output=True, text=True
    )
    return result.stdout


def parse_investors(rsc_text: str) -> list:
    """RSC 페이로드에서 investors 배열을 파싱합니다."""
    marker = '"investors":'
    idx = rsc_text.find(marker)
    if idx == -1:
        raise ValueError("investors 데이터를 찾을 수 없습니다. RSC 응답을 확인하세요.")

    arr_start = rsc_text.index('[', idx)
    depth = 0
    arr_end = arr_start
    for i, ch in enumerate(rsc_text[arr_start:], start=arr_start):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                arr_end = i
                break

    arr_text = rsc_text[arr_start:arr_end + 1]
    investors = json.loads(arr_text)
    return investors


def save_investors(investors: list, year: str, quarter: str, output_dir: Path):
    """투자자 데이터를 JSON으로 저장합니다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "investors_data.json"

    total = len(investors)
    with_data = sum(1 for inv in investors if inv.get("hasData"))

    payload = {
        "year": year,
        "quarter": quarter,
        "total": total,
        "with_data": with_data,
        "investors": investors
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[01] 투자자 수집 완료: 전체 {total}명, 데이터 있음 {with_data}명")
    print(f"[01] 저장: {out_file}")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="구루 투자자 목록 수집")
    parser.add_argument("--year", required=True, help="연도 (예: 2026)")
    parser.add_argument("--quarter", required=True, help="분기 (예: Q1)")
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output" / f"{args.year}_{args.quarter}"

    print(f"[01] {args.year} {args.quarter} 투자자 데이터 수집 중...")
    rsc_text = fetch_investors_rsc(args.year, args.quarter)

    if not rsc_text.strip():
        print("[01] ERROR: RSC 응답이 비어 있습니다.", file=sys.stderr)
        sys.exit(1)

    investors = parse_investors(rsc_text)
    save_investors(investors, args.year, args.quarter, output_dir)


if __name__ == "__main__":
    main()
