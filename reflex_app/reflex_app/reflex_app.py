"""Detective Board - Reflex Application.

Main entry point for the Reflex app.
"""
import reflex as rx
from .pages.investigation_board import investigation_board
from .pages.investigation_board_v2 import investigation_board_v2
from .pages.research.dashboard import research_dashboard
from .state import InvestigationState, PlaybackState
from .state.research_state import ResearchState


# Global styles
style = {
    "font_family": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
}


def index() -> rx.Component:
    """Landing page that redirects to the v2 board."""
    return rx.fragment(
        rx.script(
            """
            window.location.href = '/board-v2';
            """
        ),
        rx.center(
            rx.spinner(size="3"),
            rx.text("Loading Detective Board...", margin_top="16px", color="white"),
            flex_direction="column",
            height="100vh",
            background="#030712",
        ),
    )


# Create the app
app = rx.App(
    style=style,
    stylesheets=["/styles/detective_board.css"],
)

# Add pages
app.add_page(index, route="/")
app.add_page(investigation_board, route="/detective-board", title="Detective Board")
app.add_page(investigation_board_v2, route="/board-v2", title="Deep Research Board")
app.add_page(research_dashboard, route="/research", title="Deep Research")
