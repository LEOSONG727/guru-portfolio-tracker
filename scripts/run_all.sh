#!/bin/bash
# run_all.sh — 구루 포트폴리오 분석 전체 파이프라인 실행
# 사용법: bash scripts/run_all.sh 2026 Q1

set -e

YEAR=${1:?"연도를 입력하세요 (예: bash run_all.sh 2026 Q1)"}
QUARTER=${2:?"분기를 입력하세요 (예: bash run_all.sh 2026 Q1)"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../output/${YEAR}_${QUARTER}"

echo "========================================"
echo " 구루 포트폴리오 트래커 — ${YEAR} ${QUARTER}"
echo "========================================"
echo ""

echo "[STEP 1/4] 투자자 데이터 수집..."
python3 "$SCRIPT_DIR/01_fetch_investors.py" --year "$YEAR" --quarter "$QUARTER"

echo ""
echo "[STEP 2/4] 구루 티어 스크리닝..."
python3 "$SCRIPT_DIR/02_screen_gurus.py" --year "$YEAR" --quarter "$QUARTER"

echo ""
echo "[STEP 3/4] 포트폴리오 변화 분석..."
python3 "$SCRIPT_DIR/03_analyze_changes.py" --year "$YEAR" --quarter "$QUARTER"

echo ""
echo "[STEP 4/4] 리포트 생성..."
python3 "$SCRIPT_DIR/04_generate_report.py" --year "$YEAR" --quarter "$QUARTER"

echo ""
echo "========================================"
echo " 완료! 결과물 위치:"
echo "   $OUTPUT_DIR/"
echo "   - investors_data.json  : 전체 투자자 데이터"
echo "   - screened_gurus.json  : 티어별 스크리닝 결과"
echo "   - stock_ranking.json   : 종목 랭킹"
echo "   - report.md            : 최종 리포트"
echo "========================================"
