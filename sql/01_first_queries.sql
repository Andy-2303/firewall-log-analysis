-- Q1: allowed vs blocked share, by action
SELECT
    action,
    COUNT(*) AS sessions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM raw.firewall_sessions
GROUP BY action
ORDER BY sessions DESC;

-- Q2: block rate per destination port (min 50 sessions)
SELECT
    destination_port,
    COUNT(*) AS sessions,
    ROUND(100.0 * AVG(CASE WHEN action <> 'allow' THEN 1 ELSE 0 END), 1) AS block_rate_pct
FROM raw.firewall_sessions
GROUP BY destination_port
HAVING COUNT(*) >= 50
ORDER BY sessions DESC
LIMIT 15;
