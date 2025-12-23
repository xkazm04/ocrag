"""Individual insight item components.

Components for rendering insights, recommendations, warnings,
and sources within the insights panel.
"""
import reflex as rx


def insight_bullet(insight: str) -> rx.Component:
    """Single insight bullet."""
    return rx.hstack(
        rx.icon("chevron-right", size=12, color="#a78bfa"),
        rx.text(
            insight,
            font_size="11px",
            color="#d1d5db",
            line_height="1.4",
        ),
        gap="6px",
        align="start",
    )


def insights_list(insights: list) -> rx.Component:
    """List of key insights."""
    return rx.vstack(
        rx.text(
            "KEY INSIGHTS",
            font_size="10px",
            font_weight="600",
            color="#6b7280",
            letter_spacing="1px",
        ),
        rx.foreach(
            insights,
            insight_bullet,
        ),
        align="start",
        gap="6px",
        width="100%",
    )


def recommendation_item(rec: str) -> rx.Component:
    """Single recommendation item."""
    return rx.text(
        f"- {rec}",
        font_size="11px",
        color="#86efac",
        line_height="1.4",
    )


def recommendations_section(recommendations: list) -> rx.Component:
    """Collapsible recommendations section."""
    return rx.accordion.root(
        rx.accordion.item(
            header=rx.hstack(
                rx.icon("lightbulb", size=12, color="#22c55e"),
                rx.text(
                    "RECOMMENDATIONS",
                    font_size="10px",
                    font_weight="600",
                    color="#22c55e",
                    letter_spacing="1px",
                ),
                gap="6px",
            ),
            content=rx.vstack(
                rx.foreach(
                    recommendations,
                    recommendation_item,
                ),
                gap="6px",
                padding_top="8px",
            ),
            value="recommendations",
        ),
        type="single",
        collapsible=True,
        variant="ghost",
    )


def warning_card(warning: str) -> rx.Component:
    """Single warning card."""
    return rx.box(
        rx.text(
            warning,
            font_size="11px",
            color="#fcd34d",
            line_height="1.4",
        ),
        background="rgba(251, 191, 36, 0.1)",
        border="1px solid rgba(251, 191, 36, 0.3)",
        border_radius="6px",
        padding="8px 12px",
        width="100%",
    )


def warnings_section(warnings: list) -> rx.Component:
    """Warnings display section."""
    return rx.vstack(
        rx.hstack(
            rx.icon("alert-triangle", size=12, color="#fbbf24"),
            rx.text(
                "WARNINGS",
                font_size="10px",
                font_weight="600",
                color="#fbbf24",
                letter_spacing="1px",
            ),
            gap="6px",
        ),
        rx.foreach(
            warnings,
            warning_card,
        ),
        align="start",
        gap="8px",
        width="100%",
    )


def source_item(source: dict) -> rx.Component:
    """Single source item."""
    return rx.hstack(
        rx.box(
            width="4px",
            height="4px",
            border_radius="50%",
            background="#60a5fa",
        ),
        rx.link(
            rx.text(
                source.get("domain", "Unknown"),
                font_size="11px",
                color="#93c5fd",
            ),
            href=source.get("url", "#"),
            is_external=True,
        ),
        gap="8px",
        align="center",
    )
