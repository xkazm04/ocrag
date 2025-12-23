"""Timeline Panel component.

Displays the timeline at the bottom of the investigation board
with markers and event carousel. Uses static rendering.
"""
import reflex as rx
from ..state import InvestigationState
from ..lib.mock_data import investigation_data


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


def _build_markers_data() -> list:
    """Build static timeline markers data."""
    return [
        {
            "id": f"marker-{i}",
            "year": m.year,
            "month": m.month or "",
            "event_count": m.event_count,
            "is_active": m.is_active,
            "severity": m.severity,
            "color": _get_severity_color(m.severity),
        }
        for i, m in enumerate(investigation_data.timeline)
    ]


def _build_events_data() -> list:
    """Build static events data sorted by date."""
    events = sorted(investigation_data.events, key=lambda e: e.date, reverse=True)
    return [
        {
            "id": e.id,
            "title": e.title,
            "date": e.date,
            "severity": e.severity,
            "is_key_event": e.is_key_event or False,
            "color": _get_severity_color(e.severity),
        }
        for e in events
    ]


# Pre-calculate at module load time
_MARKERS_DATA = _build_markers_data()
_EVENTS_DATA = _build_events_data()


def timeline_panel() -> rx.Component:
    """Render the timeline panel at the bottom of the board."""
    return rx.box(
        # Timeline markers
        rx.hstack(
            *[timeline_marker_static(m) for m in _MARKERS_DATA],
            justify="between",
            padding="0 60px",
            margin_bottom="16px",
        ),
        # Events carousel with navigation
        rx.hstack(
            # Previous button
            rx.button(
                rx.icon("chevron-left", size=20),
                on_click=lambda: InvestigationState.navigate_carousel(-1),
                variant="ghost",
                color_scheme="gray",
                size="2",
            ),
            # Events container
            rx.box(
                rx.hstack(
                    *[event_card_static(e) for e in _EVENTS_DATA],
                    gap="12px",
                    padding="8px 0",
                ),
                overflow_x="auto",
                flex="1",
                style={
                    "scrollbar_width": "none",
                    "-ms-overflow-style": "none",
                },
            ),
            # Next button
            rx.button(
                rx.icon("chevron-right", size=20),
                on_click=lambda: InvestigationState.navigate_carousel(1),
                variant="ghost",
                color_scheme="gray",
                size="2",
            ),
            align="center",
            gap="8px",
            width="100%",
        ),
        position="fixed",
        bottom="0",
        left="0",
        right="0",
        z_index="100",
        background="linear-gradient(to top, rgba(3, 7, 18, 0.95) 0%, rgba(3, 7, 18, 0.8) 100%)",
        backdrop_filter="blur(12px)",
        border_top="1px solid rgba(55, 65, 81, 0.5)",
        padding="16px 24px",
    )


def timeline_marker_static(marker: dict) -> rx.Component:
    """Render a single timeline marker with static data."""
    severity = marker["severity"]
    is_active = marker["is_active"]
    month = marker["month"]
    year = marker["year"]
    event_count = marker["event_count"]
    color = marker["color"]

    return rx.vstack(
        # Marker dot
        rx.box(
            # Event count badge
            rx.box(
                rx.text(
                    str(event_count),
                    font_size="8px",
                    font_weight="bold",
                    color="white",
                ),
                position="absolute",
                top="-6px",
                right="-6px",
                background="#374151",
                border_radius="50%",
                width="14px",
                height="14px",
                display="flex",
                align_items="center",
                justify_content="center",
            ) if event_count > 0 else rx.fragment(),
            width="16px" if is_active else "12px",
            height="16px" if is_active else "12px",
            border_radius="50%",
            background=color,
            box_shadow=f"0 0 12px {color}" if is_active else "none",
            position="relative",
            transition="all 0.2s ease",
        ),
        # Label
        rx.text(
            f"{month} {year}",
            font_size="10px",
            color="white" if is_active else "#9ca3af",
            font_weight="600" if is_active else "400",
        ),
        align="center",
        gap="4px",
        cursor="pointer",
        _hover={
            "transform": "scale(1.1)",
        },
        transition="transform 0.2s ease",
        key=marker["id"],
    )


def event_card_static(event: dict) -> rx.Component:
    """Render a single event card with static data."""
    title = event["title"]
    date = event["date"]
    is_key_event = event["is_key_event"]
    color = event["color"]
    event_id = event["id"]

    return rx.box(
        # Key event indicator
        rx.box(
            rx.icon("star", size=12, color="#fbbf24"),
            position="absolute",
            top="8px",
            right="8px",
        ) if is_key_event else rx.fragment(),
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
        # Content
        rx.vstack(
            rx.text(
                title,
                font_size="12px",
                font_weight="600",
                color="white",
                white_space="nowrap",
                overflow="hidden",
                text_overflow="ellipsis",
                width="100%",
            ),
            rx.text(
                date,
                font_size="10px",
                color="#9ca3af",
            ),
            align="start",
            gap="4px",
            padding_left="8px",
        ),
        position="relative",
        flex_shrink="0",
        width="176px",
        background="rgba(31, 41, 55, 0.8)",
        border="1px solid rgba(75, 85, 99, 0.5)",
        border_radius="8px",
        padding="12px",
        cursor="pointer",
        transition="all 0.2s ease",
        _hover={
            "background": "rgba(55, 65, 81, 0.8)",
            "transform": "translateY(-2px)",
        },
        on_click=lambda eid=event_id: InvestigationState.open_dossier(eid),
        key=event_id,
    )


# Keep old function names for compatibility
def timeline_marker(marker: dict) -> rx.Component:
    return rx.fragment()


def event_card(event: dict) -> rx.Component:
    return rx.fragment()
