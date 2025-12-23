"""Playback state management for the Next-Gen Detective Board.

Main PlaybackState class with timeline playback, visibility computation,
and progressive reveal of actors, events, and connections.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Set
import reflex as rx

from ...models.research_types import BoardData, PerspectiveView
from ...lib.loader import load_research_json, transform_research_to_board_data
from .positioning import calculate_actor_positions, calculate_connection_paths
from .visibility import (
    calculate_visible_events,
    calculate_visible_actors,
    calculate_visible_connections,
    calculate_newly_revealed,
)


class PlaybackState(rx.State):
    """State for timeline playback and visibility control."""

    # Core playback state
    current_date: str = ""
    is_playing: bool = False
    playback_speed: float = 1.0
    progress_percent: float = 0.0
    is_loaded: bool = False

    # Board dimensions
    board_width: int = 2000
    board_height: int = 900

    # Selection state
    selected_actor_id: Optional[str] = None
    selected_event_id: Optional[str] = None
    hovered_actor_id: Optional[str] = None
    carousel_index: int = 0

    # Animation tracking
    _newly_revealed_actors: List[str] = []
    _newly_revealed_events: List[str] = []
    _newly_revealed_connections: List[str] = []
    _prev_visible_actor_ids: Set[str] = set()
    _prev_visible_event_ids: Set[str] = set()
    _prev_visible_conn_ids: Set[str] = set()

    # Stored data
    _case_name: str = ""
    _query: str = ""
    _timestamp: str = ""
    _primary_actor: Optional[dict] = None
    _all_actors: List[dict] = []
    _all_events: List[dict] = []
    _all_connections: List[dict] = []
    _all_perspectives: List[dict] = []
    _all_sources: List[dict] = []
    _earliest_date: str = ""
    _latest_date: str = ""
    _finding_count: int = 0
    _source_count: int = 0

    # Computed properties
    @rx.var
    def center_x(self) -> float:
        return self.board_width / 2

    @rx.var
    def center_y(self) -> float:
        return self.board_height / 2 - 100

    @rx.var
    def case_name(self) -> str:
        return self._case_name

    @rx.var
    def query(self) -> str:
        return self._query

    @rx.var
    def earliest_date(self) -> str:
        return self._earliest_date

    @rx.var
    def latest_date(self) -> str:
        return self._latest_date

    @rx.var
    def finding_count(self) -> int:
        return self._finding_count

    @rx.var
    def source_count(self) -> int:
        return self._source_count

    @rx.var
    def current_date_text(self) -> str:
        if not self.current_date:
            return ""
        try:
            dt = datetime.fromisoformat(self.current_date)
            return dt.strftime("%B %d, %Y")
        except ValueError:
            return self.current_date

    @rx.var
    def visible_events(self) -> List[dict]:
        return calculate_visible_events(
            self._all_events, self.current_date, self._newly_revealed_events
        )

    @rx.var
    def visible_actors(self) -> List[dict]:
        return calculate_visible_actors(
            self._all_actors, self._all_events,
            self.current_date, self._newly_revealed_actors
        )

    @rx.var
    def visible_connections(self) -> List[dict]:
        visible_ids = {a.get("id") for a in self.visible_actors}
        return calculate_visible_connections(
            self._all_connections, visible_ids, self._newly_revealed_connections
        )

    @rx.var
    def primary_actor_data(self) -> Optional[dict]:
        return self._primary_actor

    @rx.var
    def actor_positions(self) -> List[dict]:
        return calculate_actor_positions(
            self.visible_actors, self.center_x, self.center_y,
            self.board_width, self.board_height
        )

    @rx.var
    def connection_paths(self) -> List[dict]:
        return calculate_connection_paths(
            self.visible_connections, self.actor_positions,
            self._primary_actor, self.center_x, self.center_y
        )

    @rx.var
    def perspectives_data(self) -> List[PerspectiveView]:
        # Add precomputed values for Reflex rendering
        result = []
        for p in self._all_perspectives:
            analysis = p.get("analysis", "")
            truncated = analysis[:300] + "..." if len(analysis) > 300 else analysis
            result.append(PerspectiveView(
                type=p.get("type", ""),
                type_upper=p.get("type", "").upper(),
                analysis=analysis,
                analysis_truncated=truncated,
                insights=p.get("insights", []),
                recommendations=p.get("recommendations", []),
                warnings=p.get("warnings", []),
                confidence=p.get("confidence", 1.0),
                has_insights=len(p.get("insights", [])) > 0,
                has_recommendations=len(p.get("recommendations", [])) > 0,
                has_warnings=len(p.get("warnings", [])) > 0,
            ))
        return result

    @rx.var
    def sources_data(self) -> List[dict]:
        return self._all_sources

    @rx.var
    def timeline_years(self) -> List[str]:
        years = set()
        for event in self._all_events:
            date = event.get("date", "")
            if date and len(date) >= 4:
                years.add(date[:4])
        return sorted(list(years))

    @rx.var
    def current_event(self) -> Optional[dict]:
        visible = self.visible_events
        return visible[-1] if visible else None

    @rx.var
    def selected_event_data(self) -> Optional[dict]:
        if not self.selected_event_id:
            return None
        for event in self._all_events:
            if event.get("id") == self.selected_event_id:
                return event
        return None

    @rx.var
    def case_summary(self) -> dict:
        return {
            "total_actors": len(self._all_actors),
            "visible_actors": len(self.visible_actors),
            "total_events": len(self._all_events),
            "visible_events": len(self.visible_events),
            "total_connections": len(self._all_connections),
            "visible_connections": len(self.visible_connections),
            "finding_count": self._finding_count,
            "source_count": self._source_count,
            "progress": self.progress_percent,
        }

    # Event handlers
    async def load_research_data(self, file_path: str = "assets/data/ukraine_war_timeline.json"):
        """Load and initialize board data from JSON file."""
        try:
            raw_data = load_research_json(file_path)
            board_data = transform_research_to_board_data(raw_data)

            self._case_name = board_data.case_name
            self._query = board_data.query
            self._timestamp = board_data.timestamp
            self._primary_actor = board_data.primary_actor.model_dump() if board_data.primary_actor else None
            self._all_actors = [a.model_dump() for a in board_data.actors]
            self._all_events = [e.model_dump() for e in board_data.events]
            self._all_connections = [c.model_dump() for c in board_data.connections]
            self._all_perspectives = [p.model_dump() for p in board_data.perspectives]
            self._all_sources = [s.model_dump() for s in board_data.sources]
            self._earliest_date = board_data.date_range[0]
            self._latest_date = board_data.date_range[1]
            self._finding_count = board_data.finding_count
            self._source_count = board_data.source_count

            self.current_date = self._earliest_date
            self.progress_percent = 0.0
            self.is_loaded = True
            self._update_newly_revealed()
        except Exception as e:
            print(f"Error loading research data: {e}")
            self.is_loaded = False

    def play(self):
        self.is_playing = True

    def pause(self):
        self.is_playing = False

    def toggle_playback(self):
        self.is_playing = not self.is_playing

    def set_speed(self, speed: str):
        speed_map = {"1x": 1.0, "2x": 2.0, "5x": 5.0}
        self.playback_speed = speed_map.get(speed, 1.0)

    def seek(self, date: str):
        self.current_date = date
        self._update_progress()
        self._update_newly_revealed()

    def seek_by_percent(self, percent: float):
        if not self._earliest_date or not self._latest_date:
            return
        try:
            start = datetime.fromisoformat(self._earliest_date)
            end = datetime.fromisoformat(self._latest_date)
            days_offset = int((end - start).days * percent / 100)
            self.current_date = (start + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            self.progress_percent = percent
            self._update_newly_revealed()
        except ValueError:
            pass

    def seek_to_event(self, event_id: str):
        for event in self._all_events:
            if event.get("id") == event_id:
                self.seek(event.get("date", ""))
                break

    def tick(self):
        if not self.is_playing or not self.current_date or not self._latest_date:
            return
        try:
            current = datetime.fromisoformat(self.current_date)
            end = datetime.fromisoformat(self._latest_date)
            days_per_tick = int(30 * self.playback_speed)
            new_date = current + timedelta(days=days_per_tick)

            if new_date >= end:
                self.current_date = self._latest_date
                self.is_playing = False
                self.progress_percent = 100.0
            else:
                self.current_date = new_date.strftime("%Y-%m-%d")
                self._update_progress()
            self._update_newly_revealed()
        except ValueError:
            pass

    def reset_playback(self):
        self.current_date = self._earliest_date
        self.progress_percent = 0.0
        self.is_playing = False
        self._newly_revealed_actors = []
        self._newly_revealed_events = []
        self._newly_revealed_connections = []
        self._prev_visible_actor_ids = set()
        self._prev_visible_event_ids = set()
        self._prev_visible_conn_ids = set()

    def _update_progress(self):
        if not self._earliest_date or not self._latest_date:
            return
        try:
            start = datetime.fromisoformat(self._earliest_date)
            end = datetime.fromisoformat(self._latest_date)
            current = datetime.fromisoformat(self.current_date)
            total_days = (end - start).days
            if total_days > 0:
                self.progress_percent = min(100.0, ((current - start).days / total_days) * 100)
        except ValueError:
            pass

    def _update_newly_revealed(self):
        result = calculate_newly_revealed(
            self._all_actors, self._all_events, self._all_connections,
            self.current_date, self._prev_visible_actor_ids,
            self._prev_visible_event_ids, self._prev_visible_conn_ids
        )
        self._newly_revealed_actors = result[0]
        self._newly_revealed_events = result[1]
        self._newly_revealed_connections = result[2]
        self._prev_visible_actor_ids = result[3]
        self._prev_visible_event_ids = result[4]
        self._prev_visible_conn_ids = result[5]

    # Selection handlers
    def select_actor(self, actor_id: str):
        self.selected_actor_id = None if self.selected_actor_id == actor_id else actor_id

    def clear_selection(self):
        self.selected_actor_id = None

    def hover_actor(self, actor_id: str):
        self.hovered_actor_id = actor_id

    def unhover_actor(self):
        self.hovered_actor_id = None

    def select_event(self, event_id: str):
        self.selected_event_id = event_id

    def close_event(self):
        self.selected_event_id = None

    def navigate_carousel(self, direction: int):
        max_index = len(self.visible_events) - 1
        if max_index >= 0:
            self.carousel_index = max(0, min(self.carousel_index + direction, max_index))
