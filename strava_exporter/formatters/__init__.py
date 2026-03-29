OPTIONAL_FIELDS = [
    "elev_high",
    "elev_low",
    "average_heartrate",
    "max_heartrate",
    "suffer_score",
    "average_speed",
    "max_speed",
    "average_watts",
    "weighted_average_watts",
    "max_watts",
    "kilojoules",
    "average_cadence",
    "calories",
    "average_temp",
    "device_name",
    "workout_type",
]


def extract_fields(activity: dict) -> dict:
    result = {
        "id": activity.get("id"),
        "name": activity.get("name"),
        "sport_type": activity.get("sport_type"),
        "start_date_local": activity.get("start_date_local"),
        "distance_m": activity.get("distance"),
        "moving_time_s": activity.get("moving_time"),
        "elapsed_time_s": activity.get("elapsed_time"),
        "total_elevation_gain_m": activity.get("total_elevation_gain"),
    }

    for field in OPTIONAL_FIELDS:
        val = activity.get(field)
        if val is not None:
            result[field] = val

    gear = activity.get("gear")
    if gear:
        result["gear_name"] = gear.get("name")

    splits = activity.get("splits_metric")
    if splits:
        result["splits"] = [
            {
                "km": i + 1,
                "elapsed_time_s": s.get("elapsed_time"),
                "distance_m": s.get("distance"),
                "average_heartrate": s.get("average_heartrate"),
                "average_speed_ms": s.get("average_speed"),
            }
            for i, s in enumerate(splits)
        ]

    return result
