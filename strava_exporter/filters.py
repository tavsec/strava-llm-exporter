def filter_by_sport(
    activities: list[dict], sports: list[str] | None
) -> list[dict]:
    if not sports:
        return activities
    sports_lower = {s.lower() for s in sports}
    return [
        a for a in activities
        if a.get("sport_type", "").lower() in sports_lower
    ]
