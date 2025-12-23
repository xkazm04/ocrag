"""Connection Lines V2 SVG component.

Renders red thread connections between actors with
playback-based visibility and draw animations.
"""
import reflex as rx
from ..state import PlaybackState


def _get_connection_color(conn_type: str) -> str:
    """Get color based on connection type."""
    colors = {
        "political": "#dc2626",  # Red
        "military": "#ef4444",   # Lighter red
        "economic": "#f97316",   # Orange
        "diplomatic": "#3b82f6", # Blue
        "conflict": "#ef4444",   # Red
        "alliance": "#22c55e",   # Green
        "support": "#8b5cf6",    # Purple
    }
    return colors.get(conn_type, "#dc2626")


def connection_lines_v2() -> rx.Component:
    """Render visible connections with playback-based visibility."""
    return rx.el.svg(
        # Draw each visible connection
        rx.foreach(
            PlaybackState.connection_paths,
            connection_path_v2,
        ),
        position="absolute",
        inset="0",
        width="100%",
        height="100%",
        style={"z_index": "1", "pointer_events": "none"},
        overflow="visible",
    )


def connection_path_v2(conn: dict) -> rx.Component:
    """Single connection path with draw animation."""
    path_d = conn["path"]
    conn_type = conn["type"]
    is_new = conn["is_new"]
    conn_id = conn["id"]

    color = _get_connection_color(conn_type)

    return rx.fragment(
        # Glow effect (behind)
        rx.el.path(
            d=path_d,
            stroke=color,
            stroke_width="6",
            stroke_opacity="0.15",
            stroke_linecap="round",
            fill="none",
            key=f"{conn_id}-glow",
        ),
        # Main line
        rx.el.path(
            d=path_d,
            stroke=color,
            stroke_width="2",
            stroke_opacity="0.8",
            stroke_linecap="round",
            fill="none",
            class_name=rx.cond(
                is_new,
                "connection-draw-animation",
                "",
            ),
            key=conn_id,
        ),
    )


def connection_line_static(
    path: str,
    conn_type: str = "political",
    is_new: bool = False,
    key: str = ""
) -> rx.Component:
    """Static connection line helper."""
    color = _get_connection_color(conn_type)

    return rx.fragment(
        rx.el.path(
            d=path,
            stroke=color,
            stroke_width="6",
            stroke_opacity="0.15",
            stroke_linecap="round",
            fill="none",
        ),
        rx.el.path(
            d=path,
            stroke=color,
            stroke_width="2",
            stroke_opacity="0.8",
            stroke_linecap="round",
            fill="none",
            class_name="connection-draw-animation" if is_new else "",
        ),
    )


def connection_labels_layer() -> rx.Component:
    """Optional layer showing connection type labels on hover."""
    return rx.fragment(
        # Labels can be added here if needed
    )
