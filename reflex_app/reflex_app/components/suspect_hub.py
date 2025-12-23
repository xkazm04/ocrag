"""Central Suspect Hub component.

Displays the primary suspect at the center of the investigation board
with a Polaroid-style appearance for the Red String theme.
"""
import reflex as rx
from ..state import InvestigationState


def suspect_hub() -> rx.Component:
    """Render the central suspect hub with Red String theme styling."""
    suspect = InvestigationState.primary_suspect_data

    return rx.box(
        # Outer rotating ring (CSS animation)
        rx.box(
            class_name="suspect-hub-outer",
        ),
        # Main hub container - Polaroid style
        rx.box(
            # Pushpin at top
            rx.box(
                class_name="pushpin pushpin-critical",
            ),
            # Photo area
            rx.box(
                # Silhouette avatar SVG
                rx.el.svg(
                    rx.el.circle(cx="50", cy="32", r="18", fill="#6b7280"),
                    rx.el.ellipse(cx="50", cy="80", rx="30", ry="25", fill="#6b7280"),
                    viewBox="0 0 100 100",
                    width="80px",
                    height="80px",
                ),
                class_name="polaroid-photo",
                width="120px",
                height="120px",
                display="flex",
                align_items="center",
                justify_content="center",
            ),
            # Name label
            rx.text(
                rx.cond(
                    suspect["name"],
                    suspect["name"],
                    "Unknown",
                ),
                class_name="polaroid-name",
                font_size="14px",
            ),
            class_name="polaroid animate-scale-in",
            width="136px",
            padding_bottom="28px",
            position="relative",
        ),
        # Name card below
        rx.box(
            # Header
            rx.hstack(
                rx.box(
                    width="8px",
                    height="8px",
                    border_radius="50%",
                    background="#ef4444",
                    class_name="animate-pulse",
                ),
                rx.text(
                    "PRIMARY SUSPECT",
                    font_size="10px",
                    font_weight="bold",
                    color="#f87171",
                    letter_spacing="0.1em",
                ),
                gap="6px",
                justify="center",
                margin_bottom="4px",
            ),
            # Name
            rx.text(
                rx.cond(
                    suspect["name"],
                    suspect["name"],
                    "Unknown",
                ),
                font_size="18px",
                font_weight="800",
                color="white",
                text_align="center",
            ),
            # Alias
            rx.cond(
                suspect["alias"],
                rx.text(
                    rx.text.span('aka "'),
                    rx.text.span(suspect["alias"]),
                    rx.text.span('"'),
                    font_size="12px",
                    color="#6b7280",
                    text_align="center",
                    font_style="italic",
                ),
                rx.fragment(),
            ),
            # Role & Organization
            rx.text(
                rx.cond(
                    suspect["role"],
                    rx.text.span(suspect["role"]),
                    rx.text.span(""),
                ),
                rx.text.span(" • "),
                rx.cond(
                    suspect["organization"],
                    rx.text.span(suspect["organization"]),
                    rx.text.span(""),
                ),
                font_size="12px",
                color="#9ca3af",
                text_align="center",
                margin_top="4px",
            ),
            # Footer info
            rx.hstack(
                rx.hstack(
                    rx.icon("map-pin", size=12, color="#6b7280"),
                    rx.text(
                        rx.cond(
                            suspect["last_known_location"],
                            suspect["last_known_location"],
                            "Unknown",
                        ),
                        font_size="11px",
                        color="#6b7280",
                    ),
                    gap="4px",
                ),
                rx.hstack(
                    rx.box(
                        width="6px",
                        height="6px",
                        border_radius="50%",
                        background="#22c55e",
                        class_name="animate-pulse",
                    ),
                    rx.text(
                        rx.cond(
                            suspect["last_activity"],
                            suspect["last_activity"],
                            "Unknown",
                        ),
                        font_size="11px",
                        color="#9ca3af",
                    ),
                    gap="4px",
                ),
                justify="between",
                width="100%",
                margin_top="12px",
                padding_top="8px",
                border_top="1px solid #374151",
            ),
            position="absolute",
            top="100%",
            left="50%",
            transform="translateX(-50%)",
            margin_top="32px",
            width="280px",
            background="rgba(17, 24, 39, 0.95)",
            backdrop_filter="blur(12px)",
            border="1px solid rgba(55, 65, 81, 0.5)",
            border_radius="12px",
            padding="16px 20px",
            box_shadow="0 8px 24px rgba(0, 0, 0, 0.4)",
            class_name="animate-slide-up",
        ),
        class_name="suspect-hub",
        position="relative",
        display="flex",
        flex_direction="column",
        align_items="center",
        cursor="pointer",
        on_click=InvestigationState.clear_selection,
    )
