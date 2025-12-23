"""Header Bar component.

Displays case information and stats at the top of the investigation board.
"""
import reflex as rx
from ..state import InvestigationState


def header_bar() -> rx.Component:
    """Render the header bar with case info and stats."""
    case_info = InvestigationState.case_info
    summary = InvestigationState.case_summary

    return rx.box(
        rx.hstack(
            # Left: Case info
            rx.hstack(
                # Shield icon
                rx.box(
                    rx.icon("shield", size=20, color="#f87171"),
                    width="40px",
                    height="40px",
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    background="rgba(239, 68, 68, 0.2)",
                    border="1px solid rgba(239, 68, 68, 0.3)",
                    border_radius="8px",
                ),
                # Case name and ID
                rx.vstack(
                    rx.hstack(
                        rx.text(
                            case_info["case_name"],
                            font_size="14px",
                            font_weight="800",
                            color="white",
                            text_transform="uppercase",
                            letter_spacing="0.05em",
                        ),
                        rx.box(
                            rx.text(
                                case_info["priority"].to_string().upper(),
                                font_size="10px",
                                font_weight="bold",
                                color="#f87171",
                            ),
                            padding="2px 8px",
                            background="rgba(239, 68, 68, 0.2)",
                            border="1px solid rgba(239, 68, 68, 0.3)",
                            border_radius="4px",
                        ),
                        gap="8px",
                        align="center",
                    ),
                    rx.text(
                        rx.text.span(case_info["case_id"]),
                        rx.text.span(" • "),
                        rx.text.span(case_info["case_code"]),
                        font_size="11px",
                        color="#6b7280",
                        font_family="monospace",
                    ),
                    align="start",
                    gap="2px",
                ),
                gap="12px",
                align="center",
            ),
            # Center: Quick stats
            rx.hstack(
                # Live monitoring badge
                rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="50%",
                        background="#22c55e",
                        class_name="animate-pulse",
                    ),
                    rx.text(
                        "Live Monitoring",
                        font_size="12px",
                        color="#9ca3af",
                    ),
                    gap="8px",
                    align="center",
                    padding="6px 12px",
                    background="rgba(31, 41, 55, 0.6)",
                    border="1px solid rgba(55, 65, 81, 0.5)",
                    border_radius="8px",
                ),
                # Stats
                rx.hstack(
                    stat_item(summary["total_actors"], "Subjects"),
                    rx.divider(orientation="vertical", height="32px", color="rgba(55, 65, 81, 0.5)"),
                    stat_item(summary["confirmed_connections"], "Connections"),
                    rx.divider(orientation="vertical", height="32px", color="rgba(55, 65, 81, 0.5)"),
                    stat_item(summary["estimated_value"], "Est. Value", is_value=True),
                    gap="16px",
                    align="center",
                ),
                gap="24px",
                align="center",
            ),
            # Right: AI Confidence
            rx.hstack(
                rx.icon("trending-up", size=16, color="#60a5fa"),
                rx.vstack(
                    rx.text(
                        rx.text.span(summary["ai_confidence"].to_string()),
                        rx.text.span("%"),
                        font_size="18px",
                        font_weight="800",
                        color="#60a5fa",
                    ),
                    rx.text(
                        "AI CONFIDENCE",
                        font_size="9px",
                        color="#6b7280",
                        letter_spacing="0.1em",
                    ),
                    align="end",
                    gap="0",
                ),
                gap="8px",
                align="center",
                padding="8px 16px",
                background="linear-gradient(to right, rgba(59, 130, 246, 0.1), rgba(168, 85, 247, 0.1))",
                border="1px solid rgba(59, 130, 246, 0.3)",
                border_radius="12px",
            ),
            justify="between",
            align="center",
            width="100%",
            max_width="1600px",
            margin="0 auto",
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
        class_name="animate-fade-in",
    )


def stat_item(value: rx.Var, label: str, is_value: bool = False) -> rx.Component:
    """Render a stat item."""
    return rx.vstack(
        rx.text(
            value,
            font_size="18px",
            font_weight="700",
            color="#22c55e" if is_value else "white",
        ),
        rx.text(
            label,
            font_size="11px",
            color="#6b7280",
        ),
        align="center",
        gap="2px",
    )
