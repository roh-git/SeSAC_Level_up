"""DuckDB로 CSV를 직접 읽어 기본 정보를 확인하는 스모크 테스트."""

import duckdb

# Oct 파일 하나만 대상으로 빠르게 확인
OCT = "data/2019-Oct.csv"

con = duckdb.connect()  # in-memory

# 스키마 자동 추론 결과 확인
print("=== 컬럼 스키마 ===")
print(con.sql(f"DESCRIBE SELECT * FROM read_csv_auto('{OCT}')"))

print("\n=== 샘플 5행 ===")
print(con.sql(f"SELECT * FROM read_csv_auto('{OCT}') LIMIT 5"))

print("\n=== 전체 행 수 ===")
print(con.sql(f"SELECT count(*) AS rows FROM read_csv_auto('{OCT}')"))
