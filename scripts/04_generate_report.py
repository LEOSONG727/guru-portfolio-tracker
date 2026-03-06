#!/usr/bin/env python3
"""
04_generate_report.py
종목 랭킹을 바탕으로 투자 리포트(Markdown)를 생성합니다.

구루 평균 매수 기준가 계산 방식:
  - 신규매수(NEW) 포지션만 대상 (비중확대는 기존 보유분 가격변동 포함으로 계산 불가)
  - q_end_price = valChg / shrChg  ← 분기말 시가 근사값 (실제 매수단가 아님)
  - 복수 구루가 같은 종목 신규매수 시: 주수 가중평균 = Σ(shares × price) / Σ(shares)
  - Yahoo Finance에서 현재가 조회 → 기준가 대비 등락률 계산
"""

import json
import subprocess
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


def fetch_current_price(sym: str) -> float | None:
    """Yahoo Finance v8 API로 현재가를 조회합니다."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
    result = subprocess.run(
        ["curl", "-s", "-L", url, "-H", "User-Agent: Mozilla/5.0 (compatible; GuruTracker/1.0)"],
        capture_output=True, text=True, timeout=10
    )
    try:
        data = json.loads(result.stdout)
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception:
        return None


def fetch_prices_bulk(syms: list[str]) -> dict[str, float]:
    """여러 종목의 현재가를 병렬로 조회합니다."""
    prices = {}
    for sym in syms:
        if not sym or len(sym) > 10:  # 이상한 심볼 스킵
            continue
        price = fetch_current_price(sym)
        if price:
            prices[sym] = price
    return prices


def format_pct_change(ref_price: float, current_price: float) -> str:
    """등락률 문자열 반환 (+ 초록, - 빨강 표시)"""
    pct = (current_price - ref_price) / ref_price * 100
    sign = "▲" if pct >= 0 else "▼"
    return f"{sign} {abs(pct):.1f}%"


def generate_report(year: str, quarter: str, stocks: list, current_prices: dict) -> str:
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
        f"### 구루 평균 매수 기준가 계산 방식",
        f"```",
        f"q_end_price  = valChg / shrChg          ← 분기말 시가 근사값 (투자자별)",
        f"guru_avg     = Σ(shares × price) / Σ(shares)  ← 주수 가중평균 (복수 구루 합산)",
        f"등락률        = (현재가 - guru_avg) / guru_avg × 100",
        f"",
        f"※ 실제 매수단가는 분기 중 매수 시점에 따라 다를 수 있으나,",
        f"  분기말 기준가는 구루 진입 가격대의 합리적 근사값으로 활용합니다.",
        f"```",
        f"",
        f"---",
        f"",
        f"## 강력 매수 신호 종목 (점수 ≥{SIGNAL_THRESHOLDS['강함']})",
        f"",
    ]

    for i, s in enumerate(top_picks, 1):
        lvl = signal_level(s["score"])
        sym = s["sym"]
        current_price = current_prices.get(sym)

        lines += [
            f"### {i}. {sym} — {s.get('name', '')}",
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

        # ── 구루 평균 매수 기준가 섹션 ────────────────────────────────────────
        price_refs = s.get("new_price_refs", [])
        guru_price_summary = s.get("guru_price_summary")

        if price_refs:
            lines.append(f"**구루 매수 기준가 분석** *(신규매수 포지션만, Q4 말일 시가 기준)*")
            lines.append(f"")

            # 개별 구루 내역
            lines += [
                f"| 투자자 | 매수 주수 | 투자금액 | 분기말 기준가 |",
                f"|---|---|---|---|",
            ]
            for p in price_refs:
                amt = p["amount_usd"] / 1e6
                lines.append(
                    f"| {p['investor']} | {p['shares']:,}주 | ~${amt:.1f}M | ${p['q_end_price']:,.2f} |"
                )
            lines.append(f"")

            # 가중평균 + 현재가 비교
            if guru_price_summary:
                avg = guru_price_summary["guru_avg_q_end_price"]
                total_amt = guru_price_summary["total_new_amount_usd"] / 1e6
                total_shr = guru_price_summary["total_new_shares"]
                n_buyers = guru_price_summary["buyers_count"]

                if current_price:
                    pct_str = format_pct_change(avg, current_price)
                    lines += [
                        f"| 항목 | 값 |",
                        f"|---|---|",
                        f"| 구루 가중평균 기준가 ({n_buyers}명) | **${avg:,.2f}** |",
                        f"| 총 신규 매수 주수 | {total_shr:,}주 |",
                        f"| 총 신규 투자금액 | ~${total_amt:.1f}M |",
                        f"| 현재가 ({today}) | **${current_price:,.2f}** |",
                        f"| 기준가 대비 등락률 | **{pct_str}** |",
                    ]
                else:
                    lines += [
                        f"| 항목 | 값 |",
                        f"|---|---|",
                        f"| 구루 가중평균 기준가 ({n_buyers}명) | **${avg:,.2f}** |",
                        f"| 총 신규 매수 주수 | {total_shr:,}주 |",
                        f"| 총 신규 투자금액 | ~${total_amt:.1f}M |",
                        f"| 현재가 | 조회 실패 |",
                    ]
                lines.append(f"")
            elif current_price and price_refs:
                # 구루 1명인 경우 단순 비교
                single = price_refs[0]
                pct_str = format_pct_change(single["q_end_price"], current_price)
                lines += [
                    f"| 항목 | 값 |",
                    f"|---|---|",
                    f"| 분기말 기준가 | **${single['q_end_price']:,.2f}** |",
                    f"| 현재가 ({today}) | **${current_price:,.2f}** |",
                    f"| 기준가 대비 등락률 | **{pct_str}** |",
                    f"",
                ]
        elif current_price:
            # 신규매수 정보 없는 종목 (비중확대만)도 현재가는 표시
            lines += [
                f"| 현재가 ({today}) | ${current_price:,.2f} |",
                f"",
            ]

    # ── 관심 종목 섹션 ────────────────────────────────────────────────────────
    lines += [
        f"---",
        f"",
        f"## 관심 종목 (점수 {SIGNAL_THRESHOLDS['중간']}–{SIGNAL_THRESHOLDS['강함']-1})",
        f"",
        f"| 순위 | 종목 | 이름 | 점수 | 티어1 신규 | 티어1 확대 | 현재가 |",
        f"|---|---|---|---|---|---|---|",
    ]

    for i, s in enumerate(watch_list, 1):
        cp = current_prices.get(s["sym"])
        cp_str = f"${cp:,.2f}" if cp else "—"
        lines.append(
            f"| {i} | **{s['sym']}** | {s.get('name','')} | {s['score']:.1f} "
            f"| {len(s['tier1_new'])} | {len(s['tier1_inc'])} | {cp_str} |"
        )

    # ── 전체 랭킹 섹션 ────────────────────────────────────────────────────────
    lines += [
        f"",
        f"---",
        f"",
        f"## 전체 종목 랭킹",
        f"",
        f"| 순위 | 종목 | 이름 | 점수 | 신호 강도 | 구루 기준가 | 현재가 | 등락률 |",
        f"|---|---|---|---|---|---|---|---|",
    ]

    for i, s in enumerate(stocks, 1):
        lvl = signal_level(s["score"])
        cp = current_prices.get(s["sym"])
        cp_str = f"${cp:,.2f}" if cp else "—"

        gps = s.get("guru_price_summary")
        if gps:
            ref_str = f"${gps['guru_avg_q_end_price']:,.2f}"
            pct_str = format_pct_change(gps["guru_avg_q_end_price"], cp) if cp else "—"
        elif s.get("new_price_refs"):
            p0 = s["new_price_refs"][0]
            ref_str = f"${p0['q_end_price']:,.2f}"
            pct_str = format_pct_change(p0["q_end_price"], cp) if cp else "—"
        else:
            ref_str = "—"
            pct_str = "—"

        lines.append(
            f"| {i} | {s['sym']} | {s.get('name','')} | {s['score']:.1f} | {lvl} | {ref_str} | {cp_str} | {pct_str} |"
        )

    lines += [
        f"",
        f"---",
        f"",
        f"*이 리포트는 13F 공시 데이터를 기반으로 자동 생성된 참고자료이며, 투자 권유가 아닙니다.*",
        f"*구루 기준가는 분기말 시가 근사값으로, 실제 평균 매수단가와 다를 수 있습니다.*",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="투자 리포트 생성")
    parser.add_argument("--year", required=True)
    parser.add_argument("--quarter", required=True)
    parser.add_argument("--no-price", action="store_true", help="현재가 조회 생략")
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output" / f"{args.year}_{args.quarter}"
    ranking_file = output_dir / "stock_ranking.json"

    if not ranking_file.exists():
        print(f"[04] ERROR: {ranking_file} 없음. 03_analyze_changes.py 먼저 실행하세요.")
        import sys; sys.exit(1)

    with open(ranking_file, encoding="utf-8") as f:
        data = json.load(f)

    stocks = data["stocks"]

    # 현재가 조회 (상위 30개만)
    current_prices = {}
    if not args.no_price:
        syms = [s["sym"] for s in stocks[:30] if s.get("sym")]
        print(f"[04] 현재가 조회 중 ({len(syms)}개 종목)...")
        current_prices = fetch_prices_bulk(syms)
        fetched = len(current_prices)
        print(f"[04] 현재가 조회 완료: {fetched}/{len(syms)}개")

    report = generate_report(args.year, args.quarter, stocks, current_prices)

    out_file = output_dir / "report.md"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"[04] 리포트 생성 완료: {out_file}")

    # 상위 5개 미리보기 (기준가 + 현재가 포함)
    print("\n== 상위 종목 미리보기 ==")
    for i, s in enumerate(stocks[:5], 1):
        sym = s["sym"]
        cp = current_prices.get(sym)
        gps = s.get("guru_price_summary")
        ref = s.get("new_price_refs", [])

        if gps:
            avg = gps["guru_avg_q_end_price"]
            pct = f"  현재가: ${cp:,.2f} ({format_pct_change(avg, cp)})" if cp else ""
            print(f"  {i}. {sym:8s} (점수: {s['score']:.1f}) 구루 기준가: ${avg:,.2f}{pct}")
        elif ref:
            p0 = ref[0]
            pct = f"  현재가: ${cp:,.2f} ({format_pct_change(p0['q_end_price'], cp)})" if cp else ""
            print(f"  {i}. {sym:8s} (점수: {s['score']:.1f}) 기준가: ${p0['q_end_price']:,.2f}{pct}")
        else:
            cp_str = f"  현재가: ${cp:,.2f}" if cp else ""
            print(f"  {i}. {sym:8s} (점수: {s['score']:.1f}){cp_str}")


if __name__ == "__main__":
    main()
