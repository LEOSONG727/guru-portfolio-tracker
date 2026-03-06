# Guru Portfolio Tracker

매 분기 13F 공시 데이터를 기반으로, 장기 투자 성향의 구루 포트폴리오 변화를 분석해
투자 매력도 높은 종목을 발굴하는 방법론 및 자동화 스크립트.

데이터 소스: [Giantsight.com](https://giantsight.com/ko)

---

## 분석 프로세스 (매 분기 반복)

```
1. 구루 목록 수집       →  scripts/01_fetch_investors.py
2. 장기투자자 스크리닝  →  scripts/02_screen_gurus.py
3. 포트폴리오 변화 분석 →  scripts/03_analyze_changes.py
4. 종목 랭킹 & 리포트   →  scripts/04_generate_report.py
```

### 13F 공시 일정
| 공시 시점 | 보유 기간 | 제출 마감 |
|---|---|---|
| Q1 공시 | 전년도 Q4 (10~12월) | 2월 중순 |
| Q2 공시 | 당해 Q1 (1~3월) | 5월 중순 |
| Q3 공시 | 당해 Q2 (4~6월) | 8월 중순 |
| Q4 공시 | 당해 Q3 (7~9월) | 11월 중순 |

---

## 구루 스크리닝 기준

### 포함 (최소 6개월 보유 호흡)

**티어 1 — 핵심 컨빅션 투자자** (신호 강도 최고)
- 버크셔해서웨이, 퍼싱스퀘어, 보우포스트, 도지앤콕스, 프라임캡, 베일리기포드
- 클리어브리지, 피셔자산운용, 뉴버거버먼, MFS, 프랭클린템플턴, 아메리칸센추리
- 슈로더, 아문디, 얼라이언스번스타인, 제니슨, 캐피털 그룹 3사, 웰링턴, 피델리티
- 듀케인패밀리오피스, 브리지워터, 오크트리, 코튜, 재너스헨더슨

**티어 2 — 장기 기관 (연기금·국부펀드)**
- 국민연금공단, 노르웨이은행(NBIM), CalPERS, CPPIB, 한국투자공사(KIC)
- 스위스국립은행, 프린시플, 노스웨스턴뮤추얼, 스미토모미쓰이신탁, 미쓰비시UFJ, ARK

### 제외 (단타·퀀트·마켓메이커)
- 르네상스, 디이쇼, 시타델, AQR, 서스퀘하나, 제인스트리트, IMC, 밀레니엄, 포인트72, 튜더
- 투자은행 자기매매 계정: 골드만, 모건스탠리, JPMorgan, 씨티, 바클레이즈, 도이치, BNP

---

## 종목 발굴 기준

### 신호 강도 공식
```
score = 신규매수(NEW) × 2 + 비중확대(INC) × 1
```

### 해석 기준
| 신호 유형 | 의미 |
|---|---|
| 복수 티어1 투자자가 동일 종목 신규매수 | 최강 신호 |
| 티어1 단독 대규모 신규매수 | 강한 신호 |
| 복수 티어1+2가 동시 비중 확대 | 중간 신호 |
| 티어2만 비중 확대 | 참고 신호 |

### 추가 고려사항
- 동일 운용사 계열사 중복 제거 (Capital Group 3사는 독립 운용이므로 각각 유효)
- ETF·인덱스 펀드 매수는 별도 판단 (지수 편입 효과 가능성 차감)
- 옵션(PUT/CALL) 포지션은 분석에서 제외

---

## 폴더 구조

```
guru-portfolio-tracker/
├── README.md               # 이 파일
├── docs/
│   └── methodology.md      # 상세 방법론
├── scripts/
│   ├── 01_fetch_investors.py   # 구루 목록 수집
│   ├── 02_screen_gurus.py      # 티어 스크리닝
│   ├── 03_analyze_changes.py   # 포트폴리오 변화 분석
│   ├── 04_generate_report.py   # 리포트 생성
│   └── run_all.sh              # 전체 실행 스크립트
└── output/
    └── YYYY_QN/                # 분기별 결과물
        ├── investors_data.json
        ├── popular_stocks.json
        ├── stock_ranking.json
        └── report.md
```

---

## 실행 방법

```bash
# 전체 파이프라인 실행
bash scripts/run_all.sh 2026 Q1

# 단계별 실행
python3 scripts/01_fetch_investors.py --year 2026 --quarter Q1
python3 scripts/02_screen_gurus.py
python3 scripts/03_analyze_changes.py
python3 scripts/04_generate_report.py
```
