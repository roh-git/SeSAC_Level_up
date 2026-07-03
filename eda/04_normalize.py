"""이커머스 이벤트 로그를 정규화하여 Parquet 3개로 저장.

출력 (data/normalized/):
  categories.parquet  (category_id, category_code)
  products.parquet    (product_id, category_id, brand)
  events.parquet      (event_time, event_type, product_id, price, user_id, user_session)

무결성 점검(03_check_integrity.py) 결과 product_id -> category_id/brand 는
거의 1:1 이므로, 소수 충돌은 최빈값(mode)으로 확정한다.
"""

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "normalized"
OUT.mkdir(exist_ok=True)

con = duckdb.connect()
con.sql(f"""
    CREATE VIEW events_raw AS
    SELECT * FROM read_csv_auto('{(DATA / "2019-*.csv").as_posix()}', union_by_name=true)
""")

# --- categories: category_id -> category_code (1:1) -----------------------
con.sql(f"""
    COPY (
        SELECT DISTINCT category_id, category_code
        FROM events_raw
        WHERE category_id IS NOT NULL
        ORDER BY category_id
    ) TO '{(OUT / "categories.parquet").as_posix()}' (FORMAT parquet)
""")

# --- products: product_id -> (category_id, brand), 충돌은 최빈값 ----------
# mode()는 DuckDB 집계함수. NULL은 자동 무시되므로 brand 결측이 있어도 안전.
con.sql(f"""
    COPY (
        SELECT
            product_id,
            mode(category_id) AS category_id,
            mode(brand)       AS brand
        FROM events_raw
        WHERE product_id IS NOT NULL
        GROUP BY product_id
        ORDER BY product_id
    ) TO '{(OUT / "products.parquet").as_posix()}' (FORMAT parquet)
""")

# --- events (fact): 상품 속성 제거, price는 시점 값이라 유지 --------------
con.sql(f"""
    COPY (
        SELECT
            event_time,
            event_type,
            product_id,
            price,
            user_id,
            user_session
        FROM events_raw
    ) TO '{(OUT / "events.parquet").as_posix()}' (FORMAT parquet)
""")

# --- 검증 리포트 ----------------------------------------------------------
def n(path):
    return con.sql(
        f"SELECT count(*) FROM read_parquet('{path.as_posix()}')"
    ).fetchone()[0]

print("=== 정규화 완료 ===")
for name in ("categories", "products", "events"):
    p = OUT / f"{name}.parquet"
    size_mb = p.stat().st_size / 1024 / 1024
    print(f"  {name:11s}: {n(p):>12,} rows   {size_mb:8.1f} MB   ({p})")

# 원본 CSV 총 용량 대비
csv_mb = sum(f.stat().st_size for f in DATA.glob("2019-*.csv")) / 1024 / 1024
parquet_mb = sum((OUT / f"{x}.parquet").stat().st_size for x in
                 ("categories", "products", "events")) / 1024 / 1024
print(f"\n원본 CSV 합계 : {csv_mb:,.0f} MB")
print(f"Parquet 합계  : {parquet_mb:,.0f} MB  ({parquet_mb/csv_mb*100:.1f}%)")

# 참조 무결성: events의 모든 product_id가 products에 있는가
orphans = con.sql(f"""
    SELECT count(*) FROM read_parquet('{(OUT / "events.parquet").as_posix()}') e
    LEFT JOIN read_parquet('{(OUT / "products.parquet").as_posix()}') p
      USING (product_id)
    WHERE p.product_id IS NULL AND e.product_id IS NOT NULL
""").fetchone()[0]
print(f"\n참조 무결성 위반(고아 product_id): {orphans}")