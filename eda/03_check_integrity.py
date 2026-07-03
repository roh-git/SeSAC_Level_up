"""정규화 전 관계 무결성 점검.

- product_id -> (category_id, brand) 가 얼마나 안정적인가?
- category_id -> category_code 가 1:1 인가?
같은 product_id가 여러 category/brand를 갖는다면 단순 정규화가 깨진다.
"""

import duckdb

con = duckdb.connect()
con.sql("""
    CREATE VIEW events AS
    SELECT * FROM read_csv_auto('data/2019-*.csv', union_by_name=true)
""")


def show(title, sql):
    print(f"\n{'='*60}\n{title}\n{'='*60}")
    print(con.sql(sql))


# 1) product_id가 서로 다른 category_id를 몇 개나 갖는가
show("1. product_id -> distinct category_id 개수 분포", """
    WITH pc AS (
        SELECT product_id, count(DISTINCT category_id) AS n_cat
        FROM events GROUP BY product_id
    )
    SELECT n_cat, count(*) AS n_products
    FROM pc GROUP BY n_cat ORDER BY n_cat
""")

# 2) product_id가 서로 다른 brand를 몇 개나 갖는가 (NULL 제외하고 비교)
show("2. product_id -> distinct brand 개수 분포 (non-null brand 기준)", """
    WITH pb AS (
        SELECT product_id, count(DISTINCT brand) AS n_brand
        FROM events WHERE brand IS NOT NULL
        GROUP BY product_id
    )
    SELECT n_brand, count(*) AS n_products
    FROM pb GROUP BY n_brand ORDER BY n_brand
""")

# 3) category_id -> category_code 가 1:1 인가
show("3. category_id -> distinct category_code 개수 (non-null 기준)", """
    WITH cc AS (
        SELECT category_id, count(DISTINCT category_code) AS n_code
        FROM events WHERE category_code IS NOT NULL
        GROUP BY category_id
    )
    SELECT n_code, count(*) AS n_categories
    FROM cc GROUP BY n_code ORDER BY n_code
""")

# 4) 유니크 개수 요약
show("4. 카디널리티 요약", """
    SELECT
        count(DISTINCT product_id)   AS products,
        count(DISTINCT category_id)  AS categories,
        count(DISTINCT user_id)      AS users,
        count(DISTINCT user_session) AS sessions,
        count(*)                     AS events
    FROM events
""")