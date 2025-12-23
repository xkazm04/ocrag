"""Positioning utilities for the Detective Board.

Helper functions for calculating elliptical actor positions
and bezier curve connection paths.
"""
import math
from typing import List, Optional


def generate_position_slots(
    radius_x: float,
    radius_y: float,
    count: int,
    ring: int
) -> List[dict]:
    """Generate position slots on an elliptical ring.

    Args:
        radius_x: Horizontal radius of the ellipse
        radius_y: Vertical radius of the ellipse
        count: Number of slots to generate
        ring: Ring number (1=inner, 2=outer)

    Returns:
        List of slot dicts with angle, priority, ring, radius info
    """
    slots = []
    for i in range(count):
        angle = (math.pi * 2 * i) / count - math.pi / 2
        normalized_angle = (angle + math.pi * 2) % (math.pi * 2)

        # Priority: top > sides > bottom
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


def calculate_actor_positions(
    visible_actors: List[dict],
    center_x: float,
    center_y: float,
    board_width: int = 2000,
    board_height: int = 900,
) -> List[dict]:
    """Calculate elliptical positions for visible actors.

    Args:
        visible_actors: List of actor dicts
        center_x: Center X coordinate
        center_y: Center Y coordinate
        board_width: Board width in pixels
        board_height: Board height in pixels

    Returns:
        List of position dicts with actor_id, x, y, angle, ring
    """
    positions = []

    # Exclude primary actor from positioning (goes to center)
    actors_to_position = [
        a for a in visible_actors
        if not a.get("is_primary", False)
    ]

    # Radii for the rings
    inner_radius_x = 520
    inner_radius_y = 240
    outer_radius_x = 820
    outer_radius_y = 300

    # Generate slots for both rings
    inner_slots = generate_position_slots(inner_radius_x, inner_radius_y, 8, 1)
    outer_slots = generate_position_slots(outer_radius_x, outer_radius_y, 8, 2)
    all_slots = inner_slots + outer_slots

    # Add original index and sort by priority
    for idx, slot in enumerate(all_slots):
        slot["original_index"] = idx
    all_slots.sort(key=lambda s: (s["priority"], s["ring"], s["original_index"]))

    # Assign actors to slots
    for index, actor in enumerate(actors_to_position):
        if index >= len(all_slots):
            break

        slot = all_slots[index]
        x = center_x + math.cos(slot["angle"]) * slot["radius_x"]
        y = center_y + math.sin(slot["angle"]) * slot["radius_y"]

        rotation = ((index % 7) - 3) * 2
        positions.append({
            "actor_id": actor.get("id"),
            "x": x,
            "y": y,
            "angle": slot["angle"],
            "ring": slot["ring"],
            "index": index,
            "label": f"Actor {index + 1}",
            "rotation": rotation,
            "transform": f"rotate({rotation}deg)",
            "hover_transform": f"rotate({rotation - 2}deg) scale(1.05)",
            "is_new": actor.get("is_new", False),
        })

    return positions


def calculate_bezier_control_point(
    x1: float, y1: float,
    x2: float, y2: float,
    offset_factor: float = 0.2,
    max_offset: float = 50
) -> tuple:
    """Calculate bezier curve control point for connection line.

    Args:
        x1, y1: Start point coordinates
        x2, y2: End point coordinates
        offset_factor: Factor for curve offset relative to line length
        max_offset: Maximum offset value

    Returns:
        Tuple of (cx, cy) control point coordinates
    """
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2

    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)

    if length > 0:
        offset = min(max_offset, length * offset_factor)
        nx = -dy / length * offset
        ny = dx / length * offset
    else:
        nx, ny = 0, 0

    return mx + nx, my + ny


def calculate_connection_paths(
    visible_connections: List[dict],
    actor_positions: List[dict],
    primary_actor: Optional[dict],
    center_x: float,
    center_y: float,
) -> List[dict]:
    """Calculate SVG paths for visible connections.

    Args:
        visible_connections: List of connection dicts
        actor_positions: List of position dicts from calculate_actor_positions
        primary_actor: Primary actor dict or None
        center_x: Center X coordinate for primary actor
        center_y: Center Y coordinate for primary actor

    Returns:
        List of path dicts with id, path, type, label, is_new
    """
    paths = []
    actor_pos_map = {p["actor_id"]: p for p in actor_positions}

    # Add primary actor position to map
    if primary_actor:
        actor_pos_map[primary_actor.get("id", "")] = {
            "x": center_x,
            "y": center_y,
        }

    for conn in visible_connections:
        source_id = conn.get("source_id", "")
        target_id = conn.get("target_id", "")

        source_pos = actor_pos_map.get(source_id)
        target_pos = actor_pos_map.get(target_id)

        if not source_pos or not target_pos:
            continue

        x1, y1 = source_pos["x"], source_pos["y"]
        x2, y2 = target_pos["x"], target_pos["y"]

        cx, cy = calculate_bezier_control_point(x1, y1, x2, y2)
        path = f"M {x1} {y1} Q {cx} {cy} {x2} {y2}"

        paths.append({
            "id": conn.get("id"),
            "path": path,
            "type": conn.get("type", "political"),
            "label": conn.get("label", ""),
            "is_new": conn.get("is_new", False),
        })

    return paths
