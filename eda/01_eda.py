"""이커머스 행동 데이터 EDA (DuckDB, DB 셋업 없이 CSV 직접 쿼리).

Oct + Nov 두 파일을 하나의 뷰(events)로 묶어 분석한다.
"""

import duckdb

con = duckdb.connect()

# 두 CSV를 events 라는 뷰로 통합 (union_by_name=true로 컬럼명 기준 결합)
con.sql("""
    CREATE VIEW events AS
    SELECT * FROM read_csv_auto('data/2019-*.csv', union_by_name=true)
""")


def show(title: str, sql: str):
    print(f"\n{'='*70}\n{title}\n{'='*70}")
    print(con.sql(sql))


# 1. 기본 규모/기간
show("1. 전체 규모 & 기간", """
    SELECT
        count(*)                     AS total_rows,
        min(event_time)              AS start_time,
        max(event_time)              AS end_time,
        count(DISTINCT user_id)      AS unique_users,
        count(DISTINCT product_id)   AS unique_products,
        count(DISTINCT user_session) AS unique_sessions
    FROM events
""")

# 2. 이벤트 타입 분포
show("2. 이벤트 타입 분포", """
    SELECT event_type,
           count(*) AS n,
           round(100.0 * count(*) / sum(count(*)) OVER (), 2) AS pct
    FROM events
    GROUP BY event_type ORDER BY n DESC
""")

# 3. 결측치 현황
show("3. 결측치 현황", """
    SELECT
        round(100.0*count(*) FILTER (WHERE category_code IS NULL)/count(*),2) AS null_category_pct,
        round(100.0*count(*) FILTER (WHERE brand IS NULL)/count(*),2)         AS null_brand_pct,
        round(100.0*count(*) FILTER (WHERE price IS NULL)/count(*),2)         AS null_price_pct,
        round(100.0*count(*) FILTER (WHERE user_session IS NULL)/count(*),2)  AS null_session_pct
    FROM events
""")

# 4. 퍼널 (view -> cart -> purchase)
show("4. 전환 퍼널", """
    WITH f AS (
        SELECT
            count(*) FILTER (WHERE event_type='view')     AS views,
            count(*) FILTER (WHERE event_type='cart')     AS carts,
            count(*) FILTER (WHERE event_type='purchase') AS purchases
        FROM events
    )
    SELECT views, carts, purchases,
        round(100.0*carts/NULLIF(views,0),2)     AS view_to_cart_pct,
        round(100.0*purchases/NULLIF(carts,0),2) AS cart_to_purchase_pct,
        round(100.0*purchases/NULLIF(views,0),2) AS view_to_purchase_pct
    FROM f
""")

# 5. 매출 상위 카테고리
show("5. 매출 상위 카테고리 TOP 15", """
    SELECT category_code,
           count(*)          AS purchases,
           round(sum(price))  AS revenue,
           round(avg(price),2) AS avg_price
    FROM events
    WHERE event_type='purchase' AND category_code IS NOT NULL
    GROUP BY category_code ORDER BY revenue DESC LIMIT 15
""")

# 6. 매출 상위 브랜드
show("6. 매출 상위 브랜드 TOP 15", """
    SELECT brand,
           count(*)          AS purchases,
           round(sum(price))  AS revenue
    FROM events
    WHERE event_type='purchase' AND brand IS NOT NULL
    GROUP BY brand ORDER BY revenue DESC LIMIT 15
""")

# 7. 일별 매출 추이
show("7. 일별 매출 추이 (상위 10일)", """
    SELECT date_trunc('day', event_time)::DATE AS day,
           count(*)          AS purchases,
           round(sum(price))  AS revenue
    FROM events
    WHERE event_type='purchase'
    GROUP BY day ORDER BY revenue DESC LIMIT 10
""")

# 8. 시간대별 구매 패턴
show("8. 시간대(UTC)별 구매량", """
    SELECT extract(hour FROM event_time) AS hour,
           count(*) AS purchases
    FROM events
    WHERE event_type='purchase'
    GROUP BY hour ORDER BY hour
""")

# 9. 가격 분포 (구매 기준)
show("9. 구매 가격 분포", """
    SELECT
        round(min(price),2)    AS min_price,
        round(avg(price),2)    AS avg_price,
        round(median(price),2) AS median_price,
        round(quantile(price,0.9),2) AS p90_price,
        round(max(price),2)    AS max_price
    FROM events WHERE event_type='purchase'
""")

# 10. 세션당 이벤트 수
show("10. 세션당 평균/중앙 이벤트 수", """
    WITH s AS (
        SELECT user_session, count(*) AS cnt
        FROM events WHERE user_session IS NOT NULL
        GROUP BY user_session
    )
    SELECT round(avg(cnt),2) AS avg_events_per_session,
           median(cnt)       AS median_events_per_session,
           max(cnt)          AS max_events_per_session
    FROM s
""")

print("\n완료.")
