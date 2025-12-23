"""Detective Board - Reflex Application.

Main entry point for the Reflex app.
"""
import reflex as rx
from .pages.investigation_board import investigation_board
from .state import InvestigationState


# Global styles
style = {
    "font_family": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
}


def index() -> rx.Component:
    """Landing page that redirects to the investigation board."""
    return rx.fragment(
        rx.script(
            """
            window.location.href = '/detective-board';
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
