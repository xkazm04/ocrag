"""Investigation Board V2 - Next-Gen Detective Board.

Main page assembling all components with timeline playback,
insights panel, and progressive actor/connection reveal.
"""
import reflex as rx
from ..state import PlaybackState
from ..components import (
    actors_layer_v2,
    primary_actor_hub,
    connection_lines_v2,
    timeline_panel_v2,
    event_dossier_modal,
    insights_panel,
)


def header_bar_v2() -> rx.Component:
    """Top header bar with case info and stats."""
    return rx.box(
        rx.hstack(
            # Logo/brand
            rx.hstack(
                rx.icon("radar", size=24, color="#dc2626"),
                rx.text(
                    "DEEP RESEARCH",
                    font_size="14px",
                    font_weight="800",
                    color="white",
                    letter_spacing="3px",
                ),
                gap="10px",
                align="center",
            ),
            # Case name
            rx.text(
                PlaybackState.case_name,
                font_size="16px",
                font_weight="600",
                color="white",
            ),
            # Stats
            rx.hstack(
                stat_pill("file-text", PlaybackState.finding_count, "findings"),
                stat_pill("link", PlaybackState.source_count, "sources"),
                stat_pill("users", PlaybackState.case_summary["visible_actors"], "actors"),
                stat_pill("calendar", PlaybackState.case_summary["visible_events"], "events"),
                gap="12px",
            ),
            # Loading status
            rx.cond(
                PlaybackState.is_loaded,
                rx.badge("LOADED", color_scheme="green", size="1"),
                rx.badge("LOADING...", color_scheme="yellow", size="1"),
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        position="fixed",
        top="0",
        left="0",
        right="0",
        z_index="100",
        background="rgba(3, 7, 18, 0.9)",
        backdrop_filter="blur(12px)",
        border_bottom="1px solid rgba(55, 65, 81, 0.5)",
        padding="12px 24px",
    )


def stat_pill(icon_name: str, value: rx.Var, label: str) -> rx.Component:
    """Small stat pill for header."""
    return rx.hstack(
        rx.icon(icon_name, size=12, color="#9ca3af"),
        rx.text(
            value,
            font_size="12px",
            font_weight="700",
            color="white",
        ),
        rx.text(
            label,
            font_size="10px",
            color="#6b7280",
        ),
        gap="4px",
        align="center",
        background="rgba(55, 65, 81, 0.4)",
        padding="4px 10px",
        border_radius="12px",
    )


def cork_board_background() -> rx.Component:
    """Cork board textured background."""
    return rx.box(
        class_name="cork-board",
        position="absolute",
        inset="0",
    )


def legend_panel() -> rx.Component:
    """Left side legend showing connection types."""
    return rx.vstack(
        rx.text(
            "CONNECTIONS",
            font_size="10px",
            font_weight="700",
            color="#6b7280",
            letter_spacing="2px",
            margin_bottom="8px",
        ),
        legend_item("#dc2626", "Political"),
        legend_item("#f97316", "Economic"),
        legend_item("#3b82f6", "Diplomatic"),
        legend_item("#22c55e", "Alliance"),
        legend_item("#8b5cf6", "Support"),
        gap="6px",
        align="start",
        position="fixed",
        left="24px",
        top="50%",
        transform="translateY(-50%)",
        z_index="50",
        background="rgba(17, 24, 39, 0.9)",
        border="1px solid rgba(55, 65, 81, 0.5)",
        border_radius="8px",
        padding="12px",
    )


def legend_item(color: str, label: str) -> rx.Component:
    """Single legend item."""
    return rx.hstack(
        rx.box(
            width="20px",
            height="3px",
            background=color,
            border_radius="2px",
        ),
        rx.text(
            label,
            font_size="10px",
            color="#9ca3af",
        ),
        gap="8px",
        align="center",
    )


def investigation_board_v2() -> rx.Component:
    """Main next-gen investigation board page."""
    return rx.box(
        # Cork board background
        cork_board_background(),
        # Header bar
        header_bar_v2(),
        # Main board container
        rx.box(
            rx.box(
                # Connection lines layer (behind actors)
                connection_lines_v2(),
                # Central hub (primary actor)
                rx.box(
                    primary_actor_hub(),
                    position="absolute",
                    left="50%",
                    top="350px",
                    transform="translate(-50%, -50%)",
                    z_index="20",
                ),
                # Actor nodes layer
                actors_layer_v2(),
                position="relative",
                width="2000px",
                height="900px",
            ),
            position="absolute",
            top="80px",
            left="0",
            right="320px",  # Leave room for insights panel
            bottom="180px",
            display="flex",
            align_items="center",
            justify_content="center",
            overflow="auto",
        ),
        # Legend panel (left side)
        legend_panel(),
        # Insights panel (right side)
        insights_panel(),
        # Timeline panel (bottom)
        timeline_panel_v2(),
        # Event dossier modal
        event_dossier_modal(),
        # Page container
        height="100vh",
        width="100vw",
        background="#030712",
        color="white",
        overflow="hidden",
        position="relative",
        # Load data on mount
        on_mount=PlaybackState.load_research_data,
    )


def index() -> rx.Component:
    """Index page wrapper."""
    return investigation_board_v2()
