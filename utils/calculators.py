"""Pure fitness calculation functions."""
import math

ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55,
            "active": 1.725, "very_active": 1.9}


def bmi(weight_kg, height_cm):
    h = height_cm / 100
    return round(weight_kg / (h * h), 1)


def bmi_category(v):
    if v < 18.5: return "Underweight"
    if v < 25: return "Normal"
    if v < 30: return "Overweight"
    return "Obese"


def bmr(weight_kg, height_cm, age, gender):
    """Mifflin-St Jeor."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return round(base + (5 if gender.lower().startswith("m") else -161))


def tdee(bmr_val, activity_level):
    return round(bmr_val * ACTIVITY.get(activity_level, 1.2))


def macros(tdee_val, goal):
    """Return (calories, protein_g, carbs_g, fat_g) for goal."""
    cal = tdee_val + ({"fat_loss": -500, "muscle_gain": 300}.get(goal, 0))
    p_pct, c_pct, f_pct = {"fat_loss": (0.40, 0.30, 0.30),
                           "muscle_gain": (0.30, 0.45, 0.25)}.get(goal, (0.30, 0.40, 0.30))
    return cal, round(cal * p_pct / 4), round(cal * c_pct / 4), round(cal * f_pct / 9)


def protein_range(weight_kg):
    return round(weight_kg * 1.6), round(weight_kg * 2.2)


def water_ml(weight_kg):
    return int(weight_kg * 35)


def ideal_weight(height_cm, gender):
    """Devine formula."""
    inches_over_5ft = max(0, height_cm / 2.54 - 60)
    base = 50 if gender.lower().startswith("m") else 45.5
    return round(base + 2.3 * inches_over_5ft, 1)


def body_fat_navy(gender, waist_cm, neck_cm, height_cm, hips_cm=None):
    """US Navy method."""
    try:
        if gender.lower().startswith("m"):
            v = 495 / (1.0324 - 0.19077 * math.log10(waist_cm - neck_cm)
                       + 0.15456 * math.log10(height_cm)) - 450
        else:
            v = 495 / (1.29579 - 0.35004 * math.log10(waist_cm + (hips_cm or waist_cm) - neck_cm)
                       + 0.22100 * math.log10(height_cm)) - 450
        return round(v, 1)
    except (ValueError, ZeroDivisionError):
        return None
