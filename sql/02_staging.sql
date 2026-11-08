-- Step 2a: staging layer. Typed, cleaned copy of the raw table plus helper columns.

CREATE SCHEMA IF NOT EXISTS staging;

-- Lookup table: well-known destination ports and the service they usually carry
DROP TABLE IF EXISTS staging.port_services;
CREATE TABLE staging.port_services (
    port         INTEGER PRIMARY KEY,
    service_name TEXT NOT NULL
);

INSERT INTO staging.port_services (port, service_name) VALUES
    (20, 'FTP-Data'), (21, 'FTP'), (22, 'SSH'), (23, 'Telnet'),
    (25, 'SMTP'), (53, 'DNS'), (80, 'HTTP'), (110, 'POP3'),
    (123, 'NTP'), (135, 'MS-RPC'), (137, 'NetBIOS-NS'), (139, 'NetBIOS-SSN'),
    (143, 'IMAP'), (161, 'SNMP'), (389, 'LDAP'), (443, 'HTTPS'),
    (445, 'SMB'), (465, 'SMTPS'), (514, 'Syslog'), (587, 'SMTP-Submission'),
    (993, 'IMAPS'), (995, 'POP3S'), (1433, 'MSSQL'), (3306, 'MySQL'),
    (3389, 'RDP'), (5432, 'PostgreSQL'), (5900, 'VNC'), (8080, 'HTTP-Alt'), (8443, 'HTTPS-Alt');

-- Cleaned sessions table
DROP TABLE IF EXISTS staging.firewall_sessions;
CREATE TABLE staging.firewall_sessions AS
SELECT
    ROW_NUMBER() OVER ()                          AS session_id,
    CAST(r.source_port AS INTEGER)                AS source_port,
    CAST(r.destination_port AS INTEGER)           AS destination_port,
    CAST(r.nat_source_port AS INTEGER)            AS nat_source_port,
    CAST(r.nat_destination_port AS INTEGER)       AS nat_destination_port,
    LOWER(TRIM(r.action))                         AS action,
    (LOWER(TRIM(r.action)) <> 'allow')            AS is_blocked,
    CAST(r.bytes AS BIGINT)                       AS bytes,
    CAST(r.bytes_sent AS BIGINT)                  AS bytes_sent,
    CAST(r.bytes_received AS BIGINT)              AS bytes_received,
    CAST(r.packets AS BIGINT)                     AS packets,
    CAST(r.pkts_sent AS BIGINT)                   AS pkts_sent,
    CAST(r.pkts_received AS BIGINT)               AS pkts_received,
    CAST(r.elapsed_time_sec AS INTEGER)           AS elapsed_seconds,
    COALESCE(p.service_name, 'Other')             AS service_name
FROM raw.firewall_sessions AS r
LEFT JOIN staging.port_services AS p
       ON p.port = r.destination_port;

ALTER TABLE staging.firewall_sessions ADD PRIMARY KEY (session_id);
CREATE INDEX idx_staging_dest_port ON staging.firewall_sessions (destination_port);
