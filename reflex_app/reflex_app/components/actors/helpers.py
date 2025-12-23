"""Helper functions for actor components."""


def get_initials(name: str) -> str:
    """Get initials from a name."""
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    return name[:2].upper() if name else "??"


def get_risk_color(risk_level: str) -> str:
    """Get color for risk level."""
    colors = {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#3b82f6",
        "minimal": "#22c55e",
    }
    return colors.get(risk_level, "#6b7280")
