#!/usr/bin/env python3
"""
03_analyze_changes.py
티어1+2 구루의 포트폴리오 변화를 분석하여 종목별 신호 강도를 계산합니다.

데이터 소스:
  1) investors_data.json — 각 투자자의 top-3 매수/매도 종목
  2) popular stocks RSC  — 종목별 전체 보유자 목록(topH)과 행동
"""

import json
import subprocess
import argparse
from pathlib import Path
from collections import defaultdict

BASE_URL = "https://giantsight.com"


def fetch_popular_rsc(year: str, quarter: str) -> str:
    url = f"{BASE_URL}/ko/{year}/{quarter}/popular-stocks?_rsc=popdata1"
    result = subprocess.run(
        ["curl", "-s", url, "-H", "RSC: 1", "-H", "Accept: text/x-component",
         "-H", "User-Agent: Mozilla/5.0 (compatible; GuruTracker/1.0)"],
        capture_output=True, text=True
    )
    return result.stdout


def extract_json_array(text: str, key: str) -> list:
    """RSC 텍스트에서 특정 키의 JSON 배열을 추출합니다."""
    marker = f'"{key}":'
    idx = text.find(marker)
    if idx == -1:
        return []
    arr_start = text.index('[', idx)
    depth = 0
    for i, ch in enumerate(text[arr_start:], start=arr_start):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                return json.loads(text[arr_start:i + 1])
    return []


def build_tier12_set(screened: dict) -> dict:
    """CIK → (tier, label) 딕셔너리 생성."""
    cik_map = {}
    for inv in screened.get("tier1", []):
        cik_map[inv["cik"]] = (1, inv.get("label") or inv.get("nameKo") or inv.get("name"))
    for inv in screened.get("tier2", []):
        cik_map[inv["cik"]] = (2, inv.get("label") or inv.get("nameKo") or inv.get("name"))
    return cik_map


def analyze_from_investors(investors: list, tier12: dict) -> dict:
    """
    investors_data.json의 top-3 buy 데이터로 종목별 신호 집계.
    행동: new / increased / decreased / sold
    """
    stocks = defaultdict(lambda: {"sym": "", "name": "", "cusip": "",
                                   "tier1_new": [], "tier1_inc": [],
                                   "tier2_new": [], "tier2_inc": [],
                                   "new_price_refs": [],
                                   "sources": set()})

    for inv in investors:
        cik = inv.get("cik", "")
        if cik not in tier12:
            continue
        tier, label = tier12[cik]

        for buy in inv.get("buy", []):
            act = buy.get("act", "")
            sym = buy.get("sym") or buy.get("in") or buy.get("cusip", "")
            cusip = buy.get("cusip", "")
            name = buy.get("inKo") or buy.get("in", "")

            key = cusip or sym
            s = stocks[key]
            s["sym"] = sym
            s["name"] = name
            s["cusip"] = cusip
            s["sources"].add("investors_top3")

            if act in ("new", "NEW"):
                if tier == 1:
                    s["tier1_new"].append(label)
                else:
                    s["tier2_new"].append(label)
                # 신규매수만 implied price 계산 (비중확대는 기존 보유분 가격변동 포함으로 무의미)
                shrc = buy.get("shrChg", 0)
                valc = buy.get("valChg", 0)
                if shrc and valc:
                    implied = valc / shrc
                    if 0 < implied < 1:   # 단위가 천달러인 경우 정규화
                        implied *= 1000
                        valc *= 1000
                    if 1 < implied < 5000:  # 이상값 제외 (옵션 등)
                        s["new_price_refs"].append({
                            "investor": label,
                            "shares": abs(shrc),
                            "amount_usd": abs(int(valc)),
                            "q_end_price": round(implied, 2),
                        })
            elif act in ("increased", "INC", "inc"):
                if tier == 1:
                    s["tier1_inc"].append(label)
                else:
                    s["tier2_inc"].append(label)

    return stocks


def analyze_from_popular(rsc_text: str, tier12: dict, stocks: dict):
    """popular-stocks RSC의 topH 데이터로 종목별 신호 보강."""
    arrays_to_check = ["topBuyStocks", "mostIncreased", "mostNewlyBought"]

    for arr_key in arrays_to_check:
        items = extract_json_array(rsc_text, arr_key)
        for item in items:
            cusip = item.get("cusip", "")
            sym = item.get("sym") or item.get("in", "")
            name = item.get("inKo") or item.get("in", "")
            key = cusip or sym
            if not key:
                continue

            if key not in stocks:
                stocks[key] = {"sym": sym, "name": name, "cusip": cusip,
                               "tier1_new": [], "tier1_inc": [],
                               "tier2_new": [], "tier2_inc": [],
                               "new_price_refs": [],
                               "sources": set()}

            s = stocks[key]
            s["sym"] = sym or s["sym"]
            s["name"] = name or s["name"]
            s["sources"].add(arr_key)

            for holder in item.get("topH", []):
                hcik = holder.get("cik", "")
                if hcik not in tier12:
                    continue
                tier, label = tier12[hcik]
                act = holder.get("act", "")

                if act in ("new", "NEW"):
                    lst = s["tier1_new"] if tier == 1 else s["tier2_new"]
                    if label not in lst:
                        lst.append(label)
                    # topH에서 신규매수 implied price 보강
                    shrc = holder.get("shrChg", 0)
                    valc = holder.get("valChg", 0)
                    if shrc and valc:
                        implied = valc / shrc
                        if 0 < implied < 1:
                            implied *= 1000
                            valc *= 1000
                        if 1 < implied < 5000:
                            existing = [p for p in s["new_price_refs"] if p["investor"] == label]
                            if not existing:
                                s["new_price_refs"].append({
                                    "investor": label,
                                    "shares": abs(int(shrc)),
                                    "amount_usd": abs(int(valc)),
                                    "q_end_price": round(implied, 2),
                                })
                elif act in ("increased", "INC", "inc"):
                    lst = s["tier1_inc"] if tier == 1 else s["tier2_inc"]
                    if label not in lst:
                        lst.append(label)


def calc_guru_avg_price(new_price_refs: list) -> dict | None:
    """
    복수 구루가 동일 종목을 신규매수한 경우 주수 가중평균 분기말 기준가를 계산합니다.

    가중평균 공식:
        guru_avg_q_end_price = Σ(shares_i × q_end_price_i) / Σ(shares_i)

    주의: q_end_price 자체가 실제 매수단가가 아닌 분기말 시가 근사값이므로
          이 평균도 "구루들이 보유 시작한 시점의 기준 가격대" 정도로 해석합니다.
    """
    refs = [p for p in new_price_refs if p.get("shares", 0) > 0 and p.get("q_end_price", 0) > 0]
    if not refs:
        return None

    total_shares = sum(p["shares"] for p in refs)
    weighted_price = sum(p["shares"] * p["q_end_price"] for p in refs) / total_shares
    total_amount = sum(p["amount_usd"] for p in refs)

    return {
        "guru_avg_q_end_price": round(weighted_price, 2),
        "total_new_shares": total_shares,
        "total_new_amount_usd": total_amount,
        "buyers_count": len(refs),
    }


def score_stocks(stocks: dict) -> list:
    """
    신호 강도 계산:
      score = (tier1_new × 2) + (tier1_inc × 1) + (tier2_new × 1) + (tier2_inc × 0.5)
    """
    ranked = []
    for key, s in stocks.items():
        t1n = len(s["tier1_new"])
        t1i = len(s["tier1_inc"])
        t2n = len(s["tier2_new"])
        t2i = len(s["tier2_inc"])
        score = t1n * 2 + t1i * 1 + t2n * 1 + t2i * 0.5

        if score == 0:
            continue

        price_refs = s.get("new_price_refs", [])
        guru_price_summary = calc_guru_avg_price(price_refs)

        ranked.append({
            "sym": s["sym"],
            "name": s["name"],
            "cusip": s["cusip"],
            "score": score,
            "tier1_new": s["tier1_new"],
            "tier1_inc": s["tier1_inc"],
            "tier2_new": s["tier2_new"],
            "tier2_inc": s["tier2_inc"],
            # 개별 구루 신규매수 기준가 (실제 매수단가 ≠, Q4 말일 시가 근사값)
            "new_price_refs": price_refs,
            # 복수 구루 가중평균 기준가 (신규매수 구루가 2명 이상일 때 의미 있음)
            "guru_price_summary": guru_price_summary,
            "sources": list(s.get("sources", [])),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked


def print_top(ranked: list, n: int = 20):
    print(f"\n{'순위':>4}  {'종목':>8}  {'점수':>6}  {'T1신규':>6}  {'T1확대':>6}  이름")
    print("-" * 70)
    for i, s in enumerate(ranked[:n], 1):
        print(f"{i:>4}  {s['sym']:>8}  {s['score']:>6.1f}  "
              f"{len(s['tier1_new']):>6}  {len(s['tier1_inc']):>6}  {s['name']}")
        if s["tier1_new"]:
            print(f"       → 신규: {', '.join(s['tier1_new'])}")
        if s["tier1_inc"]:
            print(f"       → 확대: {', '.join(s['tier1_inc'])}")


def main():
    parser = argparse.ArgumentParser(description="포트폴리오 변화 분석")
    parser.add_argument("--year", required=True)
    parser.add_argument("--quarter", required=True)
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output" / f"{args.year}_{args.quarter}"

    # 데이터 로드
    with open(output_dir / "investors_data.json", encoding="utf-8") as f:
        inv_data = json.load(f)
    with open(output_dir / "screened_gurus.json", encoding="utf-8") as f:
        screened = json.load(f)

    tier12 = build_tier12_set(screened)
    print(f"[03] 티어1+2 투자자: {len(tier12)}개 CIK")

    # 분석
    stocks = analyze_from_investors(inv_data["investors"], tier12)

    print(f"[03] popular-stocks RSC 데이터 수집 중...")
    pop_rsc = fetch_popular_rsc(args.year, args.quarter)
    if pop_rsc.strip():
        analyze_from_popular(pop_rsc, tier12, stocks)
        print(f"[03] popular-stocks 데이터 병합 완료")
    else:
        print(f"[03] WARN: popular-stocks 데이터 없음, investors top-3만 사용")

    ranked = score_stocks(stocks)
    print_top(ranked)

    # 저장
    out_file = output_dir / "stock_ranking.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"year": args.year, "quarter": args.quarter,
                   "total": len(ranked), "stocks": ranked},
                  f, ensure_ascii=False, indent=2)

    print(f"\n[03] 분석 완료: 총 {len(ranked)}개 종목, 저장: {out_file}")


if __name__ == "__main__":
    main()
