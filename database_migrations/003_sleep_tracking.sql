-- Sleep Tracking Table
-- Tracks sleep duration, quality, and notes for correlation with performance

CREATE TABLE IF NOT EXISTS sleep_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    hours DECIMAL(4, 2) NOT NULL, -- e.g., 7.5 hours
    quality INTEGER CHECK (quality >= 1 AND quality <= 5), -- 1=terrible, 5=excellent (optional)
    notes TEXT, -- "Woke up 2x", "Restless", etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Ensure one sleep log per day per user
    UNIQUE(user_id, date)
);

-- Index for quick queries by user and date range
CREATE INDEX idx_sleep_logs_user_date ON sleep_logs(user_id, date DESC);

-- Comments for documentation
COMMENT ON TABLE sleep_logs IS 'Sleep tracking for correlation with performance and recovery';
COMMENT ON COLUMN sleep_logs.hours IS 'Total sleep duration in hours (decimal)';
COMMENT ON COLUMN sleep_logs.quality IS 'Subjective sleep quality: 1=terrible, 2=poor, 3=ok, 4=good, 5=excellent';
COMMENT ON COLUMN sleep_logs.notes IS 'Optional notes about sleep (woke up, restless, dreams, etc.)';
