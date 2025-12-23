"""Dossier Modal component.

Displays detailed event information in a slide-up modal overlay.
Uses static data with reactive visibility.
"""
import reflex as rx
from ..state import InvestigationState
from ..lib.mock_data import investigation_data, get_actor_name


def _build_events_dict() -> dict:
    """Build a dict of event data keyed by event ID."""
    events_dict = {}
    for event in investigation_data.events:
        actors = [
            {
                "id": aid,
                "name": get_actor_name(aid),
                "is_suspect": aid == "suspect-1",
            }
            for aid in event.actors_involved
        ]
        events_dict[event.id] = {
            "id": event.id,
            "title": event.title,
            "date": event.date,
            "description": event.description,
            "type": event.type,
            "severity": event.severity,
            "location": event.location or "Unknown",
            "amount": event.amount or "",
            "actors": actors,
        }
    return events_dict


# Pre-calculate at module load time
_EVENTS_DICT = _build_events_dict()


def dossier_modal() -> rx.Component:
    """Render the dossier modal overlay when an event is expanded."""
    # Create a modal for each possible event (only one will be shown at a time)
    return rx.fragment(
        *[
            dossier_for_event(event_id, event_data)
            for event_id, event_data in _EVENTS_DICT.items()
        ]
    )


def dossier_for_event(event_id: str, event_data: dict) -> rx.Component:
    """Render a dossier modal for a specific event."""
    return rx.cond(
        InvestigationState.expanded_event == event_id,
        rx.box(
            # Backdrop
            rx.box(
                position="absolute",
                inset="0",
                background="rgba(0, 0, 0, 0.8)",
                on_click=InvestigationState.close_dossier,
            ),
            # Modal content
            rx.box(
                # Classification stamp
                rx.box(
                    rx.text(
                        "TOP SECRET",
                        font_size="10px",
                        font_weight="bold",
                        letter_spacing="2px",
                        color="white",
                    ),
                    position="absolute",
                    top="12px",
                    right="24px",
                    padding="4px 12px",
                    background="#dc2626",
                    transform="rotate(3deg)",
                ),
                # Close button
                rx.button(
                    rx.icon("x", size=20),
                    on_click=InvestigationState.close_dossier,
                    position="absolute",
                    top="16px",
                    left="16px",
                    variant="ghost",
                    color_scheme="gray",
                    size="2",
                ),
                # Header
                rx.vstack(
                    rx.text(
                        "EVENT DOSSIER",
                        font_size="10px",
                        font_weight="bold",
                        color="#ef4444",
                        letter_spacing="2px",
                    ),
                    rx.text(
                        event_data["title"],
                        font_size="24px",
                        font_weight="800",
                        color="white",
                    ),
                    rx.text(
                        event_data["date"],
                        font_size="14px",
                        color="#9ca3af",
                    ),
                    align="center",
                    padding_top="32px",
                    margin_bottom="24px",
                ),
                # Content grid
                rx.hstack(
                    # Left column - Actors
                    rx.vstack(
                        rx.text(
                            "ACTORS INVOLVED",
                            font_size="10px",
                            font_weight="bold",
                            color="#6b7280",
                            letter_spacing="1px",
                        ),
                        *[
                            actor_badge_static(actor)
                            for actor in event_data["actors"]
                        ],
                        align="start",
                        gap="8px",
                        flex="1",
                        padding="16px",
                        background="rgba(31, 41, 55, 0.5)",
                        border_radius="8px",
                    ),
                    # Middle column - Evidence
                    rx.vstack(
                        rx.text(
                            "EVIDENCE",
                            font_size="10px",
                            font_weight="bold",
                            color="#6b7280",
                            letter_spacing="1px",
                        ),
                        rx.vstack(
                            evidence_item("Document A-127", "document"),
                            evidence_item("Wire Transfer Record", "file"),
                            evidence_item("Surveillance Photo", "image"),
                            evidence_item("Audio Recording", "audio"),
                            gap="8px",
                            width="100%",
                        ),
                        align="start",
                        gap="8px",
                        flex="1",
                        padding="16px",
                        background="rgba(31, 41, 55, 0.5)",
                        border_radius="8px",
                    ),
                    # Right column - Details
                    rx.vstack(
                        rx.text(
                            "DETAILS",
                            font_size="10px",
                            font_weight="bold",
                            color="#6b7280",
                            letter_spacing="1px",
                        ),
                        rx.vstack(
                            detail_row("Type", event_data["type"]),
                            detail_row("Severity", event_data["severity"]),
                            detail_row("Location", event_data["location"]),
                            detail_row("Amount", event_data["amount"]) if event_data["amount"] else rx.fragment(),
                            gap="12px",
                            width="100%",
                        ),
                        rx.box(
                            rx.text(
                                "Description",
                                font_size="10px",
                                color="#6b7280",
                                margin_bottom="4px",
                            ),
                            rx.text(
                                event_data["description"],
                                font_size="12px",
                                color="#e5e7eb",
                                line_height="1.5",
                            ),
                            margin_top="16px",
                        ),
                        align="start",
                        gap="8px",
                        flex="1",
                        padding="16px",
                        background="rgba(31, 41, 55, 0.5)",
                        border_radius="8px",
                    ),
                    gap="16px",
                    width="100%",
                    align="stretch",
                ),
                width="100%",
                max_width="1000px",
                max_height="70vh",
                background="linear-gradient(145deg, #1f2937 0%, #111827 100%)",
                border="1px solid rgba(75, 85, 99, 0.5)",
                border_radius="16px 16px 0 0",
                padding="24px",
                overflow_y="auto",
                position="relative",
            ),
            position="fixed",
            inset="0",
            z_index="200",
            display="flex",
            align_items="flex-end",
            justify_content="center",
            key=f"dossier-{event_id}",
        ),
        rx.fragment(),
    )


def actor_badge_static(actor: dict) -> rx.Component:
    """Render a badge for an actor involved in the event."""
    return rx.button(
        rx.hstack(
            rx.box(
                width="6px",
                height="6px",
                border_radius="50%",
                background="#ef4444" if actor["is_suspect"] else "#3b82f6",
            ),
            rx.text(
                actor["name"],
                font_size="12px",
            ),
            gap="6px",
            align="center",
        ),
        variant="outline",
        size="1",
        on_click=lambda aid=actor["id"]: InvestigationState.highlight_actors_from_event([aid]),
    )


def evidence_item(name: str, evidence_type: str) -> rx.Component:
    """Render an evidence item."""
    icon_map = {
        "document": "file-text",
        "file": "file",
        "image": "image",
        "audio": "volume-2",
    }
    icon_name = icon_map.get(evidence_type, "file")

    return rx.hstack(
        rx.icon(icon_name, size=14, color="#9ca3af"),
        rx.text(
            name,
            font_size="12px",
            color="#e5e7eb",
        ),
        gap="8px",
        align="center",
        padding="8px 12px",
        background="rgba(17, 24, 39, 0.5)",
        border_radius="6px",
        width="100%",
        cursor="pointer",
        _hover={
            "background": "rgba(31, 41, 55, 0.8)",
        },
    )


def detail_row(label: str, value: str) -> rx.Component:
    """Render a detail row with label and value."""
    return rx.hstack(
        rx.text(
            label,
            font_size="11px",
            color="#6b7280",
            min_width="80px",
        ),
        rx.text(
            value,
            font_size="12px",
            color="#e5e7eb",
            font_weight="500",
            text_transform="capitalize",
        ),
        gap="8px",
        width="100%",
    )
