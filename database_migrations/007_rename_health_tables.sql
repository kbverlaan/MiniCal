-- Rename health tracking tables to match naming convention (meals, workouts)
-- Migration 007: Simplify health table names

-- 1. Rename tables
ALTER TABLE sleep_logs RENAME TO sleep;
ALTER TABLE heart_rate_logs RENAME TO heart_rate;
ALTER TABLE stress_logs RENAME TO stress;

-- 2. Update recovery_scores view to use new table names
DROP VIEW IF EXISTS recovery_scores;

CREATE OR REPLACE VIEW recovery_scores AS
SELECT 
    s.user_id,
    s.date,
    s.quality_score as sleep_score,
    hr.hrv_avg,
    st.avg_stress,
    -- Calculate combined recovery score (0-100)
    ROUND(
        (s.quality_score * 0.4) + 
        (LEAST(hr.hrv_avg / 100, 1.0) * 100 * 0.3) + 
        ((100 - st.avg_stress) * 0.3)
    ) as recovery_score
FROM sleep s
LEFT JOIN heart_rate hr ON s.user_id = hr.user_id AND s.date = hr.date
LEFT JOIN stress st ON s.user_id = st.user_id AND s.date = st.date
ORDER BY s.date DESC;

COMMENT ON VIEW recovery_scores IS 'Combined recovery score based on sleep quality, HRV, and stress levels';
