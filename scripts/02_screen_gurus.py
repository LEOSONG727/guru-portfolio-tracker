#!/usr/bin/env python3
"""
02_screen_gurus.py
투자자 목록에서 장기 투자 성향의 구루를 티어별로 스크리닝합니다.
"""

import json
import argparse
from pathlib import Path

# ── 티어 1: 핵심 컨빅션 투자자 (신호 강도 최고) ─────────────────────────────
TIER1_CIKS = {
    "0001067983": "버크셔해서웨이 (워렌 버핏)",
    "0001336528": "퍼싱스퀘어 (빌 애크먼)",
    "0001379785": "보우포스트그룹 (셋 클라만)",
    "0000029136": "도지앤콕스",
    "0001061768": "프라임캡",
    "0001156375": "베일리기포드",
    "0000811156": "클리어브리지",
    "0001056831": "피셔자산운용",
    "0000804239": "뉴버거버먼",
    "0001048268": "MFS",
    "0001099590": "프랭클린템플턴",
    "0000006701": "아메리칸센추리",
    "0001060349": "슈로더",
    "0001353283": "아문디",
    "0001109164": "얼라이언스번스타인",
    "0000793074": "제니슨",
    "0001422849": "캐피털 리서치 & 매니지먼트",
    "0001562230": "캐피털 인터내셔널",
    "0001422848": "캐피털 월드",
    "0000101984": "웰링턴",
    "0000315066": "피델리티",
    "0001039454": "듀케인패밀리오피스 (스탠리 드러켄밀러)",
    "0001350487": "브리지워터",
    "0000793251": "오크트리",
    "0001423538": "코튜",
    "0001279914": "재너스헨더슨",
    "0001048062": "테퍼 (아팔루사)",
}

# ── 티어 2: 장기 기관 (연기금·국부펀드) ──────────────────────────────────────
TIER2_CIKS = {
    "0000940729": "국민연금공단 (NPS)",
    "0001571592": "노르웨이은행 (NBIM)",
    "0000805387": "CalPERS",
    "0001362988": "CPPIB",
    "0001466222": "한국투자공사 (KIC)",
    "0001582202": "스위스국립은행 (SNB)",
    "0000894871": "프린시플",
    "0000075340": "노스웨스턴뮤추얼",
    "0000807985": "스미토모미쓰이신탁",
    "0001173281": "미쓰비시UFJ",
    "0001418612": "ARK인베스트",
}

# ── 티어 3: 패시브·인덱스 매니저 (참고용) ────────────────────────────────────
TIER3_CIKS = {
    "0001364742": "블랙록",
    "0000315252": "뱅가드",
    "0000093751": "스테이트스트리트",
    "0001603466": "DFA",
    "0000277751": "인베스코",
    "0000102909": "T. 로우 프라이스",
    "0000315508": "모건스탠리 자산운용",
    "0001099590": "프랭클린",
}

# ── 제외: 퀀트·마켓메이커·투자은행 ──────────────────────────────────────────
EXCLUDED_CIKS = {
    "0001037389": "르네상스",
    "0001009207": "디이쇼",
    "0001423298": "시타델",
    "0001167557": "AQR",
    "0000804212": "서스퀘하나",
    "0001302028": "제인스트리트",
    "0001288810": "IMC",
    "0001273931": "밀레니엄",
    "0000867463": "포인트72",
    "0001210472": "튜더",
    "0000886982": "골드만삭스 자기매매",
    "0001053785": "모건스탠리 자기매매",
    "0000019617": "JPMorgan 자기매매",
    "0001012270": "씨티",
    "0000009626": "바클레이즈",
    "0000029033": "도이치은행",
    "0000048898": "BNP파리바",
}

TIER_MAP = {
    **{cik: (1, name) for cik, name in TIER1_CIKS.items()},
    **{cik: (2, name) for cik, name in TIER2_CIKS.items()},
    **{cik: (3, name) for cik, name in TIER3_CIKS.items()},
}


def screen(investors: list) -> dict:
    """투자자 목록을 티어별로 분류합니다."""
    result = {1: [], 2: [], 3: [], "unknown": [], "excluded": []}

    for inv in investors:
        cik = inv.get("cik", "")
        name = inv.get("nameKo") or inv.get("name", "")
        has_data = inv.get("hasData", False)

        if cik in EXCLUDED_CIKS:
            result["excluded"].append({**inv, "tier": "excluded", "reason": "퀀트/마켓메이커/투자은행"})
        elif cik in TIER_MAP:
            tier, label = TIER_MAP[cik]
            result[tier].append({**inv, "tier": tier, "label": label})
        else:
            result["unknown"].append({**inv, "tier": "unknown"})

    return result


def print_summary(screened: dict):
    for tier in [1, 2, 3]:
        label = {1: "티어1 핵심 컨빅션", 2: "티어2 장기 기관", 3: "티어3 패시브/인덱스"}[tier]
        items = screened[tier]
        with_data = [x for x in items if x.get("hasData")]
        print(f"\n[티어{tier}] {label} — {len(items)}개 매핑 / 데이터 있음 {len(with_data)}개")
        for inv in with_data:
            print(f"  - {inv.get('label')} ({inv.get('cik')})")

    print(f"\n[미분류] {len(screened['unknown'])}개")
    print(f"[제외] {len(screened['excluded'])}개 (퀀트/마켓메이커)")


def main():
    parser = argparse.ArgumentParser(description="구루 티어 스크리닝")
    parser.add_argument("--year", required=True)
    parser.add_argument("--quarter", required=True)
    args = parser.parse_args()

    output_dir = Path(__file__).parent.parent / "output" / f"{args.year}_{args.quarter}"
    investors_file = output_dir / "investors_data.json"

    if not investors_file.exists():
        print(f"[02] ERROR: {investors_file} 없음. 01_fetch_investors.py 먼저 실행하세요.")
        import sys; sys.exit(1)

    with open(investors_file, encoding="utf-8") as f:
        data = json.load(f)

    investors = data["investors"]
    screened = screen(investors)
    print_summary(screened)

    # 저장
    out = {
        "year": args.year,
        "quarter": args.quarter,
        "tier1": screened[1],
        "tier2": screened[2],
        "tier3": screened[3],
        "excluded": screened["excluded"],
        "unknown": screened["unknown"],
    }
    out_file = output_dir / "screened_gurus.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n[02] 스크리닝 결과 저장: {out_file}")


if __name__ == "__main__":
    main()
