"""Primary actor hub component.

Central hub display for the primary actor on the detective board.
"""
import reflex as rx
from ...state import PlaybackState


def primary_actor_hub() -> rx.Component:
    """Central hub for the primary actor."""
    return rx.cond(
        PlaybackState.primary_actor_data != None,
        rx.box(
            # Outer rotating ring
            rx.box(
                width="200px",
                height="200px",
                border="2px dashed #dc2626",
                border_radius="50%",
                position="absolute",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                class_name="rotate-slow",
            ),
            # Center circle with silhouette
            rx.box(
                rx.icon("user", size=48, color="#9ca3af"),
                width="140px",
                height="140px",
                border_radius="50%",
                background="linear-gradient(135deg, #374151 0%, #1f2937 100%)",
                border="3px solid #dc2626",
                display="flex",
                align_items="center",
                justify_content="center",
                box_shadow="0 0 30px rgba(220, 38, 38, 0.3)",
            ),
            # Name card
            rx.box(
                rx.vstack(
                    rx.hstack(
                        rx.box(
                            width="8px",
                            height="8px",
                            border_radius="50%",
                            background="#dc2626",
                            class_name="pulse-glow",
                        ),
                        rx.text(
                            "PRIMARY ACTOR",
                            font_size="10px",
                            font_weight="700",
                            color="#dc2626",
                            letter_spacing="2px",
                        ),
                        gap="6px",
                        align="center",
                    ),
                    rx.text(
                        PlaybackState.primary_actor_data["name"],
                        font_size="16px",
                        font_weight="700",
                        color="white",
                    ),
                    rx.text(
                        PlaybackState.primary_actor_data["role"],
                        font_size="11px",
                        color="#9ca3af",
                    ),
                    align="center",
                    gap="4px",
                ),
                position="absolute",
                bottom="-80px",
                left="50%",
                transform="translateX(-50%)",
                background="rgba(17, 24, 39, 0.9)",
                border="1px solid rgba(75, 85, 99, 0.5)",
                border_radius="8px",
                padding="12px 16px",
                white_space="nowrap",
            ),
            position="relative",
            width="200px",
            height="200px",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.fragment(),
    )
