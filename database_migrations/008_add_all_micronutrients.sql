-- Migration 008: Add missing micronutrients

ALTER TABLE meals
ADD COLUMN IF NOT EXISTS vitamin_d DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS vitamin_c DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS vitamin_b12 DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS magnesium DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS calcium DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS iron DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS zinc DECIMAL(10,2) DEFAULT 0,
ADD COLUMN IF NOT EXISTS creatine DECIMAL(10,2) DEFAULT 0;

COMMENT ON COLUMN meals.vitamin_d IS 'Vitamin D in mcg';
COMMENT ON COLUMN meals.vitamin_c IS 'Vitamin C in mg';
COMMENT ON COLUMN meals.vitamin_b12 IS 'Vitamin B12 in mcg';
COMMENT ON COLUMN meals.magnesium IS 'Magnesium in mg';
COMMENT ON COLUMN meals.calcium IS 'Calcium in mg';
COMMENT ON COLUMN meals.iron IS 'Iron in mg';
COMMENT ON COLUMN meals.zinc IS 'Zinc in mg';
COMMENT ON COLUMN meals.creatine IS 'Creatine in grams';

-- Re-create the view to include new columns
DROP VIEW IF EXISTS daily_nutrition_detailed;

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
    SUM(omega3_ala + omega3_epa_dha) as total_omega3,
    SUM(vitamin_d) as total_vitamin_d,
    SUM(vitamin_c) as total_vitamin_c,
    SUM(vitamin_b12) as total_vitamin_b12,
    SUM(magnesium) as total_magnesium,
    SUM(calcium) as total_calcium,
    SUM(iron) as total_iron,
    SUM(zinc) as total_zinc,
    SUM(creatine) as total_creatine
FROM meals
GROUP BY user_id, date
ORDER BY date DESC;
