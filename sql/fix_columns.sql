-- FitCoach — manual column fix (only needed if the app shows "no such column")
-- Paste these into the Turso SQL console and run them ONE BY ONE.
-- If any line says "duplicate column name" — that's fine, it means it already
-- exists; just continue with the next line.

ALTER TABLE clients ADD COLUMN daily_calorie_target REAL;
ALTER TABLE clients ADD COLUMN daily_protein_target REAL;
ALTER TABLE clients ADD COLUMN weekly_weight_target_kg REAL;
ALTER TABLE diet_items ADD COLUMN day_of_week TEXT;
