"""
Wall Coverage Planner Module

Implements a boustrophedon (lawnmower-style) coverage algorithm for
autonomous wall-finishing robots. Includes obstacle preprocessing,
lane generation, interval subtraction, waypoint construction, and
basic coverage metrics.

Author: Siddhant Gond 
"""

from math import atan2, sqrt
from typing import List, Dict, Tuple, Optional


# ---------------------------------------------------------------------
# Data Types (Dict-based to stay lightweight)
# ---------------------------------------------------------------------

Rect = Dict[str, float]
Point = Dict[str, float]
Segment = Dict[str, object]    # lane_idx, start, end
PlaneInterval = Tuple[float, float]


# ---------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------

def inflate_rect(rect: Rect, margin: float) -> Rect:
    """
    Inflate a rectangle by a given margin on all sides.
    """
    return {
        "x": rect["x"] - margin,
        "y": rect["y"] - margin,
        "w": rect["w"] + 2 * margin,
        "h": rect["h"] + 2 * margin
    }


def clip_rect_to_wall(rect: Rect, wall_w: float, wall_h: float) -> Optional[Rect]:
    """
    Clips a rectangle to the wall boundaries.
    Returns None if the rectangle falls fully outside the wall.
    """
    x = max(0.0, rect["x"])
    y = max(0.0, rect["y"])
    w = min(wall_w - x, rect["w"])
    h = min(wall_h - y, rect["h"])

    if w <= 0 or h <= 0:
        return None

    return {"x": x, "y": y, "w": w, "h": h}


def rects_overlap(a: Rect, b: Rect) -> bool:
    """
    Check if two rectangles overlap.
    """
    if a["x"] + a["w"] < b["x"]:
        return False
    if b["x"] + b["w"] < a["x"]:
        return False
    if a["y"] + a["h"] < b["y"]:
        return False
    if b["y"] + b["h"] < a["y"]:
        return False

    return True


def merge_rectangles(rects: List[Rect]) -> List[Rect]:
    """
    Merge overlapping axis-aligned rectangles.
    Simple O(N^2) merging (fine for <= 100 obstacles).
    """
    merged = rects[:]
    changed = True

    while changed:
        changed = False
        new_list = []
        while merged:
            rect = merged.pop()
            merged_any = False

            for i, existing in enumerate(merged):
                if rects_overlap(rect, existing):
                    # Merge the two rectangles
                    x = min(rect["x"], existing["x"])
                    y = min(rect["y"], existing["y"])
                    w = max(rect["x"] + rect["w"], existing["x"] + existing["w"]) - x
                    h = max(rect["y"] + rect["h"], existing["y"] + existing["h"]) - y

                    merged.pop(i)
                    merged.append({"x": x, "y": y, "w": w, "h": h})
                    merged_any = True
                    changed = True
                    break

            if not merged_any:
                new_list.append(rect)

        merged = new_list

    return merged


# ---------------------------------------------------------------------
# Interval helpers
# ---------------------------------------------------------------------

def merge_intervals(intervals: List[PlaneInterval]) -> List[PlaneInterval]:
    """
    Merge overlapping intervals on a line.
    """
    if not intervals:
        return []

    intervals.sort(key=lambda it: it[0])
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def subtract_intervals(full: PlaneInterval, blocks: List[PlaneInterval]) -> List[PlaneInterval]:
    """
    Subtract a set of blocked intervals from a full interval.
    Return list of free intervals.
    """
    free = []
    cursor = full[0]

    for start, end in blocks:
        if start > cursor:
            free.append((cursor, min(start, full[1])))
        cursor = max(cursor, end)

    if cursor < full[1]:
        free.append((cursor, full[1]))

    return free


# ---------------------------------------------------------------------
# Waypoint helpers
# ---------------------------------------------------------------------

def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    """
    Euclidean distance between two points.
    """
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def discretize_segment(
    start: Tuple[float, float],
    end: Tuple[float, float],
    spacing: float
) -> List[Tuple[float, float]]:
    """
    Produce intermediate points along a segment including endpoints.
    """
    x0, y0 = start
    x1, y1 = end
    seg_len = distance(start, end)

    if seg_len < spacing:
        return [start, end]

    num_points = int(seg_len / spacing)
    pts = []
    for i in range(num_points + 1):
        t = i / num_points
        x = x0 * (1 - t) + x1 * t
        y = y0 * (1 - t) + y1 * t
        pts.append((x, y))

    if pts[-1] != end:
        pts.append(end)

    return pts


def connect_points(
    a: Tuple[float, float],
    b: Tuple[float, float],
    spacing: float
) -> List[Point]:
    """
    Straight-line connection between two points.
    """
    pts = discretize_segment(a, b, spacing)
    return [{"x": p[0], "y": p[1], "theta": 0.0} for p in pts]


def point_in_rect(pt: Point, rect: Rect) -> bool:
    """
    Check if a waypoint lies inside a forbidden rectangle.
    """
    return (
        rect["x"] <= pt["x"] <= rect["x"] + rect["w"]
        and rect["y"] <= pt["y"] <= rect["y"] + rect["h"]
    )


def compute_path_length(waypoints: List[Point]) -> float:
    """
    Sum of Euclidean distances over consecutive waypoints.
    """
    total = 0.0
    for i in range(len(waypoints) - 1):
        a = (waypoints[i]["x"], waypoints[i]["y"])
        b = (waypoints[i + 1]["x"], waypoints[i + 1]["y"])
        total += distance(a, b)
    return total


def estimate_coverage_fraction(
    wall_w: float,
    wall_h: float,
    tool_w: float,
    overlap: float,
    lanes: List[Dict[str, float]],
    forbidden: List[Rect]
) -> float:
    """
    Approximate coverage fraction using swept lane area minus forbidden regions.
    """
    lane_spacing = tool_w * (1 - overlap)
    total_area = wall_w * wall_h

    forbidden_area = sum(r["w"] * r["h"] for r in forbidden)

    swept_area = len(lanes) * lane_spacing * (wall_h if lanes[0]["orientation"] == "vertical" else wall_w)
    swept_area = min(swept_area, total_area - forbidden_area)

    return swept_area / max(total_area, 1e-9)


# ---------------------------------------------------------------------
# Obstacle pipeline
# ---------------------------------------------------------------------

def process_obstacles(
    obstacles: List[Rect],
    safe_margin: float,
    wall_w: float,
    wall_h: float
) -> List[Rect]:
    """
    Inflate → clip → merge → clean.
    """
    inflated = [inflate_rect(o, safe_margin) for o in obstacles]

    clipped = []
    for r in inflated:
        c = clip_rect_to_wall(r, wall_w, wall_h)
        if c:
            clipped.append(c)

    merged = merge_rectangles(clipped)
    return merged


# ---------------------------------------------------------------------
# Main planner
# ---------------------------------------------------------------------

def plan_coverage(
    wall_w: float,
    wall_h: float,
    obstacles: List[Rect],
    tool_w: float,
    overlap: float,
    safe_margin: float,
    waypoint_spacing: Optional[float] = None,
    orientation: str = "auto",
    min_segment_length: Optional[float] = None,
    speed: Optional[float] = None
) -> Dict[str, object]:
    """
    Coverage path planning using a boustrophedon sweep.
    """
    # Defaults
    if waypoint_spacing is None:
        waypoint_spacing = tool_w / 2.0
    if min_segment_length is None:
        min_segment_length = max(0.25 * tool_w, 0.05)

    # 1) Preprocess obstacles
    forbidden = process_obstacles(obstacles, safe_margin, wall_w, wall_h)

    # 2) Lane spacing
    lane_spacing = tool_w * (1 - overlap)
    if lane_spacing <= 0:
        raise ValueError("Invalid overlap -> lane spacing <= 0")

    # 3) Orientation
    if orientation == "auto":
        orientation = "vertical" if wall_h > wall_w else "horizontal"

    # 4) Generate lanes
    lanes = []
    half = lane_spacing / 2.0

    if orientation == "vertical":
        x = half
        while x <= wall_w - half + 1e-9:
            lanes.append({"orientation": "vertical", "coord": x})
            x += lane_spacing
    else:
        y = half
        while y <= wall_h - half + 1e-9:
            lanes.append({"orientation": "horizontal", "coord": y})
            y += lane_spacing

    # 5) Project forbidden → blocked intervals → subtract
    lanes_segments = []

    for i, lane in enumerate(lanes):
        if lane["orientation"] == "vertical":
            X = lane["coord"]
            full = (0.0, wall_h)

            blocked = [
                (r["y"], r["y"] + r["h"])
                for r in forbidden
                if r["x"] <= X <= r["x"] + r["w"]
            ]

            merged_b = merge_intervals(blocked)
            free_intervals = subtract_intervals(full, merged_b)
            free_intervals = [
                iv for iv in free_intervals
                if iv[1] - iv[0] >= min_segment_length
            ]

            segments = [
                {"lane_idx": i, "start": (X, iv[0]), "end": (X, iv[1])}
                for iv in free_intervals
            ]
            lanes_segments.append(segments)

        else:
            Y = lane["coord"]
            full = (0.0, wall_w)

            blocked = [
                (r["x"], r["x"] + r["w"])
                for r in forbidden
                if r["y"] <= Y <= r["y"] + r["h"]
            ]

            merged_b = merge_intervals(blocked)
            free_intervals = subtract_intervals(full, merged_b)
            free_intervals = [
                iv for iv in free_intervals
                if iv[1] - iv[0] >= min_segment_length
            ]

            segments = [
                {"lane_idx": i, "start": (iv[0], Y), "end": (iv[1], Y)}
                for iv in free_intervals
            ]
            lanes_segments.append(segments)

    # 6) Boustrophedon ordering
    ordered_segments = []
    direction_up = True

    for segs in lanes_segments:
        if not segs:
            direction_up = not direction_up
            continue

        if orientation == "vertical":
            segs.sort(key=lambda s: s["start"][1])
        else:
            segs.sort(key=lambda s: s["start"][0])

        if not direction_up:
            segs.reverse()

        ordered_segments.extend(segs)
        direction_up = not direction_up

    # 7) Discretization + transitions
    waypoints: List[Point] = []
    prev = None

    for seg in ordered_segments:
        p0 = seg["start"]
        p1 = seg["end"]

        pts = discretize_segment(p0, p1, waypoint_spacing)

        if prev is not None:
            if distance(prev, pts[0]) > 1e-6:
                waypoints.extend(connect_points(prev, pts[0], waypoint_spacing))

        for x, y in pts:
            waypoints.append({"x": x, "y": y, "theta": 0.0})

        prev = pts[-1]

    # 8) Heading angles
    for i in range(len(waypoints) - 1):
        dx = waypoints[i + 1]["x"] - waypoints[i]["x"]
        dy = waypoints[i + 1]["y"] - waypoints[i]["y"]
        waypoints[i]["theta"] = atan2(dy, dx)

    if len(waypoints) >= 2:
        waypoints[-1]["theta"] = waypoints[-2]["theta"]

    # 9) Collision check
    collisions = []
    for pt in waypoints:
        for rect in forbidden:
            if point_in_rect(pt, rect):
                collisions.append((pt, rect))

    # 10) Metrics
    path_length = compute_path_length(waypoints)
    coverage = estimate_coverage_fraction(
        wall_w, wall_h, tool_w, overlap, lanes, forbidden
    )

    return {
        "waypoints": waypoints,
        "meta": {
            "path_length": path_length,
            "coverage_fraction": coverage,
            "num_waypoints": len(waypoints),
            "collision_flag": len(collisions) > 0,
            "validation_warnings": [f"Collision detected at {c[0]}" for c in collisions] if collisions else []
        },
        "forbidden_rects": forbidden,
        "lanes": lanes
    }
