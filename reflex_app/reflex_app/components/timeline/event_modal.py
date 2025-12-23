"""Event dossier modal component.

Modal overlay for displaying detailed event information.
"""
import reflex as rx
from ...state import PlaybackState


def event_dossier_modal() -> rx.Component:
    """Modal overlay for event details."""
    return rx.cond(
        PlaybackState.selected_event_id != None,
        rx.box(
            # Backdrop
            rx.box(
                position="fixed",
                inset="0",
                background="rgba(0, 0, 0, 0.7)",
                backdrop_filter="blur(4px)",
                z_index="199",
                on_click=PlaybackState.close_event,
            ),
            # Modal content
            rx.box(
                rx.vstack(
                    # Header
                    rx.hstack(
                        rx.text(
                            "EVENT DETAILS",
                            font_size="12px",
                            font_weight="700",
                            color="#60a5fa",
                            letter_spacing="2px",
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.icon("x", size=18),
                            on_click=PlaybackState.close_event,
                            variant="ghost",
                            color_scheme="gray",
                            size="1",
                        ),
                        width="100%",
                        align="center",
                    ),
                    # Event title
                    rx.text(
                        PlaybackState.selected_event_data["title"],
                        font_size="18px",
                        font_weight="700",
                        color="white",
                    ),
                    # Date
                    rx.hstack(
                        rx.icon("calendar", size=14, color="#9ca3af"),
                        rx.text(
                            PlaybackState.selected_event_data["date_text"],
                            font_size="13px",
                            color="#9ca3af",
                        ),
                        gap="6px",
                        align="center",
                    ),
                    # Summary
                    rx.text(
                        PlaybackState.selected_event_data["summary"],
                        font_size="14px",
                        color="#d1d5db",
                        line_height="1.6",
                    ),
                    # Full content
                    rx.box(
                        rx.text(
                            PlaybackState.selected_event_data["content"],
                            font_size="13px",
                            color="#9ca3af",
                            line_height="1.5",
                        ),
                        background="rgba(17, 24, 39, 0.5)",
                        border_radius="8px",
                        padding="12px",
                        max_height="200px",
                        overflow_y="auto",
                    ),
                    # Jump to date button
                    rx.button(
                        rx.hstack(
                            rx.icon("clock", size=14),
                            rx.text("Jump to this date"),
                            gap="6px",
                        ),
                        on_click=lambda: PlaybackState.seek_to_event(
                            PlaybackState.selected_event_id
                        ),
                        variant="soft",
                        color_scheme="blue",
                        size="2",
                    ),
                    gap="16px",
                    align="start",
                    width="100%",
                ),
                position="fixed",
                left="50%",
                top="50%",
                transform="translate(-50%, -50%)",
                z_index="200",
                background="rgba(31, 41, 55, 0.95)",
                border="1px solid rgba(75, 85, 99, 0.5)",
                border_radius="12px",
                padding="24px",
                max_width="600px",
                width="90%",
                box_shadow="0 25px 50px rgba(0, 0, 0, 0.5)",
            ),
        ),
        rx.fragment(),
    )
