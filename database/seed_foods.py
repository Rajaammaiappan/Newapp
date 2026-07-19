"""Seed the food_database with common Indian (South Indian focus) + general foods.

Values are typical estimates per stated serving. Coach can edit/add more
from the Coach portal → Food Logs → Food Database tab.
Idempotent: only inserts when the table is empty.
"""
from database.connection import query, execute

# (name, category, serving, kcal, protein, carbs, fat)
FOODS = [
    # ---- Breakfast (South Indian) ----
    ("Idli", "Breakfast (South Indian)", "2 pieces", 120, 4, 24, 0.6),
    ("Plain Dosa", "Breakfast (South Indian)", "1 medium", 170, 3.5, 28, 5),
    ("Masala Dosa", "Breakfast (South Indian)", "1 medium", 350, 6, 50, 13),
    ("Set Dosa", "Breakfast (South Indian)", "2 pieces", 260, 5, 44, 7),
    ("Rava Dosa", "Breakfast (South Indian)", "1 medium", 220, 4, 32, 8),
    ("Upma", "Breakfast (South Indian)", "1 bowl (200g)", 250, 6, 40, 8),
    ("Ven Pongal", "Breakfast (South Indian)", "1 bowl (200g)", 320, 9, 45, 12),
    ("Poha", "Breakfast (South Indian)", "1 bowl (180g)", 230, 5, 42, 5),
    ("Medu Vada", "Breakfast (South Indian)", "1 piece", 130, 4, 14, 7),
    ("Uttapam (Onion)", "Breakfast (South Indian)", "1 medium", 210, 5, 34, 6),
    ("Appam", "Breakfast (South Indian)", "2 pieces", 200, 3, 40, 3),
    ("Puttu", "Breakfast (South Indian)", "1 cup (150g)", 220, 4, 45, 2),
    ("Idiyappam", "Breakfast (South Indian)", "2 pieces", 180, 3, 38, 1),
    ("Chapati / Phulka", "Breakfast (South Indian)", "2 pieces", 200, 6, 36, 4),
    ("Poori with Saagu", "Breakfast (South Indian)", "2 poori + saagu", 420, 7, 52, 20),
    # ---- Sides & Chutneys ----
    ("Coconut Chutney", "Sides & Chutneys", "2 tbsp (30g)", 60, 1, 3, 5),
    ("Tomato Chutney", "Sides & Chutneys", "2 tbsp (30g)", 40, 1, 5, 2),
    ("Mint/Coriander Chutney", "Sides & Chutneys", "2 tbsp (30g)", 25, 1, 3, 1),
    ("Sambar", "Sides & Chutneys", "1 cup (150ml)", 110, 5, 16, 3),
    ("Rasam", "Sides & Chutneys", "1 cup (150ml)", 60, 2, 9, 2),
    ("Curd / Dahi", "Sides & Chutneys", "1 cup (150g)", 90, 5, 7, 5),
    ("Pickle", "Sides & Chutneys", "1 tsp", 20, 0, 1, 2),
    # ---- Lunch / Dinner ----
    ("White Rice (cooked)", "Lunch / Dinner", "1 cup (160g)", 205, 4, 45, 0.5),
    ("Brown Rice (cooked)", "Lunch / Dinner", "1 cup (160g)", 215, 5, 45, 1.8),
    ("Curd Rice", "Lunch / Dinner", "1 bowl (250g)", 260, 8, 40, 8),
    ("Sambar Rice", "Lunch / Dinner", "1 bowl (300g)", 320, 9, 55, 7),
    ("Lemon Rice", "Lunch / Dinner", "1 bowl (250g)", 330, 6, 55, 10),
    ("Vegetable Biryani", "Lunch / Dinner", "1 plate (300g)", 420, 9, 65, 14),
    ("Chicken Biryani", "Lunch / Dinner", "1 plate (300g)", 550, 28, 60, 20),
    ("Dal / Paruppu", "Lunch / Dinner", "1 cup (150g)", 150, 9, 22, 3),
    ("Chicken Curry", "Lunch / Dinner", "1 cup (180g)", 280, 26, 8, 16),
    ("Fish Curry", "Lunch / Dinner", "1 cup (180g)", 220, 24, 6, 11),
    ("Egg Curry (2 eggs)", "Lunch / Dinner", "1 serving", 260, 14, 8, 19),
    ("Paneer Butter Masala", "Lunch / Dinner", "1 cup (180g)", 350, 14, 12, 27),
    ("Mixed Veg Poriyal", "Lunch / Dinner", "1 cup (120g)", 100, 3, 12, 4),
    ("Chapati with Dal", "Lunch / Dinner", "2 chapati + dal", 350, 15, 58, 7),
    # ---- Protein & Eggs ----
    ("Boiled Egg", "Protein & Eggs", "1 egg", 78, 6.3, 0.6, 5.3),
    ("Egg Omelette (2 eggs)", "Protein & Eggs", "1 serving", 220, 13, 2, 17),
    ("Grilled Chicken Breast", "Protein & Eggs", "100g", 165, 31, 0, 3.6),
    ("Paneer (raw)", "Protein & Eggs", "100g", 265, 18, 4, 20),
    ("Whey Protein Shake", "Protein & Eggs", "1 scoop + water", 120, 24, 3, 1.5),
    ("Sprouts Salad", "Protein & Eggs", "1 bowl (150g)", 120, 8, 18, 1),
    ("Peanuts (roasted)", "Protein & Eggs", "30g handful", 170, 7, 5, 14),
    # ---- Snacks ----
    ("Banana", "Snacks & Fruits", "1 medium", 105, 1.3, 27, 0.4),
    ("Apple", "Snacks & Fruits", "1 medium", 95, 0.5, 25, 0.3),
    ("Mango", "Snacks & Fruits", "1 cup sliced", 100, 1.4, 25, 0.6),
    ("Samosa", "Snacks & Fruits", "1 piece", 260, 4, 28, 15),
    ("Murukku", "Snacks & Fruits", "2 pieces", 180, 3, 20, 10),
    ("Biscuits (Marie)", "Snacks & Fruits", "4 biscuits", 110, 2, 20, 3),
    ("Mixture / Namkeen", "Snacks & Fruits", "30g", 160, 4, 15, 10),
    ("Dry Fruits Mix", "Snacks & Fruits", "30g", 160, 4, 12, 11),
    # ---- Drinks ----
    ("Filter Coffee (with milk & sugar)", "Drinks", "1 cup (150ml)", 90, 2, 12, 3.5),
    ("Tea (with milk & sugar)", "Drinks", "1 cup (150ml)", 75, 2, 11, 2.5),
    ("Black Coffee (no sugar)", "Drinks", "1 cup", 5, 0.3, 0, 0),
    ("Buttermilk / Neer Mor", "Drinks", "1 glass (200ml)", 40, 2, 4, 1.5),
    ("Tender Coconut Water", "Drinks", "1 glass (200ml)", 40, 0.5, 9, 0),
    ("Fresh Lime Juice (sugar)", "Drinks", "1 glass (200ml)", 60, 0, 15, 0),
    ("Milk (full cream)", "Drinks", "1 glass (200ml)", 130, 6.5, 10, 7),
]


def seed_foods():
    if query("SELECT 1 FROM food_database LIMIT 1"):
        return False
    for f in FOODS:
        execute(
            "INSERT INTO food_database (name, category, serving, calories, protein, carbs, fat) "
            "VALUES (?,?,?,?,?,?,?)", f)
    return True


if __name__ == "__main__":
    print("seeded:", seed_foods())
