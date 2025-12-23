"""Research Dashboard - main entry point for deep research features."""

import reflex as rx
from ...state.research_state import ResearchState


def template_icon(template_id: rx.Var, is_selected: rx.Var) -> rx.Component:
    """Get icon component for template based on id."""
    icon_color = rx.cond(is_selected, "#60a5fa", "#9ca3af")
    return rx.cond(
        template_id == "investigative",
        rx.icon("search", size=20, color=icon_color),
        rx.cond(
            template_id == "market",
            rx.icon("trending-up", size=20, color=icon_color),
            rx.cond(
                template_id == "historical",
                rx.icon("book-open", size=20, color=icon_color),
                rx.icon("eye", size=20, color=icon_color),  # detective/default
            ),
        ),
    )


def template_card(template: dict) -> rx.Component:
    """Render a template selection card."""
    is_selected = ResearchState.selected_template == template["id"]
    is_available = template["available"]
    template_id = template["id"]

    return rx.box(
        rx.hstack(
            template_icon(template_id, is_selected),
            rx.vstack(
                rx.text(
                    template["name"],
                    font_size="14px",
                    font_weight="600",
                    color=rx.cond(is_available, "white", "#6b7280"),
                ),
                rx.text(
                    template["description"],
                    font_size="12px",
                    color="#9ca3af",
                ),
                align_items="start",
                gap="2px",
            ),
            gap="12px",
            align="start",
        ),
        padding="12px",
        border_radius="8px",
        border=rx.cond(
            is_selected,
            "2px solid #3b82f6",
            "1px solid rgba(55, 65, 81, 0.5)",
        ),
        background=rx.cond(
            is_selected,
            "rgba(59, 130, 246, 0.1)",
            "rgba(31, 41, 55, 0.3)",
        ),
        cursor=rx.cond(is_available, "pointer", "not-allowed"),
        opacity=rx.cond(is_available, "1", "0.5"),
        on_click=lambda: ResearchState.set_template(template_id),
        pointer_events=rx.cond(is_available, "auto", "none"),
        _hover={"background": rx.cond(is_available, "rgba(59, 130, 246, 0.15)", "")},
    )


def perspective_chip(perspective: dict) -> rx.Component:
    """Render a perspective toggle chip."""
    is_selected = ResearchState.selected_perspectives.contains(perspective["id"])

    return rx.box(
        rx.hstack(
            rx.text(
                perspective["name"],
                font_size="12px",
                color=rx.cond(is_selected, "white", "#9ca3af"),
            ),
            gap="6px",
            align="center",
        ),
        padding="6px 12px",
        border_radius="16px",
        background=rx.cond(
            is_selected,
            "#3b82f6",
            "rgba(31, 41, 55, 0.5)",
        ),
        border="1px solid rgba(55, 65, 81, 0.5)",
        cursor="pointer",
        on_click=lambda: ResearchState.toggle_perspective(perspective["id"]),
    )


def sidebar() -> rx.Component:
    """Left sidebar with templates and parameters."""
    return rx.box(
        rx.vstack(
            # Templates section
            rx.text(
                "Research Template",
                font_size="12px",
                font_weight="600",
                color="#9ca3af",
                text_transform="uppercase",
                letter_spacing="0.05em",
            ),
            rx.foreach(
                ResearchState.available_templates,
                template_card,
            ),
            rx.divider(margin_y="16px", border_color="rgba(55, 65, 81, 0.5)"),

            # Parameters section
            rx.text(
                "Parameters",
                font_size="12px",
                font_weight="600",
                color="#9ca3af",
                text_transform="uppercase",
                letter_spacing="0.05em",
            ),

            # Max searches
            rx.vstack(
                rx.text("Max Searches", font_size="12px", color="#9ca3af"),
                rx.select(
                    ["3", "5", "8", "10"],
                    value=ResearchState.max_searches.to_string(),
                    on_change=ResearchState.set_max_searches,
                    size="1",
                ),
                align_items="start",
                gap="4px",
                width="100%",
            ),

            # Granularity
            rx.vstack(
                rx.text("Depth", font_size="12px", color="#9ca3af"),
                rx.select(
                    ["quick", "standard", "deep"],
                    value=ResearchState.granularity,
                    on_change=ResearchState.set_granularity,
                    size="1",
                ),
                align_items="start",
                gap="4px",
                width="100%",
            ),

            rx.divider(margin_y="16px", border_color="rgba(55, 65, 81, 0.5)"),

            # Perspectives
            rx.text(
                "Analysis Perspectives",
                font_size="12px",
                font_weight="600",
                color="#9ca3af",
                text_transform="uppercase",
                letter_spacing="0.05em",
            ),
            rx.flex(
                rx.foreach(
                    ResearchState.perspective_options,
                    perspective_chip,
                ),
                wrap="wrap",
                gap="8px",
            ),

            rx.divider(margin_y="16px", border_color="rgba(55, 65, 81, 0.5)"),

            # Cache toggle
            rx.hstack(
                rx.switch(
                    checked=ResearchState.use_cache,
                    on_change=lambda _: ResearchState.toggle_cache(),
                    size="1",
                ),
                rx.text("Use cached results", font_size="12px", color="#9ca3af"),
                gap="8px",
            ),

            align_items="start",
            gap="12px",
            width="100%",
        ),
        width="280px",
        min_width="280px",
        background="rgba(17, 24, 39, 0.8)",
        border_right="1px solid rgba(55, 65, 81, 0.5)",
        padding="16px",
        height="calc(100vh - 60px)",
        overflow_y="auto",
    )


def progress_display() -> rx.Component:
    """Display research progress."""
    return rx.vstack(
        rx.heading(
            "Research in Progress",
            size="5",
            color="white",
        ),
        rx.progress(
            value=ResearchState.progress_int,
            max=100,
            width="100%",
            height="8px",
        ),
        rx.text(
            ResearchState.progress_message,
            font_size="14px",
            color="#9ca3af",
        ),
        rx.hstack(
            rx.spinner(size="2"),
            rx.text(
                ResearchState.phase,
                font_size="12px",
                color="#60a5fa",
                text_transform="capitalize",
            ),
            gap="8px",
        ),
        align="center",
        gap="16px",
        width="100%",
        max_width="600px",
        padding="40px",
    )


def new_research_form() -> rx.Component:
    """Form for starting new research."""
    return rx.vstack(
        rx.heading(
            "Start New Research",
            size="6",
            color="white",
            margin_bottom="24px",
        ),
        rx.box(
            rx.text(
                "Research Question",
                font_size="14px",
                font_weight="600",
                color="#9ca3af",
                margin_bottom="8px",
            ),
            rx.text_area(
                placeholder="Enter your research question or topic... (minimum 10 characters)",
                value=ResearchState.research_query,
                on_change=ResearchState.set_query,
                min_height="120px",
                width="100%",
                style={
                    "background": "rgba(31, 41, 55, 0.5)",
                    "border": "1px solid rgba(55, 65, 81, 0.5)",
                    "color": "white",
                },
            ),
            width="100%",
            max_width="800px",
        ),
        rx.hstack(
            rx.box(
                rx.text(
                    "Template:",
                    font_size="12px",
                    color="#6b7280",
                ),
                rx.badge(
                    ResearchState.selected_template,
                    color_scheme="blue",
                    size="2",
                ),
                display="flex",
                align_items="center",
                gap="8px",
            ),
            rx.spacer(),
            rx.button(
                rx.icon("play", size=18),
                rx.text("Start Research"),
                color_scheme="green",
                size="3",
                on_click=ResearchState.start_research,
                disabled=~ResearchState.can_start_research,
            ),
            width="100%",
            max_width="800px",
            margin_top="24px",
        ),
        # Error message
        rx.cond(
            ResearchState.error_message != "",
            rx.box(
                rx.hstack(
                    rx.icon("circle-alert", size=16, color="#ef4444"),
                    rx.text(
                        ResearchState.error_message,
                        font_size="14px",
                        color="#ef4444",
                    ),
                    rx.spacer(),
                    rx.icon(
                        "x",
                        size=16,
                        color="#ef4444",
                        cursor="pointer",
                        on_click=ResearchState.dismiss_error,
                    ),
                    width="100%",
                ),
                padding="12px",
                background="rgba(239, 68, 68, 0.1)",
                border="1px solid rgba(239, 68, 68, 0.3)",
                border_radius="8px",
                margin_top="16px",
                width="100%",
                max_width="800px",
            ),
        ),
        align="start",
        padding="40px",
    )


def get_finding_color(finding_type: rx.Var) -> rx.Component:
    """Get color scheme for finding type using rx.cond."""
    return rx.cond(
        finding_type == "actor", "blue",
        rx.cond(
            finding_type == "event", "green",
            rx.cond(
                finding_type == "relationship", "purple",
                rx.cond(
                    finding_type == "evidence", "yellow",
                    rx.cond(
                        finding_type == "pattern", "orange",
                        rx.cond(
                            finding_type == "gap", "red",
                            "gray"
                        )
                    )
                )
            )
        )
    )


def finding_card(finding: dict) -> rx.Component:
    """Render a finding card."""
    finding_type = finding["finding_type_display"]
    confidence = finding["confidence_percent"]
    summary = finding["display_summary"]
    temporal = finding["temporal_context"]

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    finding_type,
                    color_scheme=get_finding_color(finding_type),
                    size="1",
                ),
                rx.spacer(),
                rx.text(
                    confidence,
                    font_size="12px",
                    color="#9ca3af",
                ),
                width="100%",
            ),
            rx.text(
                summary,
                font_size="14px",
                color="white",
            ),
            rx.cond(
                temporal,
                rx.text(
                    temporal,
                    font_size="11px",
                    color="#6b7280",
                ),
                rx.fragment(),
            ),
            align_items="start",
            gap="8px",
            width="100%",
        ),
        padding="12px",
        background="rgba(31, 41, 55, 0.5)",
        border="1px solid rgba(55, 65, 81, 0.5)",
        border_radius="8px",
        cursor="pointer",
    )


def source_card(source: dict) -> rx.Component:
    """Render a source card."""
    title_display = source["title_display"]
    domain = source["domain"]
    cred_percent = source["credibility_percent"]
    cred_color = source["credibility_color"]

    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.text(
                    title_display,
                    font_size="13px",
                    color="white",
                    font_weight="500",
                ),
                rx.text(
                    domain,
                    font_size="11px",
                    color="#6b7280",
                ),
                align_items="start",
                gap="2px",
                flex="1",
            ),
            rx.box(
                rx.text(
                    cred_percent,
                    font_size="12px",
                    font_weight="600",
                    color=cred_color,
                ),
            ),
            width="100%",
            align="center",
        ),
        padding="10px",
        background="rgba(31, 41, 55, 0.3)",
        border="1px solid rgba(55, 65, 81, 0.3)",
        border_radius="6px",
    )


def perspective_panel(perspective: dict) -> rx.Component:
    """Render a perspective analysis panel."""
    type_title = perspective["type_title"]
    conf_display = perspective["confidence_display"]
    analysis_display = perspective["analysis_display"]

    return rx.box(
        rx.vstack(
            rx.hstack(
                rx.badge(
                    type_title,
                    color_scheme="blue",
                    variant="surface",
                ),
                rx.text(
                    conf_display,
                    font_size="11px",
                    color="#6b7280",
                ),
                width="100%",
                justify="between",
            ),
            rx.text(
                analysis_display,
                font_size="13px",
                color="#d1d5db",
                line_height="1.5",
            ),
            # Simplified: no nested foreach for insights to avoid Reflex var issues
            align_items="start",
            gap="12px",
            width="100%",
        ),
        padding="16px",
        background="rgba(31, 41, 55, 0.5)",
        border="1px solid rgba(55, 65, 81, 0.5)",
        border_radius="8px",
        margin_bottom="12px",
    )


def results_display() -> rx.Component:
    """Display research results."""
    return rx.vstack(
        # Header
        rx.hstack(
            rx.vstack(
                rx.heading(
                    ResearchState.current_session.get("title", "Research Results"),
                    size="5",
                    color="white",
                ),
                rx.text(
                    ResearchState.current_session.get("query", ""),
                    font_size="14px",
                    color="#9ca3af",
                ),
                align_items="start",
            ),
            rx.spacer(),
            rx.hstack(
                rx.badge(
                    f"{ResearchState.findings_count} findings",
                    color_scheme="blue",
                ),
                rx.badge(
                    f"{ResearchState.sources_count} sources",
                    color_scheme="green",
                ),
                rx.badge(
                    "Completed",
                    color_scheme="green",
                    variant="surface",
                ),
                gap="8px",
            ),
            width="100%",
            margin_bottom="24px",
        ),

        # Main results grid
        rx.flex(
            # Findings column
            rx.box(
                rx.text(
                    "Findings",
                    font_size="14px",
                    font_weight="600",
                    color="white",
                    margin_bottom="12px",
                ),
                rx.vstack(
                    rx.foreach(
                        ResearchState.display_findings,
                        finding_card,
                    ),
                    gap="8px",
                    width="100%",
                ),
                flex="1",
                padding_right="16px",
            ),

            # Sources column
            rx.box(
                rx.text(
                    "Sources",
                    font_size="14px",
                    font_weight="600",
                    color="white",
                    margin_bottom="12px",
                ),
                rx.vstack(
                    rx.foreach(
                        ResearchState.display_sources,
                        source_card,
                    ),
                    gap="6px",
                    width="100%",
                ),
                width="300px",
                min_width="300px",
            ),

            gap="24px",
            width="100%",
        ),

        align="start",
        width="100%",
        padding="24px",
    )


def perspectives_sidebar() -> rx.Component:
    """Right sidebar with expert perspectives."""
    return rx.box(
        rx.vstack(
            rx.text(
                "Expert Perspectives",
                font_size="14px",
                font_weight="600",
                color="white",
                margin_bottom="12px",
            ),
            rx.foreach(
                ResearchState.display_perspectives,
                perspective_panel,
            ),
            align_items="start",
            width="100%",
        ),
        width="350px",
        min_width="350px",
        background="rgba(17, 24, 39, 0.8)",
        border_left="1px solid rgba(55, 65, 81, 0.5)",
        padding="16px",
        height="calc(100vh - 60px)",
        overflow_y="auto",
    )


def header() -> rx.Component:
    """Header bar for research dashboard."""
    return rx.box(
        rx.hstack(
            rx.hstack(
                rx.icon("search", size=24, color="#60a5fa"),
                rx.text(
                    "Deep Research",
                    font_size="18px",
                    font_weight="700",
                    color="white",
                ),
                gap="12px",
                align="center",
            ),
            rx.spacer(),
            rx.hstack(
                rx.button(
                    rx.icon("arrow-left", size=16),
                    rx.text("Detective Board"),
                    variant="ghost",
                    color_scheme="gray",
                    on_click=rx.redirect("/detective-board"),
                ),
                rx.button(
                    rx.icon("plus", size=16),
                    rx.text("New Research"),
                    color_scheme="blue",
                    on_click=ResearchState.reset_to_new,
                ),
                gap="12px",
            ),
            width="100%",
            padding="12px 24px",
            justify="between",
        ),
        background="rgba(3, 7, 18, 0.95)",
        border_bottom="1px solid rgba(55, 65, 81, 0.5)",
        position="sticky",
        top="0",
        z_index="100",
    )


def main_content() -> rx.Component:
    """Main content area that switches based on state."""
    return rx.box(
        rx.cond(
            ResearchState.phase == "idle",
            new_research_form(),
            rx.cond(
                ResearchState.is_researching,
                rx.center(
                    progress_display(),
                    width="100%",
                    height="100%",
                ),
                rx.cond(
                    ResearchState.is_completed,
                    results_display(),
                    # Failed state
                    rx.center(
                        rx.vstack(
                            rx.icon("circle-alert", size=48, color="#ef4444"),
                            rx.heading("Research Failed", size="5", color="#ef4444"),
                            rx.text(
                                ResearchState.error_message,
                                color="#9ca3af",
                            ),
                            rx.button(
                                "Try Again",
                                color_scheme="blue",
                                on_click=ResearchState.reset_to_new,
                            ),
                            align="center",
                            gap="16px",
                        ),
                        width="100%",
                        height="100%",
                    ),
                ),
            ),
        ),
        flex="1",
        overflow_y="auto",
    )


def research_dashboard() -> rx.Component:
    """Main research dashboard page."""
    return rx.box(
        header(),
        rx.flex(
            sidebar(),
            main_content(),
            rx.cond(
                ResearchState.is_completed,
                perspectives_sidebar(),
            ),
            direction="row",
            height="calc(100vh - 60px)",
        ),
        min_height="100vh",
        background="#030712",
        color="white",
    )
