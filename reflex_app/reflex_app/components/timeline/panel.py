"""Timeline Panel V2 component.

Displays the timeline at the bottom of the next-gen detective board
with playback controls and visible events carousel.
"""
import reflex as rx
from ...state import PlaybackState
from ..playback_controls import playback_controls, playback_stats
from .event_card import event_card_v2


def timeline_panel_v2() -> rx.Component:
    """Render the enhanced timeline panel with playback."""
    return rx.box(
        # Playback controls bar
        playback_controls(),
        # Stats display
        rx.hstack(
            playback_stats(),
            justify="center",
            margin_bottom="12px",
        ),
        # Events carousel
        rx.hstack(
            # Previous button
            rx.button(
                rx.icon("chevron-left", size=20),
                on_click=lambda: PlaybackState.navigate_carousel(-1),
                variant="ghost",
                color_scheme="gray",
                size="2",
            ),
            # Events container
            rx.box(
                rx.hstack(
                    rx.foreach(
                        PlaybackState.visible_events,
                        event_card_v2,
                    ),
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
                on_click=lambda: PlaybackState.navigate_carousel(1),
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
        right="320px",
        z_index="100",
        background="linear-gradient(to top, rgba(3, 7, 18, 0.95) 0%, rgba(3, 7, 18, 0.8) 100%)",
        backdrop_filter="blur(12px)",
        border_top="1px solid rgba(55, 65, 81, 0.5)",
        padding="16px 24px",
    )


def timeline_markers_v2() -> rx.Component:
    """Year markers along the timeline."""
    return rx.hstack(
        rx.foreach(
            PlaybackState.timeline_years,
            year_marker,
        ),
        justify="between",
        padding="0 60px",
        margin_bottom="8px",
    )


def year_marker(year: str) -> rx.Component:
    """Single year marker."""
    return rx.vstack(
        rx.box(
            width="12px",
            height="12px",
            border_radius="50%",
            background="#4b5563",
            border="2px solid #374151",
        ),
        rx.text(
            year,
            font_size="11px",
            color="#9ca3af",
            font_weight="600",
        ),
        align="center",
        gap="4px",
        cursor="pointer",
        _hover={
            "transform": "scale(1.1)",
        },
        transition="transform 0.2s ease",
        on_click=lambda y=year: PlaybackState.seek(f"{y}-01-01"),
    )
