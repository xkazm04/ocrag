"""State management for the Investigation Board.

Handles all reactive state and computed properties including
the elliptical actor positioning algorithm.
"""
import math
from typing import Optional
import reflex as rx

from ..lib.mock_data import investigation_data, get_actor_by_id


class InvestigationState(rx.State):
    """Central state for the Investigation Board."""

    # Selection state
    selected_actor_id: Optional[str] = None
    hovered_actor_id: Optional[str] = None
    expanded_event: Optional[str] = None  # Event ID for dossier modal

    # Board dimensions
    board_width: int = 2000
    board_height: int = 900

    # Carousel state
    carousel_index: int = 0

    # -------------------------
    # Computed properties
    # -------------------------

    @rx.var
    def center_x(self) -> float:
        """Center X coordinate."""
        return self.board_width / 2

    @rx.var
    def center_y(self) -> float:
        """Center Y coordinate (offset up for metadata card)."""
        return self.board_height / 2 - 100

    @rx.var
    def suspect_position(self) -> dict:
        """Position for the central suspect hub."""
        return {"x": self.center_x, "y": self.center_y}

    @rx.var
    def actor_positions(self) -> list[dict]:
        """Calculate elliptical positions for all actors.

        Returns a list of dicts with actor_id, x, y, angle, ring for each actor.
        Uses priority ordering: Top > Left/Right > Bottom.
        """
        positions = []
        actors = investigation_data.actors

        # Radii for the rings - wide horizontal spread
        inner_radius_x = 520
        inner_radius_y = 240
        outer_radius_x = 820
        outer_radius_y = 300

        def generate_slots(radius_x: float, radius_y: float, count: int, ring: int) -> list[dict]:
            """Generate position slots ordered by priority."""
            slots = []
            for i in range(count):
                # Start from top (-PI/2) and go clockwise
                angle = (math.pi * 2 * i) / count - math.pi / 2

                # Calculate priority: lower is better (filled first)
                normalized_angle = (angle + math.pi * 2) % (math.pi * 2)

                if 5 * math.pi / 4 <= normalized_angle <= 7 * math.pi / 4:
                    # Top quadrant (270 +/- 45) - highest priority
                    priority = 0
                elif 3 * math.pi / 4 <= normalized_angle < 5 * math.pi / 4:
                    # Left quadrant - high priority
                    priority = 1
                elif (0 <= normalized_angle < math.pi / 4) or normalized_angle > 7 * math.pi / 4:
                    # Right quadrant - high priority
                    priority = 1
                else:
                    # Bottom quadrant - lowest priority
                    priority = 2

                slots.append({
                    "angle": angle,
                    "priority": priority,
                    "ring": ring,
                    "radius_x": radius_x,
                    "radius_y": radius_y,
                })
            return slots

        # Generate slots from both rings (8 slots each)
        inner_slots = generate_slots(inner_radius_x, inner_radius_y, 8, 1)
        outer_slots = generate_slots(outer_radius_x, outer_radius_y, 8, 2)

        # Combine and sort by priority
        all_slots = inner_slots + outer_slots
        for idx, slot in enumerate(all_slots):
            slot["original_index"] = idx

        # Sort: priority first, then ring, then original index
        all_slots.sort(key=lambda s: (s["priority"], s["ring"], s["original_index"]))

        # Manual position overrides for specific actors
        manual_overrides = {
            "actor-4": {"angle_offset": -0.5, "radius_multiplier": 0.95, "ring": 2},
            "actor-1": {"angle_offset": 0.4, "radius_multiplier": 0.95, "ring": 2},
        }

        # Assign actors to slots
        for index, actor in enumerate(actors):
            if index >= len(all_slots):
                break

            slot = all_slots[index]
            override = manual_overrides.get(actor.id, {})

            radius_x = slot["radius_x"]
            radius_y = slot["radius_y"]
            angle = slot["angle"]
            ring = slot["ring"]

            # Apply manual overrides if exists
            if "angle_offset" in override:
                angle += override["angle_offset"]
            if "radius_multiplier" in override:
                radius_x *= override["radius_multiplier"]
                radius_y *= override["radius_multiplier"]
            if "ring" in override:
                ring = override["ring"]

            x = self.center_x + math.cos(angle) * radius_x
            y = self.center_y + math.sin(angle) * radius_y

            positions.append({
                "actor_id": actor.id,
                "x": x,
                "y": y,
                "angle": angle,
                "ring": ring,
                "index": index,
            })

        return positions

    @rx.var
    def actors_data(self) -> list[dict]:
        """Get all actors as serializable dicts."""
        return [actor.model_dump() for actor in investigation_data.actors]

    @rx.var
    def primary_suspect_data(self) -> dict:
        """Get primary suspect as serializable dict."""
        return investigation_data.primary_suspect.model_dump()

    @rx.var
    def connections_data(self) -> list[dict]:
        """Get all connections as serializable dicts."""
        return [conn.model_dump() for conn in investigation_data.connections]

    @rx.var
    def primary_connections(self) -> list[dict]:
        """Get connections involving the primary suspect."""
        return [
            conn.model_dump()
            for conn in investigation_data.connections
            if conn.source_id == "suspect-1" or conn.target_id == "suspect-1"
        ]

    @rx.var
    def secondary_connections(self) -> list[dict]:
        """Get connections between actors (not involving suspect)."""
        return [
            conn.model_dump()
            for conn in investigation_data.connections
            if conn.source_id != "suspect-1" and conn.target_id != "suspect-1"
        ]

    @rx.var
    def events_data(self) -> list[dict]:
        """Get all timeline events as serializable dicts."""
        return [event.model_dump() for event in investigation_data.events]

    @rx.var
    def sorted_events(self) -> list[dict]:
        """Get events sorted by date (newest first)."""
        events = investigation_data.events.copy()
        events.sort(key=lambda e: e.date, reverse=True)
        return [event.model_dump() for event in events]

    @rx.var
    def timeline_markers_data(self) -> list[dict]:
        """Get timeline markers as serializable dicts."""
        return [marker.model_dump() for marker in investigation_data.timeline]

    @rx.var
    def case_summary(self) -> dict:
        """Get case summary stats."""
        return investigation_data.summary.model_dump()

    @rx.var
    def case_info(self) -> dict:
        """Get basic case info."""
        return {
            "case_id": investigation_data.case_id,
            "case_name": investigation_data.case_name,
            "case_code": investigation_data.case_code,
            "status": investigation_data.status,
            "priority": investigation_data.priority,
        }

    @rx.var
    def current_event(self) -> Optional[dict]:
        """Get the currently expanded event for dossier."""
        if not self.expanded_event:
            return None
        for event in investigation_data.events:
            if event.id == self.expanded_event:
                return event.model_dump()
        return None

    # -------------------------
    # Event handlers
    # -------------------------

    def select_actor(self, actor_id: str):
        """Toggle actor selection."""
        if self.selected_actor_id == actor_id:
            self.selected_actor_id = None
        else:
            self.selected_actor_id = actor_id

    def clear_selection(self):
        """Clear actor selection."""
        self.selected_actor_id = None

    def hover_actor(self, actor_id: str):
        """Set hovered actor."""
        self.hovered_actor_id = actor_id

    def unhover_actor(self):
        """Clear hovered actor."""
        self.hovered_actor_id = None

    def open_dossier(self, event_id: str):
        """Open dossier modal for an event."""
        self.expanded_event = event_id

    def close_dossier(self):
        """Close dossier modal."""
        self.expanded_event = None

    def navigate_carousel(self, direction: int):
        """Navigate the timeline carousel."""
        max_index = len(investigation_data.events) - 1
        new_index = self.carousel_index + direction
        self.carousel_index = max(0, min(new_index, max_index))

    def highlight_actors_from_event(self, actor_ids: list[str]):
        """Highlight actors from a dossier event."""
        if actor_ids:
            first_actor = actor_ids[0]
            if first_actor == "suspect-1":
                self.selected_actor_id = None
            else:
                self.selected_actor_id = first_actor

    def is_actor_highlighted(self, actor_id: str) -> bool:
        """Check if an actor should be highlighted based on selection."""
        if not self.selected_actor_id:
            return False
        if actor_id == self.selected_actor_id:
            return True
        # Check if connected to selected actor
        for conn in investigation_data.connections:
            if (conn.source_id == self.selected_actor_id and conn.target_id == actor_id) or \
               (conn.target_id == self.selected_actor_id and conn.source_id == actor_id):
                return True
        return False
