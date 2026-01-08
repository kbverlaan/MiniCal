-- Advanced Workout Tracking
-- Tracks exercises with sets, reps, weight for progressive overload

-- Main workout session table
CREATE TABLE IF NOT EXISTS workout_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    name TEXT NOT NULL, -- e.g., "Upper Body A", "Leg Day", "Push"
    duration_minutes INTEGER, -- Total workout duration
    notes TEXT, -- Overall workout notes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Individual exercise sets within a workout
CREATE TABLE IF NOT EXISTS exercise_sets (
    id BIGSERIAL PRIMARY KEY,
    workout_session_id BIGINT NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise_name TEXT NOT NULL, -- e.g., "Bench Press", "Squat", "Deadlift"
    set_number INTEGER NOT NULL, -- 1, 2, 3, etc.
    reps INTEGER NOT NULL, -- Number of reps completed
    weight DECIMAL(6, 2), -- Weight in kg (optional for bodyweight exercises)
    rpe INTEGER CHECK (rpe >= 1 AND rpe <= 10), -- Rate of Perceived Exertion (1-10)
    notes TEXT, -- Set-specific notes: "felt heavy", "PR!", etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_workout_sessions_user_date ON workout_sessions(user_id, date DESC);
CREATE INDEX idx_exercise_sets_workout ON exercise_sets(workout_session_id);
CREATE INDEX idx_exercise_sets_name ON exercise_sets(exercise_name); -- For finding PRs

-- View for easy workout summary queries
CREATE OR REPLACE VIEW workout_summary AS
SELECT 
    ws.id as session_id,
    ws.user_id,
    ws.date,
    ws.name as workout_name,
    ws.duration_minutes,
    COUNT(DISTINCT es.exercise_name) as num_exercises,
    COUNT(es.id) as total_sets,
    SUM(es.reps * COALESCE(es.weight, 0)) as total_volume_kg
FROM workout_sessions ws
LEFT JOIN exercise_sets es ON ws.id = es.workout_session_id
GROUP BY ws.id, ws.user_id, ws.date, ws.name, ws.duration_minutes;

-- Comments
COMMENT ON TABLE workout_sessions IS 'Workout session metadata (date, name, duration)';
COMMENT ON TABLE exercise_sets IS 'Individual sets per exercise with reps, weight, RPE';
COMMENT ON COLUMN exercise_sets.rpe IS 'Rate of Perceived Exertion: 1=very easy, 10=max effort';
COMMENT ON COLUMN exercise_sets.weight IS 'Weight in kg (NULL for bodyweight exercises)';
COMMENT ON VIEW workout_summary IS 'Aggregated workout stats per session';
