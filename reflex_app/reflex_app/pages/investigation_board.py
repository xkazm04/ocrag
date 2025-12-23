"""Investigation Board page.

Main page that assembles all components to create the detective board visualization.
"""
import reflex as rx
from ..state import InvestigationState
from ..components.header_bar import header_bar
from ..components.suspect_hub import suspect_hub
from ..components.actor_node import actors_layer_static
from ..components.connection_lines import connection_lines_static
from ..components.timeline_panel import timeline_panel
from ..components.dossier_modal import dossier_modal


def investigation_board() -> rx.Component:
    """Render the complete investigation board page."""
    return rx.box(
        # Cork board background
        rx.box(
            class_name="cork-board",
            position="absolute",
            inset="0",
        ),
        # Header bar
        header_bar(),
        # Main board container
        rx.box(
            rx.box(
                # Connection lines SVG layer (behind everything)
                connection_lines_static(),
                # Central suspect hub
                rx.box(
                    suspect_hub(),
                    position="absolute",
                    left="50%",
                    top="350px",
                    transform="translate(-50%, -50%)",
                    z_index="20",
                ),
                # Actor nodes (static rendering)
                actors_layer_static(),
                position="relative",
                width="2000px",
                height="900px",
            ),
            position="absolute",
            inset="0",
            display="flex",
            align_items="center",
            justify_content="center",
            padding_top="80px",
            padding_bottom="160px",
            overflow="auto",
        ),
        # Legend panels
        legend_panel_left(),
        legend_panel_right(),
        # Timeline panel
        timeline_panel(),
        # Dossier modal (conditional)
        dossier_modal(),
        # Page container styles
        height="100vh",
        width="100vw",
        background="#030712",
        color="white",
        overflow="hidden",
        position="relative",
    )


def legend_panel_left() -> rx.Component:
    """Connection types legend on the left side."""
    connection_types = [
        {"color": "#22c55e", "label": "Financial"},
        {"color": "#3b82f6", "label": "Travel"},
        {"color": "#f97316", "label": "Business"},
        {"color": "#a855f7", "label": "Communication"},
        {"color": "#ec4899", "label": "Personal"},
        {"color": "#ef4444", "label": "Criminal"},
    ]

    return rx.box(
        rx.text(
            "CONNECTIONS",
            class_name="legend-title",
        ),
        rx.vstack(
            *[
                rx.hstack(
                    rx.box(
                        width="12px",
                        height="2px",
                        border_radius="1px",
                        background=item["color"],
                    ),
                    rx.text(
                        item["label"],
                        font_size="10px",
                        color="#9ca3af",
                    ),
                    gap="8px",
                    align="center",
                )
                for item in connection_types
            ],
            gap="6px",
        ),
        # Note about red string mode
        rx.box(
            rx.text(
                "Red String Mode",
                font_size="9px",
                color="#6b7280",
                font_style="italic",
            ),
            margin_top="12px",
            padding_top="8px",
            border_top="1px solid rgba(55, 65, 81, 0.5)",
        ),
        rx.hstack(
            rx.box(
                width="12px",
                height="2px",
                border_radius="1px",
                background="#dc2626",
            ),
            rx.text(
                "All Connections",
                font_size="10px",
                color="#f87171",
            ),
            gap="8px",
            align="center",
        ),
        class_name="legend-panel legend-panel-left animate-fade-in",
    )


def legend_panel_right() -> rx.Component:
    """Risk levels legend on the right side."""
    risk_levels = [
        {"color": "#ef4444", "label": "Critical"},
        {"color": "#f97316", "label": "High"},
        {"color": "#eab308", "label": "Medium"},
        {"color": "#3b82f6", "label": "Low"},
        {"color": "#22c55e", "label": "Minimal"},
    ]

    return rx.box(
        rx.text(
            "RISK LEVELS",
            class_name="legend-title",
        ),
        rx.vstack(
            *[
                rx.hstack(
                    rx.box(
                        width="8px",
                        height="8px",
                        border_radius="50%",
                        background=item["color"],
                    ),
                    rx.text(
                        item["label"],
                        font_size="10px",
                        color="#9ca3af",
                    ),
                    gap="8px",
                    align="center",
                )
                for item in risk_levels
            ],
            gap="6px",
        ),
        class_name="legend-panel legend-panel-right animate-fade-in",
    )
