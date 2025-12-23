"""UI Components for the Detective Board."""
from .suspect_hub import suspect_hub
from .actor_node import actor_node, actors_layer, actor_node_simple, polaroid_card
from .connection_lines import connection_lines_static
from .timeline_panel import timeline_panel
from .dossier_modal import dossier_modal
from .header_bar import header_bar

# V2 Components for Next-Gen Detective Board
from .actors import actors_layer_v2, primary_actor_hub
from .connection_lines_v2 import connection_lines_v2
from .timeline import timeline_panel_v2, event_dossier_modal
from .playback_controls import playback_controls, playback_stats
from .insights import insights_panel

__all__ = [
    # V1 Components
    "suspect_hub",
    "actor_node",
    "actors_layer",
    "actor_node_simple",
    "polaroid_card",
    "connection_lines_static",
    "timeline_panel",
    "dossier_modal",
    "header_bar",
    # V2 Components
    "actors_layer_v2",
    "primary_actor_hub",
    "connection_lines_v2",
    "timeline_panel_v2",
    "event_dossier_modal",
    "playback_controls",
    "playback_stats",
    "insights_panel",
]
