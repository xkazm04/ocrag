"""Playback Controls component.

Provides play/pause, speed control, and timeline scrubber for
the next-gen detective board timeline playback.
"""
import reflex as rx
from ..state import PlaybackState


def playback_controls() -> rx.Component:
    """Render the playback control bar."""
    return rx.hstack(
        # Play/Pause button
        rx.button(
            rx.cond(
                PlaybackState.is_playing,
                rx.icon("pause", size=20),
                rx.icon("play", size=20),
            ),
            on_click=PlaybackState.toggle_playback,
            class_name="playback-btn",
            variant="ghost",
            color_scheme="blue",
            size="3",
        ),
        # Speed selector
        rx.select(
            ["1x", "2x", "5x"],
            default_value="1x",
            on_change=PlaybackState.set_speed,
            size="2",
            variant="soft",
            color_scheme="gray",
        ),
        # Current date display
        rx.box(
            rx.text(
                PlaybackState.current_date_text,
                font_size="14px",
                font_weight="600",
                color="#60a5fa",
            ),
            padding="6px 14px",
            background="rgba(59, 130, 246, 0.1)",
            border_radius="6px",
            min_width="180px",
            text_align="center",
        ),
        # Progress scrubber
        rx.box(
            rx.slider(
                default_value=[0],
                value=[PlaybackState.progress_percent],
                on_change=lambda v: PlaybackState.seek_by_percent(v[0]),
                min=0,
                max=100,
                step=1,
                size="1",
            ),
            flex="1",
            padding_x="16px",
        ),
        # Date range labels
        rx.hstack(
            rx.text(
                PlaybackState.earliest_date,
                font_size="11px",
                color="#6b7280",
            ),
            rx.text(
                "-",
                font_size="11px",
                color="#4b5563",
            ),
            rx.text(
                PlaybackState.latest_date,
                font_size="11px",
                color="#6b7280",
            ),
            gap="4px",
        ),
        # Reset button
        rx.button(
            rx.icon("rotate-ccw", size=16),
            on_click=PlaybackState.reset_playback,
            variant="ghost",
            color_scheme="gray",
            size="2",
            title="Reset to beginning",
        ),
        class_name="playback-controls-bar",
        gap="16px",
        align="center",
        padding="12px 16px",
        background="rgba(17, 24, 39, 0.8)",
        border_radius="8px",
        margin_bottom="16px",
    )


def now_marker() -> rx.Component:
    """Animated 'now' marker on the timeline track."""
    return rx.box(
        rx.box(
            class_name="now-marker-dot",
        ),
        position="absolute",
        left=f"{PlaybackState.progress_percent}%",
        top="50%",
        transform="translate(-50%, -50%)",
        z_index="10",
        transition="left 0.3s ease-out",
        class_name="now-marker",
    )


def timeline_track() -> rx.Component:
    """Timeline track with year markers and now indicator."""
    return rx.box(
        # Background track line
        rx.box(
            width="100%",
            height="2px",
            background="rgba(75, 85, 99, 0.5)",
            position="absolute",
            top="50%",
            transform="translateY(-50%)",
        ),
        # Progress fill
        rx.box(
            width=f"{PlaybackState.progress_percent}%",
            height="2px",
            background="#3b82f6",
            position="absolute",
            top="50%",
            transform="translateY(-50%)",
            transition="width 0.3s ease-out",
        ),
        # Now marker
        now_marker(),
        # Year markers
        rx.hstack(
            rx.foreach(
                PlaybackState.timeline_years,
                year_marker,
            ),
            justify="between",
            width="100%",
            padding="0 20px",
        ),
        position="relative",
        height="40px",
        width="100%",
        margin_y="8px",
    )


def year_marker(year: str) -> rx.Component:
    """Single year marker on the timeline."""
    return rx.vstack(
        rx.box(
            width="8px",
            height="8px",
            border_radius="50%",
            background="#4b5563",
        ),
        rx.text(
            year,
            font_size="10px",
            color="#9ca3af",
        ),
        align="center",
        gap="4px",
        cursor="pointer",
        _hover={
            "transform": "scale(1.1)",
        },
        transition="transform 0.2s ease",
    )


def playback_stats() -> rx.Component:
    """Display current playback statistics."""
    return rx.hstack(
        rx.hstack(
            rx.icon("users", size=14, color="#9ca3af"),
            rx.text(
                PlaybackState.case_summary["visible_actors"],
                font_size="12px",
                color="white",
                font_weight="600",
            ),
            rx.text(
                f"/ {PlaybackState.case_summary['total_actors']}",
                font_size="12px",
                color="#6b7280",
            ),
            gap="4px",
            align="center",
        ),
        rx.hstack(
            rx.icon("calendar", size=14, color="#9ca3af"),
            rx.text(
                PlaybackState.case_summary["visible_events"],
                font_size="12px",
                color="white",
                font_weight="600",
            ),
            rx.text(
                f"/ {PlaybackState.case_summary['total_events']}",
                font_size="12px",
                color="#6b7280",
            ),
            gap="4px",
            align="center",
        ),
        rx.hstack(
            rx.icon("git-branch", size=14, color="#9ca3af"),
            rx.text(
                PlaybackState.case_summary["visible_connections"],
                font_size="12px",
                color="white",
                font_weight="600",
            ),
            gap="4px",
            align="center",
        ),
        gap="20px",
        align="center",
    )
