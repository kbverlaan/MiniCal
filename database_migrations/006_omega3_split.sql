-- Split omega-3 into ALA (plant-based) and EPA/DHA (marine-based)
-- Migration 006: Omega-3 differentiation + additional nutrients

-- 1. Add new columns for ALA and EPA/DHA
ALTER TABLE meals
ADD COLUMN omega3_ala DECIMAL(10,2) DEFAULT 0,
ADD COLUMN omega3_epa_dha DECIMAL(10,2) DEFAULT 0;

-- 2. Migrate existing omega3 data to ALA (user has only logged flaxseed so far)
UPDATE meals
SET omega3_ala = omega3
WHERE omega3 > 0;

-- Note: We keep the old omega3 column for now to avoid breaking existing code
-- It can be removed in a future migration after all code is updated
-- For now, omega3 will represent total omega-3 (ALA + EPA/DHA)

-- 3. Create view for easy querying
CREATE OR REPLACE VIEW daily_nutrition_detailed AS
SELECT 
    user_id,
    date,
    SUM(calories) as total_calories,
    SUM(protein) as total_protein,
    SUM(carbs) as total_carbs,
    SUM(fat) as total_fat,
    SUM(fiber) as total_fiber,
    SUM(sugar) as total_sugar,
    SUM(saturated_fat) as total_saturated_fat,
    SUM(omega3_ala) as total_omega3_ala,
    SUM(omega3_epa_dha) as total_omega3_epa_dha,
    SUM(omega3_ala + omega3_epa_dha) as total_omega3
FROM meals
GROUP BY user_id, date
ORDER BY date DESC;

COMMENT ON COLUMN meals.omega3_ala IS 'Alpha-Linolenic Acid (plant-based omega-3) in mg';
COMMENT ON COLUMN meals.omega3_epa_dha IS 'EPA + DHA (marine-based omega-3) in mg';
COMMENT ON COLUMN meals.fiber IS 'Dietary fiber in grams';
COMMENT ON COLUMN meals.sugar IS 'Total sugars in grams';
COMMENT ON COLUMN meals.saturated_fat IS 'Saturated fat in grams';
FROM meals
GROUP BY user_id, date
ORDER BY date DESC;

COMMENT ON COLUMN meals.omega3_ala IS 'Alpha-Linolenic Acid (plant-based omega-3) in grams';
COMMENT ON COLUMN meals.omega3_epa_dha IS 'EPA + DHA (marine-based omega-3) in grams';
