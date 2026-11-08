-- Step 2b: analytics layer. Small summary tables that dashboards and notebooks read from.

CREATE SCHEMA IF NOT EXISTS analytics;

-- Allowed vs blocked, by action
DROP TABLE IF EXISTS analytics.action_summary;
CREATE TABLE analytics.action_summary AS
SELECT
    action,
    COUNT(*)                                              AS sessions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)    AS pct_of_sessions,
    ROUND(AVG(bytes), 1)                                  AS avg_bytes,
    ROUND(AVG(packets), 1)                                AS avg_packets
FROM staging.firewall_sessions
GROUP BY action;

-- Block rate per destination port (ports with at least 50 sessions)
DROP TABLE IF EXISTS analytics.block_rate_by_port;
CREATE TABLE analytics.block_rate_by_port AS
SELECT
    destination_port,
    service_name,
    COUNT(*)                                                       AS sessions,
    SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END)                    AS blocked_sessions,
    ROUND(100.0 * AVG(CASE WHEN is_blocked THEN 1 ELSE 0 END), 1)  AS block_rate_pct
FROM staging.firewall_sessions
GROUP BY destination_port, service_name
HAVING COUNT(*) >= 50;

-- Unusual sessions: very large ones, and allowed sessions where nothing came back
DROP TABLE IF EXISTS analytics.outlier_sessions;
CREATE TABLE analytics.outlier_sessions AS
WITH cutoff AS (
    SELECT PERCENTILE_CONT(0.999) WITHIN GROUP (ORDER BY bytes) AS p999
    FROM staging.firewall_sessions
)
SELECT s.*, 'large_session' AS reason
FROM staging.firewall_sessions AS s
CROSS JOIN cutoff AS c
WHERE s.bytes > c.p999
UNION ALL
SELECT s.*, 'one_way_allowed' AS reason
FROM staging.firewall_sessions AS s
WHERE s.action = 'allow' AND s.bytes_received = 0;
