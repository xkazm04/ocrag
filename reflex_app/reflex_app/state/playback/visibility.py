"""Visibility utilities for the Detective Board.

Helper functions for calculating which actors, events, and connections
are visible at a given playback date.
"""
from typing import List, Set, Tuple


def get_visible_actor_ids_from_events(
    all_events: List[dict],
    current_date: str,
) -> Set[str]:
    """Get actor IDs that are mentioned in visible events.

    Args:
        all_events: List of all event dicts
        current_date: Current playback date (ISO format)

    Returns:
        Set of actor IDs mentioned in events at or before current_date
    """
    visible_ids = set()
    for event in all_events:
        event_date = event.get("date", "")
        if event_date and event_date <= current_date:
            for actor_id in event.get("actors_involved", []):
                visible_ids.add(actor_id)
    return visible_ids


def calculate_visible_events(
    all_events: List[dict],
    current_date: str,
    newly_revealed_ids: List[str],
) -> List[dict]:
    """Calculate which events are visible at current date.

    Args:
        all_events: List of all event dicts
        current_date: Current playback date (ISO format)
        newly_revealed_ids: List of event IDs that just became visible

    Returns:
        List of visible event dicts with is_new flag and precomputed values
    """
    if not current_date:
        return []

    visible = []
    for event in all_events:
        event_date = event.get("date", "")
        if event_date and event_date <= current_date:
            is_new = event.get("id", "") in newly_revealed_ids
            finding_type = event.get("finding_type", "event")
            title = event.get("title", "")
            visible.append({
                **event,
                "is_new": is_new,
                "finding_type_upper": finding_type.upper(),
                "title_truncated": title[:50] + "..." if len(title) > 50 else title,
            })
    return visible


def calculate_visible_actors(
    all_actors: List[dict],
    all_events: List[dict],
    current_date: str,
    newly_revealed_ids: List[str],
) -> List[dict]:
    """Calculate which actors are visible at current date.

    Args:
        all_actors: List of all actor dicts
        all_events: List of all event dicts
        current_date: Current playback date (ISO format)
        newly_revealed_ids: List of actor IDs that just became visible

    Returns:
        List of visible actor dicts with is_new flag
    """
    if not current_date:
        return []

    # Get actors mentioned in visible events
    event_actor_ids = get_visible_actor_ids_from_events(all_events, current_date)

    visible = []
    for actor in all_actors:
        first_date = actor.get("first_mentioned_date")
        actor_id = actor.get("id", "")

        # Visible if: has first_mentioned_date <= current OR in visible events
        is_visible = False
        if first_date and first_date <= current_date:
            is_visible = True
        elif actor_id in event_actor_ids:
            is_visible = True

        if is_visible:
            is_new = actor_id in newly_revealed_ids
            visible.append({**actor, "is_new": is_new})

    return visible


def calculate_visible_connections(
    all_connections: List[dict],
    visible_actor_ids: Set[str],
    newly_revealed_ids: List[str],
) -> List[dict]:
    """Calculate which connections are visible.

    Args:
        all_connections: List of all connection dicts
        visible_actor_ids: Set of visible actor IDs
        newly_revealed_ids: List of connection IDs that just became visible

    Returns:
        List of visible connection dicts with is_new flag
    """
    visible = []
    for conn in all_connections:
        source_id = conn.get("source_id", "")
        target_id = conn.get("target_id", "")

        if source_id in visible_actor_ids and target_id in visible_actor_ids:
            is_new = conn.get("id", "") in newly_revealed_ids
            visible.append({**conn, "is_new": is_new})
    return visible


def calculate_newly_revealed(
    all_actors: List[dict],
    all_events: List[dict],
    all_connections: List[dict],
    current_date: str,
    prev_actor_ids: Set[str],
    prev_event_ids: Set[str],
    prev_conn_ids: Set[str],
) -> Tuple[List[str], List[str], List[str], Set[str], Set[str], Set[str]]:
    """Calculate which items just became visible.

    Args:
        all_actors: List of all actor dicts
        all_events: List of all event dicts
        all_connections: List of all connection dicts
        current_date: Current playback date
        prev_actor_ids: Previously visible actor IDs
        prev_event_ids: Previously visible event IDs
        prev_conn_ids: Previously visible connection IDs

    Returns:
        Tuple of (new_actors, new_events, new_conns,
                  current_actor_ids, current_event_ids, current_conn_ids)
    """
    current_actor_ids: Set[str] = set()
    current_event_ids: Set[str] = set()
    current_conn_ids: Set[str] = set()

    # Events visible at current date
    for event in all_events:
        event_date = event.get("date", "")
        if event_date and event_date <= current_date:
            current_event_ids.add(event.get("id", ""))
            for actor_id in event.get("actors_involved", []):
                current_actor_ids.add(actor_id)

    # Actors by first_mentioned_date
    for actor in all_actors:
        first_date = actor.get("first_mentioned_date")
        if first_date and first_date <= current_date:
            current_actor_ids.add(actor.get("id", ""))

    # Connections where both endpoints visible
    for conn in all_connections:
        source_id = conn.get("source_id", "")
        target_id = conn.get("target_id", "")
        if source_id in current_actor_ids and target_id in current_actor_ids:
            current_conn_ids.add(conn.get("id", ""))

    # Find newly revealed items
    new_actors = list(current_actor_ids - prev_actor_ids)
    new_events = list(current_event_ids - prev_event_ids)
    new_conns = list(current_conn_ids - prev_conn_ids)

    return (new_actors, new_events, new_conns,
            current_actor_ids, current_event_ids, current_conn_ids)
