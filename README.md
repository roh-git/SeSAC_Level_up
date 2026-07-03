# team-2 — eCommerce Behavior Data EDA

[Kaggle: eCommerce behavior data from a multi-category store](https://www.kaggle.com/datasets/mkechinov/ecommerce-behavior-data-from-multi-category-store) 데이터를
**DB 셋업 없이 DuckDB로 직접 분석**하는 프로젝트입니다.

- 원본 CSV (Oct + Nov 2019, 약 **1.1억 행 / 14GB**)를 DuckDB로 스트리밍 쿼리 — 전체를 메모리에 올리지 않습니다.
- 무거운 집계는 **DuckDB**, 시각화는 **pandas + matplotlib**.
- 원본을 **정규화(star schema)** 하여 Parquet로 저장 → 14GB → 3.4GB (24.5%).

## 요구 환경

- Python ≥ 3.13, [uv](https://docs.astral.sh/uv/)
- Kaggle API 자격증명 (`~/.kaggle/kaggle.json`) — 데이터 다운로드 시

```bash
uv sync          # 의존성 설치 (kaggle, duckdb, pandas, matplotlib, ipykernel)
```

## 데이터 준비

데이터 파일은 용량이 커서 git으로 추적하지 않습니다 (`data/`는 `.gitignore` 처리).

```bash
# 1) 원본 CSV 다운로드 (약 4.3GB zip → 압축 해제 시 14GB)
uv run kaggle datasets download \
  -d mkechinov/ecommerce-behavior-data-from-multi-category-store \
  -p data --unzip
# → data/2019-Oct.csv, data/2019-Nov.csv

# 2) 정규화 Parquet 생성 (data/normalized/)
uv run python eda/04_normalize.py
```

## 데이터 스키마

원본 CSV 컬럼: `event_time, event_type(view/cart/purchase), product_id, category_id, category_code, brand, price, user_id, user_session`

정규화 후 (star schema, `data/normalized/`):

| 테이블 | 행 수 | grain |
|--------|------:|-------|
| `categories.parquet` | 691 | category_id → category_code |
| `products.parquet` | 206,876 | product_id → category_id, brand |
| `events.parquet` (fact) | 109,950,743 | 이벤트 1건 = 1행 (상품 속성 제거, price는 시점 값이라 유지) |

무결성: `product_id → category_id/brand`는 사실상 1:1 (충돌은 최빈값으로 확정), 참조 무결성 위반 0건.

## 스크립트 & 노트북 (`eda/`)

| 파일 | 설명 |
|------|------|
| `00_smoke_test.py` | CSV 로드/스키마 추론 확인 |
| `01_eda.py` | 원본 CSV 기반 EDA (퍼널·매출·시계열·세션 등, 콘솔 출력) |
| `02_eda.ipynb` | 위 EDA의 노트북 버전 (matplotlib 차트) |
| `03_check_integrity.py` | 정규화 전 관계 무결성 점검 |
| `04_normalize.py` | 정규화 → Parquet 3개 생성 |
| `05_eda_normalized.ipynb` | **정규화 Parquet 기반 EDA** (조인 분석, 권장) |

### 노트북 실행

```bash
uv run jupyter lab   # 또는 jupyter notebook
```

- **프로젝트 루트에서 실행**하세요. 노트북이 데이터 경로를 루트 기준으로 자동 탐지합니다.
- 커널은 이 프로젝트의 `.venv`(uv 환경)를 선택하세요.

## 주요 발견 (Oct + Nov 2019)

- **퍼널**: view→cart 3.79%, cart→purchase 41.96%, view→purchase 1.59% — 병목은 조회→장바구니 단계.
- **매출 집중**: 카테고리는 스마트폰이 압도적, 브랜드는 Apple + Samsung이 지배.
- **시즌성**: 11/17 매출 폭증(평소의 6배, 블랙프라이데이 세일 추정).
- **데이터 품질**: `category_code` 32% 결측, `brand` 14% 결측, `price`/`session`은 결측 0%.