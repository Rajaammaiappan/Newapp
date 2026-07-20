"""Nutrition: food database lookup, food logging, AI photo calorie estimation."""
import base64
import json
import os
import re
from datetime import date, timedelta
from pathlib import Path

import requests

from database.connection import query, execute

TODAY = lambda: date.today().isoformat()  # noqa: E731

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "assets" / "uploads" / "food"

MEAL_TYPES = ["Breakfast", "Lunch", "Dinner", "Snack"]


# ---------------- Food database ----------------
def food_categories():
    rows = query("SELECT DISTINCT category FROM food_database WHERE is_active=1 ORDER BY category")
    return [r["category"] for r in rows]


def foods_in_category(category: str):
    return query(
        "SELECT * FROM food_database WHERE is_active=1 AND category=? ORDER BY name",
        (category,))


def search_foods(term: str):
    return query(
        "SELECT * FROM food_database WHERE is_active=1 AND name LIKE ? ORDER BY name LIMIT 25",
        (f"%{term}%",))


def add_food_item(name, category, serving, calories, protein, carbs, fat):
    return execute(
        "INSERT INTO food_database (name, category, serving, calories, protein, carbs, fat) "
        "VALUES (?,?,?,?,?,?,?)", (name, category, serving, calories, protein, carbs, fat))


def deactivate_food(food_id: int):
    execute("UPDATE food_database SET is_active=0 WHERE id=?", (food_id,))


# ---------------- Food log ----------------
def log_food(client_id, meal_type, food_name, calories, protein=0, carbs=0, fat=0,
             servings=1.0, source="database", photo_path=None, ai_notes=None,
             log_date=None, entry_kind="extra", replaces_item_id=None):
    return execute(
        "INSERT INTO food_log (client_id, log_date, meal_type, food_name, servings, "
        "calories, protein, carbs, fat, source, photo_path, ai_notes, "
        "entry_kind, replaces_item_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (client_id, log_date or TODAY(), meal_type, food_name, servings,
         round(calories, 1), round(protein, 1), round(carbs, 1), round(fat, 1),
         source, photo_path, ai_notes, entry_kind, replaces_item_id))


# ---------------- Plan-aware day calculation ----------------
def todays_plan_items(client_id, log_date=None):
    """Diet items scheduled for this weekday from the client's active plan."""
    from services import plan_service as ps
    plan = ps.active_diet(client_id)
    if not plan:
        return []
    d = date.fromisoformat(log_date) if log_date else date.today()
    day = ps.DAYS[d.weekday()]
    if ps.plan_days(plan["id"]):
        return ps.diet_items_for_day(plan["id"], day)
    return ps.diet_items(plan["id"])


def skipped_ids(client_id, log_date=None):
    rows = query("SELECT diet_item_id FROM skipped_meals WHERE client_id=? AND log_date=?",
                 (client_id, log_date or TODAY()))
    return {r["diet_item_id"] for r in rows}


def set_skipped(client_id, diet_item_id, skipped: bool, log_date=None):
    d = log_date or TODAY()
    if skipped:
        try:
            execute("INSERT INTO skipped_meals (client_id, log_date, diet_item_id) "
                    "VALUES (?,?,?)", (client_id, d, diet_item_id))
        except Exception:
            pass  # already skipped
    else:
        execute("DELETE FROM skipped_meals WHERE client_id=? AND log_date=? "
                "AND diet_item_id=?", (client_id, d, diet_item_id))


def effective_day(client_id, log_date=None):
    """The number that matters: plan-aware calories/protein for the day.

    = planned meals (except skipped/replaced ones, which are assumed followed)
      + logged replacements + logged extras.
    """
    d = log_date or TODAY()
    items = todays_plan_items(client_id, d)
    logs = day_log(client_id, d)
    replaced = {r["replaces_item_id"] for r in logs
                if (r.get("entry_kind") == "replacement") and r.get("replaces_item_id")}
    skipped = skipped_ids(client_id, d)
    plan_cal = plan_pro = 0.0
    followed = []
    for it in items:
        if it["id"] in replaced or it["id"] in skipped:
            continue
        plan_cal += it["calories"] or 0
        plan_pro += it["protein_g"] or 0
        followed.append(it)
    log_cal = sum(r["calories"] or 0 for r in logs)
    log_pro = sum(r["protein"] or 0 for r in logs)
    return {
        "calories": plan_cal + log_cal,
        "protein": plan_pro + log_pro,
        "plan_calories": plan_cal,
        "logged_calories": log_cal,
        "followed_items": followed,
        "replaced_ids": replaced,
        "skipped_ids": skipped,
        "plan_item_count": len(items),
        "logs": logs,
    }


def delete_log(log_id: int, client_id: int):
    execute("DELETE FROM food_log WHERE id=? AND client_id=?", (log_id, client_id))


def day_log(client_id, log_date=None):
    return query(
        "SELECT * FROM food_log WHERE client_id=? AND log_date=? ORDER BY id",
        (client_id, log_date or TODAY()))


def day_totals(client_id, log_date=None):
    row = query(
        "SELECT COALESCE(SUM(calories),0) c, COALESCE(SUM(protein),0) p, "
        "COALESCE(SUM(carbs),0) cb, COALESCE(SUM(fat),0) f "
        "FROM food_log WHERE client_id=? AND log_date=?",
        (client_id, log_date or TODAY()))[0]
    return {"calories": row["c"], "protein": row["p"], "carbs": row["cb"], "fat": row["f"]}


def history_totals(client_id, days=7):
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    return query(
        "SELECT log_date, SUM(calories) calories, SUM(protein) protein "
        "FROM food_log WHERE client_id=? AND log_date>=? "
        "GROUP BY log_date ORDER BY log_date", (client_id, since))


def plan_targets(client_id):
    """Daily calorie/protein target from the client's active diet plan (sum of items)."""
    rows = query(
        "SELECT COALESCE(SUM(di.calories),0) c, COALESCE(SUM(di.protein_g),0) p "
        "FROM diet_items di JOIN diet_plans dp ON dp.id = di.plan_id "
        "WHERE dp.client_id=? AND dp.active=1", (client_id,))
    if rows and rows[0]["c"]:
        return {"calories": rows[0]["c"], "protein": rows[0]["p"]}
    return None


# ---------------- AI photo analysis (FREE Gemini first, Anthropic optional) ----------------
def _get_secret(name):
    val = os.environ.get(name)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(name)
    except Exception:
        return None


def ai_available() -> bool:
    return bool(_get_secret("GEMINI_API_KEY") or _get_secret("ANTHROPIC_API_KEY"))


_PROMPT = (
    "You are a nutrition estimation assistant for an Indian fitness coaching app. "
    "Look at this meal photo and identify the food items (Indian foods are common: "
    "idli, dosa, upma, rice, sambar, curries, chapati, etc.). Estimate the portion "
    "visible in the photo and give a nutrition breakdown.\n\n"
    "Respond with ONLY valid JSON, no other text, in this exact format:\n"
    '{"items": [{"name": "Idli", "quantity": "3 pieces", "calories": 180, '
    '"protein": 6, "carbs": 36, "fat": 1}], '
    '"total": {"calories": 240, "protein": 7, "carbs": 39, "fat": 6}, '
    '"confidence": "medium", "notes": "short note about assumptions"}\n\n'
    "If the image does not show food, respond with: "
    '{"items": [], "total": null, "confidence": "none", "notes": "No food detected"}'
)


def _parse_ai_json(text: str):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"error": "AI gave an unexpected answer. Please try another photo."}
    try:
        data = json.loads(match.group(0))
    except Exception:
        return {"error": "AI gave an unexpected answer. Please try another photo."}
    if not data.get("items"):
        return {"error": data.get("notes") or "No food detected in this photo."}
    return data


def _analyze_gemini(image_bytes: bytes, mime_type: str):
    key = _get_secret("GEMINI_API_KEY")
    model = _get_secret("GEMINI_MODEL") or "gemini-2.0-flash"
    b64 = base64.standard_b64encode(image_bytes).decode()
    resp = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        params={"key": key},
        json={"contents": [{"parts": [
            {"inline_data": {"mime_type": mime_type, "data": b64}},
            {"text": _PROMPT},
        ]}]},
        timeout=60)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_ai_json(text)


def _analyze_anthropic(image_bytes: bytes, mime_type: str):
    key = _get_secret("ANTHROPIC_API_KEY")
    b64 = base64.standard_b64encode(image_bytes).decode()
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": "claude-sonnet-4-6", "max_tokens": 800,
              "messages": [{"role": "user", "content": [
                  {"type": "image",
                   "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                  {"type": "text", "text": _PROMPT}]}]},
        timeout=60)
    resp.raise_for_status()
    return _parse_ai_json(resp.json()["content"][0]["text"])


def analyze_food_photo(image_bytes: bytes, mime_type: str = "image/jpeg"):
    """Meal photo → nutrition dict. Uses FREE Gemini key if set, else Anthropic."""
    if not ai_available():
        return {"error": "AI is not configured. Ask your coach to add a free "
                         "GEMINI_API_KEY (aistudio.google.com) in app settings."}
    providers = []
    if _get_secret("GEMINI_API_KEY"):
        providers.append(_analyze_gemini)
    if _get_secret("ANTHROPIC_API_KEY"):
        providers.append(_analyze_anthropic)
    last_err = None
    for fn in providers:
        try:
            return fn(image_bytes, mime_type)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            if code == 429:
                last_err = ("Free AI limit reached for now — please try again "
                            "in a minute (or tomorrow if daily limit is over).")
            elif code in (401, 403):
                last_err = "AI key is invalid. Ask your coach to check the API key."
            else:
                last_err = f"AI service error ({code}). Please try again."
        except Exception:
            last_err = "Could not reach the AI service. Check the internet and try again."
    return {"error": last_err or "AI analysis failed. Please try again."}


def save_food_photo(client_id: int, uploaded_file) -> str | None:
    """Persist the uploaded meal photo; returns relative path or None."""
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        ext = Path(uploaded_file.name).suffix.lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
            return None
        from datetime import datetime
        fname = f"c{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        path = UPLOAD_DIR / fname
        path.write_bytes(uploaded_file.getvalue())
        return str(path.relative_to(UPLOAD_DIR.parent.parent.parent))
    except Exception:
        return None
