"""Actor card components.

Polaroid-style actor cards for the detective board.
"""
import reflex as rx
from ...state import PlaybackState
from .helpers import get_initials, get_risk_color


def actors_layer_v2() -> rx.Component:
    """Render visible actors with playback-based visibility."""
    return rx.fragment(
        rx.foreach(
            PlaybackState.actor_positions,
            actor_node_animated,
        ),
    )


def actor_node_animated(position: dict) -> rx.Component:
    """Single actor node with visibility animation."""
    return rx.box(
        polaroid_card_v2(position),
        position="absolute",
        left=position["x"].to_string() + "px",
        top=position["y"].to_string() + "px",
        transform="translate(-50%, -50%)",
        z_index=rx.cond(
            PlaybackState.selected_actor_id == position["actor_id"],
            "30",
            rx.cond(
                position["is_new"],
                "25",
                "10",
            ),
        ),
        class_name=rx.cond(
            position["is_new"],
            "actor-node animate-reveal actor-glow",
            "actor-node",
        ),
        key=position["actor_id"],
    )


def polaroid_card_v2(position: dict) -> rx.Component:
    """Polaroid-style actor card for playback mode."""
    actor_id = position["actor_id"]
    is_new = position["is_new"]
    card_transform = position["transform"]
    hover_transform = position["hover_transform"]
    actor_label = position["label"]

    return rx.box(
        # Pushpin at top
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background="#dc2626",
            position="absolute",
            top="-4px",
            left="50%",
            transform="translateX(-50%)",
            box_shadow="0 2px 4px rgba(0, 0, 0, 0.3)",
        ),
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
        # Photo area with initials placeholder
        rx.box(
            rx.icon("user", size=32, color="#9ca3af"),
            width="112px",
            height="96px",
            background="linear-gradient(135deg, #374151 0%, #1f2937 100%)",
            display="flex",
            align_items="center",
            justify_content="center",
            margin_bottom="4px",
        ),
        # Name label placeholder
        rx.text(
            actor_label,
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
        # Selection ring
        rx.cond(
            PlaybackState.selected_actor_id == actor_id,
            rx.box(
                position="absolute",
                inset="-4px",
                border="3px solid #dc2626",
                border_radius="4px",
                pointer_events="none",
            ),
            rx.fragment(),
        ),
        # New reveal glow
        rx.cond(
            is_new,
            rx.box(
                position="absolute",
                inset="-8px",
                border="2px solid #fbbf24",
                border_radius="8px",
                box_shadow="0 0 20px rgba(251, 191, 36, 0.6)",
                pointer_events="none",
                class_name="glow-pulse",
            ),
            rx.fragment(),
        ),
        # Card styles
        position="relative",
        background="linear-gradient(145deg, #faf5f0 0%, #f5ebe0 100%)",
        padding="8px",
        padding_bottom="28px",
        box_shadow=rx.cond(
            PlaybackState.selected_actor_id == actor_id,
            "0 0 0 3px #dc2626, 0 8px 12px rgba(0, 0, 0, 0.4)",
            "4px 4px 12px rgba(0, 0, 0, 0.4)",
        ),
        border_radius="2px",
        cursor="pointer",
        transform=card_transform,
        _hover={
            "transform": hover_transform,
            "box_shadow": "6px 6px 16px rgba(0, 0, 0, 0.5)",
        },
        transition="all 0.2s ease",
        on_click=lambda: PlaybackState.select_actor(actor_id),
    )


def actor_node_with_data(actor: dict, position: dict) -> rx.Component:
    """Actor node with full data from visible_actors."""
    actor_id = actor.get("id", "")
    name = actor.get("name", "Unknown")
    risk_level = actor.get("risk_level", "medium")
    is_new = actor.get("is_new", False)

    x = position.get("x", 1000)
    y = position.get("y", 350)
    index = position.get("index", 0)
    rotation = ((index % 7) - 3) * 2

    initials = get_initials(name)
    risk_color = get_risk_color(risk_level)

    return rx.box(
        rx.box(
            # Pushpin
            rx.box(
                width="10px",
                height="10px",
                border_radius="50%",
                background=risk_color,
                position="absolute",
                top="-5px",
                left="50%",
                transform="translateX(-50%)",
                box_shadow="0 2px 4px rgba(0, 0, 0, 0.3)",
            ),
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
            # Photo area
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
            # Name label
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
            # Selection ring
            rx.cond(
                PlaybackState.selected_actor_id == actor_id,
                rx.box(
                    position="absolute",
                    inset="-4px",
                    border="3px solid #dc2626",
                    border_radius="4px",
                    pointer_events="none",
                ),
                rx.fragment(),
            ),
            # Card styles
            position="relative",
            background="linear-gradient(145deg, #faf5f0 0%, #f5ebe0 100%)",
            padding="8px",
            padding_bottom="28px",
            box_shadow=rx.cond(
                PlaybackState.selected_actor_id == actor_id,
                "0 0 0 3px #dc2626, 0 8px 12px rgba(0, 0, 0, 0.4)",
                "4px 4px 12px rgba(0, 0, 0, 0.4)",
            ),
            border_radius="2px",
            cursor="pointer",
            transform=f"rotate({rotation}deg)",
            _hover={
                "transform": f"rotate({rotation - 2}deg) scale(1.05)",
            },
            transition="all 0.2s ease",
            on_click=lambda: PlaybackState.select_actor(actor_id),
        ),
        position="absolute",
        left=f"{x}px",
        top=f"{y}px",
        transform="translate(-50%, -50%)",
        z_index="10",
        class_name="actor-node animate-reveal" if is_new else "actor-node",
        key=actor_id,
    )
