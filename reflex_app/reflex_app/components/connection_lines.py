"""Connection Lines SVG component.

Renders red thread connections between actors and the suspect hub
using SVG quadratic bezier curves.
"""
import math
import reflex as rx
from ..state import InvestigationState
from ..lib.mock_data import investigation_data


def calculate_path(source: dict, target: dict, index: int, is_primary: bool) -> str:
    """Calculate the SVG path for a curved connection line."""
    source_x = source.get("x", 0)
    source_y = source.get("y", 0)
    target_x = target.get("x", 0)
    target_y = target.get("y", 0)

    # Calculate midpoint
    mid_x = (source_x + target_x) / 2
    mid_y = (source_y + target_y) / 2

    # Calculate direction and distance
    dx = target_x - source_x
    dy = target_y - source_y
    dist = math.sqrt(dx * dx + dy * dy) if (dx != 0 or dy != 0) else 1

    # Curve offset - perpendicular to the line
    curve_multiplier = 0.15  # Red string mode uses larger curves
    curve_offset = min(dist * curve_multiplier, 50 if not is_primary else 30)

    # Perpendicular direction
    perp_x = (-dy / dist) * curve_offset if dist > 0 else 0
    perp_y = (dx / dist) * curve_offset if dist > 0 else 0

    # Alternate curve direction based on index
    curve_direction = 1 if index % 2 == 0 else -1
    ctrl_x = mid_x + perp_x * curve_direction
    ctrl_y = mid_y + perp_y * curve_direction

    return f"M {source_x},{source_y} Q {ctrl_x},{ctrl_y} {target_x},{target_y}"


def _get_static_positions() -> dict:
    """Get pre-calculated static positions for all actors.

    This mirrors the elliptical positioning algorithm in the state.
    """
    positions = {}

    # Suspect position (center)
    center_x = 1000
    center_y = 350
    positions["suspect-1"] = {"x": center_x, "y": center_y}

    # Actor positions - using the same algorithm as investigation_state
    actors = investigation_data.actors
    inner_radius_x = 520
    inner_radius_y = 240
    outer_radius_x = 820
    outer_radius_y = 300

    def generate_slots(radius_x: float, radius_y: float, count: int, ring: int) -> list:
        slots = []
        for i in range(count):
            angle = (math.pi * 2 * i) / count - math.pi / 2
            normalized_angle = (angle + math.pi * 2) % (math.pi * 2)

            if 5 * math.pi / 4 <= normalized_angle <= 7 * math.pi / 4:
                priority = 0
            elif 3 * math.pi / 4 <= normalized_angle < 5 * math.pi / 4:
                priority = 1
            elif (0 <= normalized_angle < math.pi / 4) or normalized_angle > 7 * math.pi / 4:
                priority = 1
            else:
                priority = 2

            slots.append({
                "angle": angle,
                "priority": priority,
                "ring": ring,
                "radius_x": radius_x,
                "radius_y": radius_y,
            })
        return slots

    inner_slots = generate_slots(inner_radius_x, inner_radius_y, 8, 1)
    outer_slots = generate_slots(outer_radius_x, outer_radius_y, 8, 2)

    all_slots = inner_slots + outer_slots
    for idx, slot in enumerate(all_slots):
        slot["original_index"] = idx

    all_slots.sort(key=lambda s: (s["priority"], s["ring"], s["original_index"]))

    manual_overrides = {
        "actor-4": {"angle_offset": -0.5, "radius_multiplier": 0.95},
        "actor-1": {"angle_offset": 0.4, "radius_multiplier": 0.95},
    }

    for index, actor in enumerate(actors):
        if index >= len(all_slots):
            break

        slot = all_slots[index]
        override = manual_overrides.get(actor.id, {})

        radius_x = slot["radius_x"]
        radius_y = slot["radius_y"]
        angle = slot["angle"]

        if "angle_offset" in override:
            angle += override["angle_offset"]
        if "radius_multiplier" in override:
            radius_x *= override["radius_multiplier"]
            radius_y *= override["radius_multiplier"]

        x = center_x + math.cos(angle) * radius_x
        y = center_y + math.sin(angle) * radius_y

        positions[actor.id] = {"x": x, "y": y}

    return positions


def build_all_connection_paths() -> list:
    """Build all connection paths with their SVG path strings.

    Returns a list of dicts containing connection info and pre-calculated path.
    """
    positions = _get_static_positions()
    paths = []

    for idx, conn in enumerate(investigation_data.connections):
        source_pos = positions.get(conn.source_id, {"x": 1000, "y": 350})
        target_pos = positions.get(conn.target_id, {"x": 1000, "y": 350})
        is_primary = conn.source_id == "suspect-1" or conn.target_id == "suspect-1"

        path = calculate_path(source_pos, target_pos, idx, is_primary)

        paths.append({
            "id": conn.id,
            "path": path,
            "is_primary": is_primary,
            "is_confirmed": conn.is_confirmed,
            "source_id": conn.source_id,
            "target_id": conn.target_id,
            "type": conn.type,
            "label": conn.label,
        })

    return paths


# Pre-calculate paths at module load time
_CONNECTION_PATHS = build_all_connection_paths()


def connection_lines_static() -> rx.Component:
    """Render static connection lines with pre-calculated paths."""
    primary_paths = [p for p in _CONNECTION_PATHS if p["is_primary"]]
    secondary_paths = [p for p in _CONNECTION_PATHS if not p["is_primary"]]

    return rx.el.svg(
        # Secondary connections (behind) - thinner, more transparent
        *[
            rx.el.path(
                d=p["path"],
                stroke="#dc2626",
                stroke_width="1",
                stroke_opacity="0.4",
                stroke_dasharray="none" if p["is_confirmed"] else "8 4",
                stroke_linecap="round",
                fill="none",
                key=p["id"],
            )
            for p in secondary_paths
        ],
        # Primary connections - glow effect (thicker, more transparent behind)
        *[
            rx.el.path(
                d=p["path"],
                stroke="#dc2626",
                stroke_width="6",
                stroke_opacity="0.15",
                stroke_linecap="round",
                fill="none",
                key=f"{p['id']}-glow",
            )
            for p in primary_paths
        ],
        # Primary connections - main line (on top)
        *[
            rx.el.path(
                d=p["path"],
                stroke="#dc2626",
                stroke_width="2",
                stroke_opacity="0.8",
                stroke_dasharray="none" if p["is_confirmed"] else "8 4",
                stroke_linecap="round",
                fill="none",
                key=p["id"],
            )
            for p in primary_paths
        ],
        position="absolute",
        inset="0",
        width="100%",
        height="100%",
        style={"z_index": "1", "pointer_events": "none"},
        overflow="visible",
    )
