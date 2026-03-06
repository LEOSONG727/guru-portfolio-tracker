#!/usr/bin/env python3
"""
04_generate_report.py
종목 랭킹을 바탕으로 투자 리포트(Markdown)를 생성합니다.
"""

import json
import argparse
from pathlib import Path
from datetime import date

SIGNAL_THRESHOLDS = {
    "최강": 6,
    "강함": 4,
    "중간": 2,
    "참고": 1,
}


def signal_level(score: float) -> str:
    if score >= SIGNAL_THRESHOLDS["최강"]:
        return "★★★ 최강"
    elif score >= SIGNAL_THRESHOLDS["강함"]:
        return "★★ 강함"
    elif score >= SIGNAL_THRESHOLDS["중간"]:
        return "★ 중간"
    else:
        return "△ 참고"


def format_investor_list(lst: list) -> str:
    if not lst:
        return "—"
    return ", ".join(lst)


def generate_report(year: str, quarter: str, stocks: list) -> str:
    today = date.today().isoformat()
    top_picks = [s for s in stocks if s["score"] >= SIGNAL_THRESHOLDS["강함"]]
    watch_list = [s for s in stocks if SIGNAL_THRESHOLDS["중간"] <= s["score"] < SIGNAL_THRESHOLDS["강함"]]

    lines = [
        f"# 구루 포트폴리오 분석 리포트 — {year} {quarter}",
        f"",
        f"> 생성일: {today}  |  데이터: giantsight.com  |  기준: 13F 공시",
        f"",
        f"---",
        f"",
        f"## 분석 요약",
        f"",
        f"- 분석 대상 종목: {len(stocks)}개",
        f"- 강력 매수 신호 (점수 ≥{SIGNAL_THRESHOLDS['강함']}): {len(top_picks)}개",
        f"- 관심 종목 (점수 ≥{SIGNAL_THRESHOLDS['중간']}): {len(watch_list)}개",
        f"",
        f"### 신호 강도 공식",
        f"```",
        f"score = 티어1 신규매수 × 2 + 티어1 비중확대 × 1",
        f"      + 티어2 신규매수 × 1 + 티어2 비중확대 × 0.5",
        f"```",
        f"",
        f"---",
        f"",
        f"## 강력 매수 신호 종목 (점수 ≥{SIGNAL_THRESHOLDS['강함']})",
        f"",
    ]

    for i, s in enumerate(top_picks, 1):
        lvl = signal_level(s["score"])
        lines += [
            f"### {i}. {s['sym']} — {s.get('name', '')}",
            f"",
            f"**신호 강도**: {lvl} (점수: {s['score']:.1f})",
            f"",
            f"| 행동 | 투자자 |",
            f"|---|---|",
            f"| 🟢 티어1 신규매수 | {format_investor_list(s['tier1_new'])} |",
            f"| 🔵 티어1 비중확대 | {format_investor_list(s['tier1_inc'])} |",
            f"| 🟡 티어2 신규매수 | {format_investor_list(s['tier2_new'])} |",
            f"| 🟠 티어2 비중확대 | {format_investor_list(s['tier2_inc'])} |",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## 관심 종목 (점수 {SIGNAL_THRESHOLDS['중간']}–{SIGNAL_THRESHOLDS['강함']-1})",
        f"",
        f"| 순위 | 종목 | 이름 | 점수 | 티어1 신규 | 티어1 확대 |",
        f"|---|---|---|---|---|---|",
    ]

    for i, s in enumerate(watch_list, 1):
        lines.append(
            f"| {i} | **{s['sym']}** | {s.get('name','')} | {s['score']:.1f} "
            f"| {len(s['tier1_new'])} | {len(s['tier1_inc'])} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"## 전체 종목 랭킹",
        f"",
        f"| 순위 | 종목 | 이름 | 점수 | 신호 강도 |",
        f"|---|---|---|---|---|",
    ]

    for i, s in enumerate(stocks, 1):
        lvl = signal_level(s["score"])
        lines.append(f"| {i} | {s['sym']} | {s.get('name','')} | {s['score']:.1f} | {lvl} |")

    lines += [
        f"",
        f"---",
        f"",
        f"*이 리포트는 13F 공시 데이터를 기반으로 자동 생성된 참고자료이며, 투자 권유가 아닙니다.*",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="투자 리포트 생성")
    parser.add_argument("--year", required=True)
    parser.add_argument("--quarter", required=True)
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output" / f"{args.year}_{args.quarter}"
    ranking_file = output_dir / "stock_ranking.json"

    if not ranking_file.exists():
        print(f"[04] ERROR: {ranking_file} 없음. 03_analyze_changes.py 먼저 실행하세요.")
        import sys; sys.exit(1)

    with open(ranking_file, encoding="utf-8") as f:
        data = json.load(f)

    report = generate_report(args.year, args.quarter, data["stocks"])

    out_file = output_dir / "report.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[04] 리포트 생성 완료: {out_file}")

    # 상위 5개 미리보기
    print("\n== 상위 종목 미리보기 ==")
    for i, s in enumerate(data["stocks"][:5], 1):
        print(f"  {i}. {s['sym']:8s} (점수: {s['score']:.1f}) — {s.get('name','')}")


if __name__ == "__main__":
    main()
