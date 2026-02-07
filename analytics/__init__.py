from __future__ import annotations

from datetime import datetime, timedelta
from math import sqrt
from typing import Any

from flask import Blueprint, jsonify, render_template, request
from sqlalchemy import func, or_

from models import (
    Athlete,
    Image,
    Jacket,
    Rifle,
    Scope,
    Session,
    Shot,
    Series,
    CompetitionAthlete,
    db,
)


analytics_bp = Blueprint("analytics", __name__, template_folder="templates", static_folder="static")


def _parse_csv_ints(value: str | None) -> list[int]:
    if not value:
        return []
    out = []
    for raw in value.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(int(raw))
        except ValueError:
            continue
    return out


def _parse_csv_strings(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _parse_bool(value: str | None) -> bool:
    if not value:
        return False
    return value.lower() in ("1", "true", "yes", "on")


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return sqrt(var)


def _slope(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if den == 0:
        return 0.0
    return num / den


def _score_expr():
    return func.coalesce(Shot.final_score, Shot.auto_score, 0)


def _apply_filters(query, filters: dict[str, Any]):
    start = filters.get("start")
    end = filters.get("end")
    athlete_ids = filters.get("athlete_ids") or []
    team_names = filters.get("teams") or []
    rifle_ids = filters.get("rifle_ids") or []
    jacket_ids = filters.get("jacket_ids") or []
    scope_ids = filters.get("scope_ids") or []
    modes = filters.get("modes") or []
    include_unassigned = filters.get("include_unassigned", False)

    if start:
        query = query.filter(Image.created_at >= start)
    if end:
        query = query.filter(Image.created_at < end)
    if modes:
        query = query.filter(Session.mode.in_(modes))

    if athlete_ids:
        if include_unassigned:
            query = query.filter(or_(Image.athlete_id.in_(athlete_ids), Image.athlete_id.is_(None)))
        else:
            query = query.filter(Image.athlete_id.in_(athlete_ids))

    if team_names:
        team_filter = Athlete.team.in_(team_names)
        if include_unassigned or "Unassigned" in team_names:
            team_filter = or_(team_filter, Athlete.team.is_(None))
        query = query.filter(team_filter)

    if rifle_ids:
        rifle_filter = Athlete.rifle_id.in_(rifle_ids)
        if include_unassigned:
            rifle_filter = or_(rifle_filter, Athlete.rifle_id.is_(None))
        query = query.filter(rifle_filter)

    if jacket_ids:
        jacket_filter = Athlete.jacket_id.in_(jacket_ids)
        if include_unassigned:
            jacket_filter = or_(jacket_filter, Athlete.jacket_id.is_(None))
        query = query.filter(jacket_filter)

    if scope_ids:
        scope_filter = Rifle.scope_id.in_(scope_ids)
        if include_unassigned:
            scope_filter = or_(scope_filter, Rifle.scope_id.is_(None))
        query = query.filter(scope_filter)

    return query


@analytics_bp.route("/")
def index():
    return render_template("analytics/index.html")


@analytics_bp.route("/filters")
def filters():
    athletes = Athlete.query.order_by(Athlete.first_name, Athlete.last_name).all()
    rifles = Rifle.query.order_by(Rifle.name).all()
    jackets = Jacket.query.order_by(Jacket.name).all()
    scopes = Scope.query.order_by(Scope.name).all()

    teams = sorted({a.team for a in athletes if a.team})

    min_date = db.session.query(func.min(Image.created_at)).scalar()
    max_date = db.session.query(func.max(Image.created_at)).scalar()

    modes = [m[0] for m in db.session.query(Session.mode).distinct().all()]
    modes = sorted([m for m in modes if m])

    return jsonify(
        {
            "athletes": [
                {
                    "id": a.id,
                    "name": f"{a.first_name} {a.last_name or ''}".strip(),
                    "team": a.team,
                    "rifle_id": a.rifle_id,
                    "jacket_id": a.jacket_id,
                    "scope_id": a.rifle.scope_id if a.rifle else None,
                }
                for a in athletes
            ],
            "teams": teams,
            "rifles": [{"id": r.id, "name": r.name} for r in rifles],
            "jackets": [{"id": j.id, "name": j.name} for j in jackets],
            "scopes": [{"id": s.id, "name": s.name} for s in scopes],
            "modes": modes or ["training", "competition"],
            "date_range": {
                "min": min_date.date().isoformat() if min_date else None,
                "max": max_date.date().isoformat() if max_date else None,
            },
        }
    )


@analytics_bp.route("/data")
def data():
    filters = {
        "start": _parse_date(request.args.get("start")),
        "end": _parse_date(request.args.get("end")),
        "athlete_ids": _parse_csv_ints(request.args.get("athlete_ids")),
        "teams": _parse_csv_strings(request.args.get("teams")),
        "rifle_ids": _parse_csv_ints(request.args.get("rifle_ids")),
        "jacket_ids": _parse_csv_ints(request.args.get("jacket_ids")),
        "scope_ids": _parse_csv_ints(request.args.get("scope_ids")),
        "modes": _parse_csv_strings(request.args.get("modes")),
        "include_unassigned": _parse_bool(request.args.get("include_unassigned")),
    }

    if filters["end"]:
        filters["end"] = filters["end"] + timedelta(days=1)

    score_expr = _score_expr()

    attempts_q = (
        db.session.query(
            Image.id.label("image_id"),
            Image.created_at.label("created_at"),
            Session.id.label("session_id"),
            Session.name.label("session_name"),
            Session.mode.label("mode"),
            Image.athlete_id.label("athlete_id"),
            Athlete.first_name.label("first_name"),
            Athlete.last_name.label("last_name"),
            Athlete.team.label("team"),
            Athlete.rifle_id.label("rifle_id"),
            Athlete.jacket_id.label("jacket_id"),
            Rifle.scope_id.label("scope_id"),
            func.sum(score_expr).label("total_score"),
            func.count(Shot.id).label("shots_count"),
        )
        .join(Session, Image.session_id == Session.id)
        .outerjoin(Athlete, Image.athlete_id == Athlete.id)
        .outerjoin(Rifle, Athlete.rifle_id == Rifle.id)
        .outerjoin(Shot, Shot.image_id == Image.id)
        .group_by(Image.id)
    )

    attempts_q = _apply_filters(attempts_q, filters)
    attempts_rows = attempts_q.all()

    attempts = []
    for row in attempts_rows:
        name = None
        if row.first_name:
            name = f"{row.first_name} {row.last_name or ''}".strip()
        attempts.append(
            {
                "image_id": row.image_id,
                "created_at": row.created_at,
                "session_id": row.session_id,
                "session_name": row.session_name,
                "mode": row.mode,
                "athlete_id": row.athlete_id,
                "athlete_name": name,
                "team": row.team,
                "rifle_id": row.rifle_id,
                "jacket_id": row.jacket_id,
                "scope_id": row.scope_id,
                "total_score": float(row.total_score or 0),
                "shots_count": int(row.shots_count or 0),
            }
        )

    scores = [a["total_score"] for a in attempts if a["total_score"] is not None]
    shots_total = sum(a["shots_count"] for a in attempts)
    avg_score = sum(scores) / len(scores) if scores else 0.0
    min_score = min(scores) if scores else 0.0
    max_score = max(scores) if scores else 0.0
    std_score = _stddev(scores) if scores else 0.0
    avg_shot_score = (sum(scores) / shots_total) if shots_total else 0.0

    training_scores = [a["total_score"] for a in attempts if a["mode"] == "training"]
    competition_scores = [a["total_score"] for a in attempts if a["mode"] == "competition"]
    standard_scores = [a["total_score"] for a in attempts if a["mode"] == "standard"]

    training_avg = sum(training_scores) / len(training_scores) if training_scores else 0.0
    competition_avg = sum(competition_scores) / len(competition_scores) if competition_scores else 0.0
    standard_avg = sum(standard_scores) / len(standard_scores) if standard_scores else 0.0

    training_delta = competition_avg - training_avg

    # Timeseries data by athlete
    series_by_athlete: dict[str, dict[str, Any]] = {}
    overall_series = []
    best_point = None
    worst_point = None

    for attempt in attempts:
        created = attempt["created_at"]
        if not created:
            continue
        ts = int(created.timestamp() * 1000)
        overall_series.append([ts, attempt["total_score"]])

        athlete_id = attempt["athlete_id"]
        athlete_key = str(athlete_id) if athlete_id is not None else "unassigned"
        athlete_name = attempt["athlete_name"] or "Unassigned"
        series = series_by_athlete.setdefault(
            athlete_key, {"id": athlete_key, "name": athlete_name, "data": []}
        )
        series["data"].append([ts, attempt["total_score"]])

        if best_point is None or attempt["total_score"] > best_point["y"]:
            best_point = {
                "x": ts,
                "y": attempt["total_score"],
                "label": f"Best {attempt['total_score']:.0f} ({athlete_name})",
            }
        if worst_point is None or attempt["total_score"] < worst_point["y"]:
            worst_point = {
                "x": ts,
                "y": attempt["total_score"],
                "label": f"Low {attempt['total_score']:.0f} ({athlete_name})",
            }

    for series in series_by_athlete.values():
        series["data"].sort(key=lambda p: p[0])
    overall_series.sort(key=lambda p: p[0])

    # Athlete stats for comparison + consistency
    athlete_stats: dict[str, dict[str, Any]] = {}
    for attempt in attempts:
        athlete_id = attempt["athlete_id"]
        key = str(athlete_id) if athlete_id is not None else "unassigned"
        stat = athlete_stats.setdefault(
            key,
            {
                "id": key,
                "name": attempt["athlete_name"] or "Unassigned",
                "scores": [],
                "training": [],
                "competition": [],
                "standard": [],
                "team": attempt["team"] or "Unassigned",
            },
        )
        stat["scores"].append(attempt["total_score"])
        if attempt["mode"] == "training":
            stat["training"].append(attempt["total_score"])
        elif attempt["mode"] == "competition":
            stat["competition"].append(attempt["total_score"])
        elif attempt["mode"] == "standard":
            stat["standard"].append(attempt["total_score"])

    comparison_rows = []
    for stat in athlete_stats.values():
        training_avg_a = sum(stat["training"]) / len(stat["training"]) if stat["training"] else 0.0
        competition_avg_a = (
            sum(stat["competition"]) / len(stat["competition"]) if stat["competition"] else 0.0
        )
        standard_avg_a = sum(stat["standard"]) / len(stat["standard"]) if stat["standard"] else 0.0
        scores_a = stat["scores"]
        overall_avg_a = sum(scores_a) / len(scores_a) if scores_a else 0.0
        std_a = _stddev(scores_a)
        comparison_rows.append(
            {
                "id": stat["id"],
                "name": stat["name"],
                "team": stat["team"],
                "training_avg": training_avg_a,
                "competition_avg": competition_avg_a,
                "standard_avg": standard_avg_a,
                "overall_avg": overall_avg_a,
                "delta": competition_avg_a - training_avg_a,
                "min": min(scores_a) if scores_a else 0.0,
                "max": max(scores_a) if scores_a else 0.0,
                "stddev": std_a,
                "attempts": len(scores_a),
            }
        )

    comparison_rows.sort(key=lambda r: r["overall_avg"], reverse=True)

    # Trend calculation
    trends = []
    for key, series in series_by_athlete.items():
        points = [(p[0] / 86400000.0, p[1]) for p in series["data"]]
        slope = _slope(points)
        direction = "up" if slope > 0 else "down" if slope < 0 else "flat"
        trends.append(
            {
                "id": key,
                "name": series["name"],
                "slope": slope,
                "direction": direction,
            }
        )

    # Team aggregations + drilldown
    team_stats: dict[str, dict[str, Any]] = {}
    for row in comparison_rows:
        team = row["team"] or "Unassigned"
        team_stat = team_stats.setdefault(team, {"scores": [], "athletes": []})
        team_stat["scores"].append(row["overall_avg"] or 0.0)
        team_stat["athletes"].append([row["name"], row["overall_avg"] or 0.0])

    team_categories = []
    team_series_data = []
    drilldown = []
    for team, stat in team_stats.items():
        avg = sum(stat["scores"]) / len(stat["scores"]) if stat["scores"] else 0.0
        team_categories.append(team)
        team_series_data.append(round(avg, 2))
        drilldown.append({"id": team, "name": f"{team} athletes", "data": stat["athletes"]})

    # Shot distribution (scatter + heatmap)
    shots_q = (
        db.session.query(
            Shot.dist_mm.label("dist_mm"),
            Shot.shot_index.label("shot_index"),
            score_expr.label("score"),
            Image.created_at.label("created_at"),
            Session.mode.label("mode"),
            Athlete.first_name.label("first_name"),
            Athlete.last_name.label("last_name"),
        )
        .join(Image, Shot.image_id == Image.id)
        .join(Session, Image.session_id == Session.id)
        .outerjoin(Athlete, Image.athlete_id == Athlete.id)
        .outerjoin(Rifle, Athlete.rifle_id == Rifle.id)
    )
    shots_q = _apply_filters(shots_q, filters)
    shot_rows = shots_q.all()

    scatter_points = []
    max_index = 0
    score_set = set()
    heat_counts: dict[tuple[int, int], int] = {}

    for row in shot_rows:
        score = int(row.score or 0)
        dist = float(row.dist_mm or 0)
        idx = int(row.shot_index or 0)
        if idx > max_index:
            max_index = idx
        score_set.add(score)
        heat_counts[(idx, score)] = heat_counts.get((idx, score), 0) + 1

        athlete_name = (
            f"{row.first_name} {row.last_name or ''}".strip() if row.first_name else "Unassigned"
        )
        scatter_points.append(
            {
                "x": score,
                "y": dist,
                "athlete": athlete_name,
                "mode": row.mode,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )

    score_categories = list(range(10, -1, -1))
    index_categories = list(range(1, max_index + 1)) if max_index else [1]

    heatmap_data = []
    for x_idx, shot_idx in enumerate(index_categories):
        for y_idx, score in enumerate(score_categories):
            count = heat_counts.get((shot_idx, score), 0)
            heatmap_data.append([x_idx, y_idx, count])

    # Series analysis (competition series)
    series_q = (
        db.session.query(
            Series.id.label("series_id"),
            Series.series_number.label("series_number"),
            Series.created_at.label("created_at"),
            CompetitionAthlete.athlete_id.label("athlete_id"),
            Athlete.team.label("team"),
            func.sum(score_expr).label("total_score"),
            func.count(Shot.id).label("shots_count"),
        )
        .join(Image, Image.series_id == Series.id)
        .join(Shot, Shot.image_id == Image.id)
        .join(CompetitionAthlete, Series.competition_athlete_id == CompetitionAthlete.id)
        .join(Athlete, CompetitionAthlete.athlete_id == Athlete.id)
        .outerjoin(Rifle, Athlete.rifle_id == Rifle.id)
        .group_by(Series.id)
    )

    series_q = _apply_filters(series_q, filters)
    series_rows = series_q.all()

    series_bucket: dict[int, list[float]] = {}
    for row in series_rows:
        series_bucket.setdefault(row.series_number, []).append(float(row.total_score or 0))

    series_categories = []
    series_avg = []
    series_min = []
    series_max = []
    for series_number in sorted(series_bucket.keys()):
        vals = series_bucket[series_number]
        series_categories.append(f"Series {series_number}")
        series_avg.append(sum(vals) / len(vals))
        series_min.append(min(vals))
        series_max.append(max(vals))

    # Consistency (standard deviation normalized)
    consistency_items = []
    for row in comparison_rows[:6]:
        stddev = row["stddev"]
        score_range = max(row["max"] - row["min"], 1.0)
        consistency_index = max(0.0, 100.0 - (stddev / score_range) * 100.0)
        consistency_items.append(
            {
                "id": row["id"],
                "name": row["name"],
                "avg": row["overall_avg"] or 0.0,
                "stddev": stddev,
                "index": round(consistency_index, 1),
            }
        )

    overall_range = max(max_score - min_score, 1.0)
    overall_index = max(0.0, 100.0 - (std_score / overall_range) * 100.0)

    # Sparklines from attempts grouped by session
    session_map: dict[int, dict[str, Any]] = {}
    for attempt in attempts:
        sid = attempt["session_id"]
        if not sid:
            continue
        entry = session_map.setdefault(
            sid,
            {
                "session_id": sid,
                "name": attempt["session_name"] or f"Session {sid}",
                "mode": attempt["mode"] or "training",
                "data": [],
                "last_at": attempt["created_at"],
            },
        )
        entry["data"].append(
            {
                "t": attempt["created_at"],
                "score": attempt["total_score"],
            }
        )
        if attempt["created_at"] and (
            entry["last_at"] is None or attempt["created_at"] > entry["last_at"]
        ):
            entry["last_at"] = attempt["created_at"]

    sparklines = []
    for entry in session_map.values():
        entry["data"].sort(key=lambda d: d["t"] or datetime.min)
        sparklines.append(
            {
                "session_id": entry["session_id"],
                "name": entry["name"],
                "mode": entry["mode"],
                "updated_at": entry["last_at"].isoformat() if entry["last_at"] else None,
                "data": [d["score"] for d in entry["data"]],
            }
        )
    sparklines.sort(key=lambda s: s["updated_at"] or "", reverse=True)
    sparklines = sparklines[:12]

    response = {
        "filters": {
            "start": request.args.get("start"),
            "end": request.args.get("end"),
            "athlete_ids": filters["athlete_ids"],
            "teams": filters["teams"],
            "rifle_ids": filters["rifle_ids"],
            "jacket_ids": filters["jacket_ids"],
            "scope_ids": filters["scope_ids"],
            "modes": filters["modes"],
            "include_unassigned": filters["include_unassigned"],
        },
        "summary": {
            "attempts": len(attempts),
            "shots": shots_total,
            "avg_score": round(avg_score, 2),
            "avg_shot_score": round(avg_shot_score, 2),
            "min_score": round(min_score, 2),
            "max_score": round(max_score, 2),
            "stddev": round(std_score, 2),
        },
        "training_vs_competition": {
            "training_avg": round(training_avg, 2),
            "competition_avg": round(competition_avg, 2),
            "standard_avg": round(standard_avg, 2),
            "delta": round(training_delta, 2),
        },
        "time_series": {
            "series": list(series_by_athlete.values()),
            "overall": overall_series,
            "best_point": best_point,
            "worst_point": worst_point,
        },
        "comparison": {
            "categories": [r["name"] for r in comparison_rows],
            "series": [
                {"name": "Training Avg", "data": [round(r["training_avg"], 2) for r in comparison_rows]},
                {"name": "Competition Avg", "data": [round(r["competition_avg"], 2) for r in comparison_rows]},
                {"name": "Standard Avg", "data": [round(r["standard_avg"], 2) for r in comparison_rows]},
                {
                    "name": "Delta (Comp - Train)",
                    "type": "spline",
                    "yAxis": 1,
                    "data": [round(r["delta"], 2) for r in comparison_rows],
                },
            ],
            "table": comparison_rows,
            "trends": trends,
        },
        "team": {
            "categories": team_categories,
            "series": [{"name": "Avg Score", "data": team_series_data}],
            "drilldown": drilldown,
        },
        "distribution": {
            "scatter": scatter_points,
            "heatmap": {
                "xCategories": [str(x) for x in index_categories],
                "yCategories": [str(y) for y in score_categories],
                "data": heatmap_data,
            },
        },
        "series_analysis": {
            "categories": series_categories,
            "avg": [round(v, 2) for v in series_avg],
            "min": [round(v, 2) for v in series_min],
            "max": [round(v, 2) for v in series_max],
        },
        "consistency": {
            "overall": {
                "index": round(overall_index, 1),
                "stddev": round(std_score, 2),
                "avg": round(avg_score, 2),
            },
            "items": consistency_items,
        },
        "sparklines": sparklines,
    }

    return jsonify(response)
