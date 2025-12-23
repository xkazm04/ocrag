"""Event card component for the timeline.

Individual event cards displayed in the timeline carousel.
"""
import reflex as rx
from ...state import PlaybackState


def _get_severity_color(severity: str) -> str:
    """Get color for severity level."""
    colors = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#3b82f6",
        "info": "#6b7280",
    }
    return colors.get(severity, "#6b7280")


def event_card_v2(event: dict) -> rx.Component:
    """Render a single event card with playback awareness."""
    event_id = event["id"]
    title_truncated = event["title_truncated"]
    date_text = event["date_text"]
    severity = event["severity"]
    is_new = event["is_new"]
    finding_type = event["finding_type"]
    finding_type_upper = event["finding_type_upper"]

    color = _get_severity_color("medium")  # Use static default since severity is a var
    # Use rx.cond with bitwise & for Reflex vars instead of Python 'and'
    is_current = (PlaybackState.current_event != None) & (PlaybackState.current_event["id"] == event_id)

    return rx.box(
        # Finding type badge
        rx.badge(
            finding_type_upper,
            position="absolute",
            top="6px",
            right="6px",
            size="1",
            color_scheme=rx.cond(
                finding_type == "event",
                "blue",
                rx.cond(
                    finding_type == "actor",
                    "purple",
                    rx.cond(
                        finding_type == "relationship",
                        "green",
                        "gray",
                    ),
                ),
            ),
            variant="surface",
        ),
        # Severity indicator bar
        rx.box(
            width="3px",
            height="100%",
            position="absolute",
            left="0",
            top="0",
            border_radius="4px 0 0 4px",
            background=color,
        ),
        # New reveal indicator
        rx.cond(
            is_new,
            rx.box(
                position="absolute",
                inset="-2px",
                border="2px solid #fbbf24",
                border_radius="10px",
                box_shadow="0 0 12px rgba(251, 191, 36, 0.5)",
                pointer_events="none",
            ),
            rx.fragment(),
        ),
        # Content
        rx.vstack(
            rx.text(
                title_truncated,
                font_size="12px",
                font_weight="600",
                color="white",
                white_space="nowrap",
                overflow="hidden",
                text_overflow="ellipsis",
                width="100%",
            ),
            rx.text(
                date_text,
                font_size="10px",
                color="#9ca3af",
            ),
            align="start",
            gap="4px",
            padding_left="8px",
        ),
        position="relative",
        flex_shrink="0",
        width="200px",
        background=rx.cond(
            is_current,
            "rgba(59, 130, 246, 0.2)",
            "rgba(31, 41, 55, 0.8)",
        ),
        border=rx.cond(
            is_current,
            "2px solid #60a5fa",
            "1px solid rgba(75, 85, 99, 0.5)",
        ),
        box_shadow=rx.cond(
            is_current,
            "0 0 16px rgba(96, 165, 250, 0.4)",
            "none",
        ),
        border_radius="8px",
        padding="12px",
        cursor="pointer",
        transition="all 0.2s ease",
        _hover={
            "background": "rgba(55, 65, 81, 0.8)",
            "transform": "translateY(-2px)",
        },
        class_name=rx.cond(
            is_new,
            "event-card event-reveal",
            "event-card",
        ),
        on_click=lambda: PlaybackState.select_event(event_id),
        key=event_id,
    )
