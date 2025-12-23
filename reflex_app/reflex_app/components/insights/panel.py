"""Insights Panel component.

Right sidebar showing perspectives, insights, recommendations,
and warnings from the research analysis.
"""
import reflex as rx
from ...state import PlaybackState
from ...models.research_types import PerspectiveView
from .items import (
    insights_list,
    recommendations_section,
    warnings_section,
    source_item,
)


def insights_panel() -> rx.Component:
    """Render the right sidebar with perspectives and insights."""
    return rx.box(
        # Header
        rx.hstack(
            rx.icon("brain", size=20, color="#a78bfa"),
            rx.text(
                "INSIGHTS",
                font_size="12px",
                font_weight="700",
                color="#a78bfa",
                letter_spacing="2px",
            ),
            gap="8px",
            margin_bottom="16px",
        ),
        # Case info
        rx.vstack(
            rx.text(
                PlaybackState.case_name,
                font_size="14px",
                font_weight="600",
                color="white",
            ),
            rx.text(
                PlaybackState.query,
                font_size="11px",
                color="#9ca3af",
                line_height="1.4",
            ),
            align="start",
            gap="4px",
            margin_bottom="16px",
            padding="12px",
            background="rgba(31, 41, 55, 0.5)",
            border_radius="8px",
            width="100%",
        ),
        # Stats summary
        stats_summary(),
        # Perspectives
        rx.vstack(
            rx.foreach(
                PlaybackState.perspectives_data,
                perspective_section,
            ),
            gap="16px",
            width="100%",
        ),
        class_name="insights-panel",
        position="fixed",
        right="0",
        top="80px",
        bottom="160px",
        width="320px",
        background="rgba(17, 24, 39, 0.95)",
        backdrop_filter="blur(12px)",
        border_left="1px solid rgba(55, 65, 81, 0.5)",
        overflow_y="auto",
        padding="16px",
        z_index="50",
    )


def stats_summary() -> rx.Component:
    """Summary statistics bar."""
    return rx.hstack(
        stat_badge(
            rx.icon("file-text", size=12),
            PlaybackState.finding_count,
            "findings",
        ),
        stat_badge(
            rx.icon("link", size=12),
            PlaybackState.source_count,
            "sources",
        ),
        gap="8px",
        margin_bottom="16px",
        width="100%",
    )


def stat_badge(icon: rx.Component, value: rx.Var, label: str) -> rx.Component:
    """Single stat badge."""
    return rx.hstack(
        icon,
        rx.text(
            value,
            font_size="14px",
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
        padding="8px 12px",
        background="rgba(55, 65, 81, 0.4)",
        border_radius="6px",
        flex="1",
    )


def perspective_section(perspective: PerspectiveView) -> rx.Component:
    """Render a single perspective section (simplified for Reflex compatibility)."""
    return rx.vstack(
        # Type badge
        rx.badge(
            perspective.type_upper,
            color_scheme="purple",
            size="1",
            variant="surface",
        ),
        # Analysis text
        rx.text(
            perspective.analysis_truncated,
            font_size="12px",
            color="#d1d5db",
            line_height="1.5",
        ),
        align="start",
        gap="12px",
        width="100%",
        class_name="perspective-section",
        background="rgba(31, 41, 55, 0.5)",
        border="1px solid rgba(55, 65, 81, 0.5)",
        border_radius="8px",
        padding="12px",
    )


def sources_panel() -> rx.Component:
    """Expandable sources list panel."""
    return rx.accordion.root(
        rx.accordion.item(
            header=rx.hstack(
                rx.icon("link-2", size=14, color="#60a5fa"),
                rx.text(
                    "SOURCES",
                    font_size="10px",
                    font_weight="600",
                    color="#60a5fa",
                    letter_spacing="1px",
                ),
                rx.badge(
                    PlaybackState.source_count,
                    color_scheme="blue",
                    size="1",
                ),
                gap="6px",
            ),
            content=rx.vstack(
                rx.foreach(
                    PlaybackState.sources_data[:10],
                    source_item,
                ),
                gap="4px",
                padding_top="8px",
                max_height="200px",
                overflow_y="auto",
            ),
            value="sources",
        ),
        type="single",
        collapsible=True,
        variant="ghost",
    )
