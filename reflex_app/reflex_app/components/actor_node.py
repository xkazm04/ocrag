"""Actor Node component.

Displays individual actors on the investigation board
with Polaroid-style cards for the Red String theme.
Uses static rendering with pre-calculated positions.
"""
import math
import reflex as rx
from ..state import InvestigationState
from ..lib.mock_data import investigation_data


def _get_static_positions() -> dict:
    """Get pre-calculated static positions for all actors."""
    positions = {}
    center_x = 1000
    center_y = 350

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

        positions[actor.id] = {"x": x, "y": y, "index": index}

    return positions


def _get_initials(name: str) -> str:
    """Get initials from a name."""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[:2].upper() if name else "??"


def _build_actor_data() -> list:
    """Build static actor data with positions."""
    positions = _get_static_positions()
    actors_data = []

    for actor in investigation_data.actors:
        pos = positions.get(actor.id, {"x": 1000, "y": 350, "index": 0})
        actors_data.append({
            "id": actor.id,
            "name": actor.name,
            "initials": _get_initials(actor.name),
            "risk_level": actor.risk_level,
            "x": pos["x"],
            "y": pos["y"],
            "index": pos["index"],
            "rotation": ((pos["index"] % 7) - 3) * 2,
        })

    return actors_data


# Pre-calculate at module load time
_ACTOR_DATA = _build_actor_data()


def actors_layer_static() -> rx.Component:
    """Render all actor nodes with static pre-calculated data."""
    return rx.fragment(
        *[
            polaroid_card_static(actor)
            for actor in _ACTOR_DATA
        ]
    )


def polaroid_card_static(actor: dict) -> rx.Component:
    """Render a polaroid-style actor card with static data."""
    actor_id = actor["id"]
    name = actor["name"]
    initials = actor["initials"]
    risk_level = actor["risk_level"]
    x = actor["x"]
    y = actor["y"]
    rotation = actor["rotation"]

    # Map risk level to pushpin class
    pushpin_classes = {
        "critical": "pushpin pushpin-critical",
        "high": "pushpin pushpin-high",
        "medium": "pushpin pushpin-medium",
        "low": "pushpin pushpin-low",
        "minimal": "pushpin pushpin-minimal",
    }
    pushpin_class = pushpin_classes.get(risk_level, "pushpin pushpin-minimal")

    return rx.box(
        rx.box(
            # Pushpin at top
            rx.box(class_name=pushpin_class),
            # Tape corners
            rx.box(
                position="absolute",
                top="-8px",
                left="-4px",
                width="32px",
                height="12px",
                background="rgba(251, 191, 36, 0.6)",
                transform="rotate(-15deg)",
                border_radius="2px",
            ),
            rx.box(
                position="absolute",
                top="-8px",
                right="-4px",
                width="32px",
                height="12px",
                background="rgba(251, 191, 36, 0.6)",
                transform="rotate(15deg)",
                border_radius="2px",
            ),
            # Photo area with initials
            rx.box(
                rx.text(
                    initials,
                    font_size="28px",
                    font_weight="bold",
                    color="#9ca3af",
                    letter_spacing="2px",
                ),
                width="112px",
                height="96px",
                background="linear-gradient(135deg, #374151 0%, #1f2937 100%)",
                display="flex",
                align_items="center",
                justify_content="center",
                margin_bottom="4px",
            ),
            # Name label (handwritten style)
            rx.text(
                name,
                font_size="12px",
                font_weight="500",
                color="#374151",
                text_align="center",
                font_family="'Brush Script MT', 'Segoe Script', cursive",
                white_space="nowrap",
                overflow="hidden",
                text_overflow="ellipsis",
                width="100%",
                padding="0 4px",
            ),
            # Selection ring (reactive)
            rx.cond(
                InvestigationState.selected_actor_id == actor_id,
                rx.box(
                    position="absolute",
                    inset="-4px",
                    border="3px solid #dc2626",
                    border_radius="4px",
                    pointer_events="none",
                ),
                rx.fragment(),
            ),
            # Main card styles
            position="relative",
            background="linear-gradient(145deg, #faf5f0 0%, #f5ebe0 100%)",
            padding="8px",
            padding_bottom="28px",
            box_shadow=rx.cond(
                InvestigationState.selected_actor_id == actor_id,
                "0 0 0 3px #dc2626, 0 8px 12px rgba(0, 0, 0, 0.4)",
                "4px 4px 12px rgba(0, 0, 0, 0.4)",
            ),
            border_radius="2px",
            cursor="pointer",
            transform=f"rotate({rotation}deg)",
            _hover={
                "transform": f"rotate({rotation - 2}deg) scale(1.05)",
                "box_shadow": "6px 6px 16px rgba(0, 0, 0, 0.5)",
            },
            transition="all 0.2s ease",
            on_click=lambda aid=actor_id: InvestigationState.select_actor(aid),
        ),
        position="absolute",
        left=f"{x}px",
        top=f"{y}px",
        transform="translate(-50%, -50%)",
        z_index=rx.cond(
            InvestigationState.selected_actor_id == actor_id,
            "30",
            "10",
        ),
        key=actor_id,
    )


# Aliases for compatibility
def actors_layer() -> rx.Component:
    return actors_layer_static()


def actor_node_simple(position: dict) -> rx.Component:
    """Not used - kept for compatibility."""
    return rx.fragment()


def actor_node(position: dict) -> rx.Component:
    """Not used - kept for compatibility."""
    return rx.fragment()


def polaroid_card(actor: dict) -> rx.Component:
    """Not used - kept for compatibility."""
    return rx.fragment()
