from strava_exporter.formatters import extract_fields


def _fmt_time(seconds: int | None) -> str:
    if seconds is None:
        return "N/A"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_pace(speed_ms: float | None) -> str:
    if not speed_ms:
        return "N/A"
    secs_per_km = 1000 / speed_ms
    m, s = divmod(int(secs_per_km), 60)
    return f"{m}:{s:02d}/km"


def _fmt_distance(meters: float | None) -> str:
    if meters is None:
        return "N/A"
    return f"{meters / 1000:.2f} km"


def _activity_section(activity: dict) -> str:
    f = extract_fields(activity)
    date = (f.get("start_date_local") or "")[:10]
    name = f.get("name", "Untitled")
    sport = f.get("sport_type", "")

    lines = [f"## {date} — {name} ({sport})"]

    volume_parts = [
        f"**Distance:** {_fmt_distance(f.get('distance_m'))}",
        f"**Moving time:** {_fmt_time(f.get('moving_time_s'))}",
        f"**Elevation gain:** {f.get('total_elevation_gain_m', 'N/A')} m",
    ]
    if "elev_high" in f and "elev_low" in f:
        volume_parts.append(f"**Elev range:** {f['elev_low']}–{f['elev_high']} m")
    lines.append("- " + " | ".join(volume_parts))

    intensity_parts = []
    if "average_heartrate" in f:
        intensity_parts.append(f"**Avg HR:** {f['average_heartrate']:.0f} bpm")
    if "max_heartrate" in f:
        intensity_parts.append(f"**Max HR:** {f['max_heartrate']:.0f} bpm")
    if "suffer_score" in f:
        intensity_parts.append(f"**Suffer score:** {f['suffer_score']}")
    if "average_speed" in f:
        intensity_parts.append(f"**Avg pace:** {_fmt_pace(f['average_speed'])}")
    if "calories" in f:
        intensity_parts.append(f"**Calories:** {f['calories']} kcal")
    if "average_cadence" in f:
        intensity_parts.append(f"**Cadence:** {f['average_cadence']:.0f} spm")
    if intensity_parts:
        lines.append("- " + " | ".join(intensity_parts))

    power_parts = []
    if "average_watts" in f:
        power_parts.append(f"**Avg power:** {f['average_watts']:.0f} W")
    if "weighted_average_watts" in f:
        power_parts.append(f"**NP:** {f['weighted_average_watts']:.0f} W")
    if "max_watts" in f:
        power_parts.append(f"**Max power:** {f['max_watts']:.0f} W")
    if "kilojoules" in f:
        power_parts.append(f"**Work:** {f['kilojoules']:.0f} kJ")
    if power_parts:
        lines.append("- " + " | ".join(power_parts))

    context_parts = []
    if "gear_name" in f:
        context_parts.append(f"**Gear:** {f['gear_name']}")
    if "device_name" in f:
        context_parts.append(f"**Device:** {f['device_name']}")
    if "average_temp" in f:
        context_parts.append(f"**Temp:** {f['average_temp']}°C")
    if context_parts:
        lines.append("- " + " | ".join(context_parts))

    splits = f.get("splits")
    if splits:
        lines.append("\n### Splits")
        lines.append("| km | Time | Pace | HR |")
        lines.append("|----|------|------|----|")
        for s in splits:
            hr = f"{s['average_heartrate']:.0f}" if s.get("average_heartrate") else "—"
            lines.append(
                f"| {s['km']} "
                f"| {_fmt_time(s['elapsed_time_s'])} "
                f"| {_fmt_pace(s['average_speed_ms'])} "
                f"| {hr} |"
            )

    return "\n".join(lines)


def format_markdown(
    activities: list[dict],
    from_date: str,
    to_date: str,
    sports: list[str] | None,
) -> str:
    sport_label = ", ".join(sports) if sports else "All sports"
    header = f"# Strava Export: {from_date} to {to_date} | {sport_label}\n"
    sections = [_activity_section(a) for a in activities]
    return header + "\n\n".join(sections)
