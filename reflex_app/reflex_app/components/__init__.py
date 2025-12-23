"""UI Components for the Detective Board."""
from .suspect_hub import suspect_hub
from .actor_node import actor_node, actors_layer, actor_node_simple, polaroid_card
from .connection_lines import connection_lines_static
from .timeline_panel import timeline_panel
from .dossier_modal import dossier_modal
from .header_bar import header_bar

__all__ = [
    "suspect_hub",
    "actor_node",
    "actors_layer",
    "actor_node_simple",
    "polaroid_card",
    "connection_lines_static",
    "timeline_panel",
    "dossier_modal",
    "header_bar",
]
