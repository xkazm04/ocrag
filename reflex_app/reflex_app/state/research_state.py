"""State management for Deep Research functionality."""

from typing import Optional, List, Dict, Any
from enum import Enum
import reflex as rx
import httpx
import json


class ResearchPhase(str, Enum):
    """Research session phases."""
    IDLE = "idle"
    CONFIGURING = "configuring"
    SEARCHING = "searching"
    ASSESSING = "assessing"
    EXTRACTING = "extracting"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


# API base URL - configurable
API_BASE_URL = "http://localhost:8000/api/research"


class ResearchState(rx.State):
    """
    Central state for research operations.

    Manages:
    - Research session lifecycle
    - Template and parameter configuration
    - Progress tracking
    - Results display
    """

    # Current session
    current_session_id: Optional[str] = None
    current_session: Dict[str, Any] = {}

    # Configuration
    selected_template: str = "investigative"
    research_query: str = ""

    # Parameters
    max_searches: int = 5
    max_sources_per_search: int = 10
    granularity: str = "standard"
    selected_perspectives: List[str] = ["historical", "economic", "political"]
    use_cache: bool = True

    # Progress
    phase: str = "idle"
    progress_percent: float = 0.0
    progress_message: str = ""

    # Results
    findings: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []
    perspectives: List[Dict[str, Any]] = []

    # History
    past_sessions: List[Dict[str, Any]] = []

    # UI state
    show_template_modal: bool = False
    show_parameters_modal: bool = False
    selected_finding_id: Optional[str] = None
    error_message: str = ""

    # -------------------------
    # Computed Properties
    # -------------------------

    @rx.var
    def progress_int(self) -> int:
        """Progress as integer for rx.progress component."""
        return int(self.progress_percent)

    @rx.var
    def available_templates(self) -> List[Dict[str, Any]]:
        """Get available research templates."""
        return [
            {
                "id": "investigative",
                "name": "Investigative Research",
                "description": "Deep investigative journalism style research with actor and relationship analysis",
                "icon": "search",
                "available": True,
            },
            {
                "id": "market",
                "name": "Market Research",
                "description": "Competitive and market analysis",
                "icon": "trending-up",
                "available": False,
            },
            {
                "id": "historical",
                "name": "Historical Research",
                "description": "Historical event analysis and pattern recognition",
                "icon": "book-open",
                "available": False,
            },
            {
                "id": "detective",
                "name": "Detective/OSINT",
                "description": "Open source intelligence gathering",
                "icon": "eye",
                "available": False,
            },
        ]

    @rx.var
    def perspective_options(self) -> List[Dict[str, Any]]:
        """Get available analysis perspectives."""
        return [
            {"id": "historical", "name": "Historical", "icon": "history"},
            {"id": "political", "name": "Political", "icon": "landmark"},
            {"id": "economic", "name": "Economic", "icon": "dollar-sign"},
            {"id": "psychological", "name": "Psychological", "icon": "brain"},
            {"id": "military", "name": "Military/Strategic", "icon": "shield"},
        ]

    @rx.var
    def is_researching(self) -> bool:
        """Check if research is in progress."""
        return self.phase in ["searching", "assessing", "extracting", "analyzing"]

    @rx.var
    def is_completed(self) -> bool:
        """Check if research is completed."""
        return self.phase == "completed"

    @rx.var
    def high_credibility_sources(self) -> List[Dict[str, Any]]:
        """Get sources with high credibility scores."""
        return [
            s for s in self.sources
            if s.get("credibility_score", 0) >= 0.7
        ]

    @rx.var
    def findings_by_type(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group findings by type."""
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for f in self.findings:
            ftype = f.get("finding_type", "other")
            if ftype not in grouped:
                grouped[ftype] = []
            grouped[ftype].append(f)
        return grouped

    @rx.var
    def findings_count(self) -> int:
        """Total number of findings."""
        return len(self.findings)

    @rx.var
    def display_findings(self) -> List[Dict[str, Any]]:
        """Findings with precomputed display values."""
        result = []
        for f in self.findings:
            conf = f.get("confidence_score", 0.5)
            content = f.get("content", "")
            summary = f.get("summary", content[:100] if content else "")
            finding_type = f.get("finding_type", "other")
            temporal = f.get("temporal_context", "")
            result.append({
                **f,
                "confidence_percent": f"{int(conf * 100)}%",
                "display_summary": summary,
                "finding_type_display": finding_type,
                "temporal_context": temporal,
            })
        return result

    @rx.var
    def sources_count(self) -> int:
        """Total number of sources."""
        return len(self.sources)

    @rx.var
    def display_sources(self) -> List[Dict[str, Any]]:
        """Sources with precomputed display values."""
        result = []
        for s in self.sources:
            cred = s.get("credibility_score", 0)
            title = s.get("title", s.get("url", ""))
            title_short = title[:50] if title else ""
            # Determine color based on credibility
            if cred >= 0.7:
                color = "#22c55e"
            elif cred >= 0.5:
                color = "#eab308"
            else:
                color = "#ef4444"
            result.append({
                **s,
                "title_display": title_short,
                "credibility_percent": f"{int(cred * 100)}%",
                "credibility_color": color,
            })
        return result

    @rx.var
    def display_perspectives(self) -> List[Dict[str, Any]]:
        """Perspectives with precomputed display values."""
        result = []
        for p in self.perspectives:
            ptype = p.get("perspective_type", "")
            conf = p.get("confidence", 0.5)
            analysis = p.get("analysis_text", "")
            insights = p.get("key_insights", [])
            result.append({
                **p,
                "type_title": ptype.title() if ptype else "",
                "confidence_display": f"{int(conf * 100)}% confidence",
                "analysis_display": analysis[:200] + "..." if len(analysis) > 200 else analysis,
                "insights_count": len(insights),
            })
        return result

    @rx.var
    def can_start_research(self) -> bool:
        """Check if we can start research."""
        return len(self.research_query.strip()) >= 10 and self.phase == "idle"

    @rx.var
    def parameters_dict(self) -> Dict[str, Any]:
        """Get parameters as dictionary."""
        return {
            "max_searches": self.max_searches,
            "max_sources_per_search": self.max_sources_per_search,
            "granularity": self.granularity,
            "perspectives": self.selected_perspectives,
            "use_cache": self.use_cache,
        }

    # -------------------------
    # Event Handlers
    # -------------------------

    def set_template(self, template_id: str):
        """Set the research template."""
        self.selected_template = template_id
        self.show_template_modal = False

    def set_query(self, query: str):
        """Set the research query."""
        self.research_query = query

    def set_max_searches(self, value: str):
        """Set max searches parameter."""
        try:
            self.max_searches = int(value)
        except ValueError:
            pass

    def set_granularity(self, value: str):
        """Set granularity parameter."""
        self.granularity = value

    def toggle_perspective(self, perspective_id: str):
        """Toggle a perspective on/off."""
        if perspective_id in self.selected_perspectives:
            self.selected_perspectives = [
                p for p in self.selected_perspectives if p != perspective_id
            ]
        else:
            self.selected_perspectives = self.selected_perspectives + [perspective_id]

    def toggle_cache(self):
        """Toggle cache usage."""
        self.use_cache = not self.use_cache

    def toggle_template_modal(self):
        """Toggle template selection modal."""
        self.show_template_modal = not self.show_template_modal

    def toggle_parameters_modal(self):
        """Toggle parameters modal."""
        self.show_parameters_modal = not self.show_parameters_modal

    def reset_to_new(self):
        """Reset state for a new research session."""
        self.phase = "idle"
        self.current_session_id = None
        self.current_session = {}
        self.research_query = ""
        self.findings = []
        self.sources = []
        self.perspectives = []
        self.progress_percent = 0.0
        self.progress_message = ""
        self.error_message = ""

    async def start_research(self):
        """Start a new research session."""
        if not self.research_query.strip():
            self.error_message = "Please enter a research query"
            return

        self.phase = "searching"
        self.progress_percent = 0.0
        self.progress_message = "Starting research..."
        self.findings = []
        self.sources = []
        self.perspectives = []
        self.error_message = ""

        # Build request
        request_data = {
            "query": self.research_query,
            "template_type": self.selected_template,
            "parameters": self.parameters_dict,
            "workspace_id": "default",
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{API_BASE_URL}/start",
                    json=request_data,
                ) as response:
                    async for line in response.aiter_lines():
                        if line and line.startswith("data: "):
                            try:
                                progress = json.loads(line[6:])
                                self._update_progress(progress)
                                yield  # Yield to update UI
                            except json.JSONDecodeError:
                                continue

        except httpx.TimeoutException:
            self.phase = "failed"
            self.error_message = "Request timed out. Please try again."
        except httpx.ConnectError:
            self.phase = "failed"
            self.error_message = "Cannot connect to research API. Is the backend running?"
        except Exception as e:
            self.phase = "failed"
            self.error_message = f"Error: {str(e)}"

    def _update_progress(self, progress: Dict[str, Any]):
        """Update state from progress event."""
        self.progress_message = progress.get("message", "")
        self.progress_percent = progress.get("progress", 0)

        status = progress.get("status", "")
        if status == "searching":
            self.phase = "searching"
        elif status == "assessing":
            self.phase = "assessing"
        elif status == "extracting":
            self.phase = "extracting"
        elif status == "analyzing":
            self.phase = "analyzing"
        elif status == "completed":
            self.phase = "completed"
            self.current_session_id = progress.get("session_id")
        elif status == "failed":
            self.phase = "failed"
            self.error_message = progress.get("message", "Research failed")

    async def fetch_results(self):
        """Fetch research results from backend."""
        if not self.current_session_id:
            return

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch session details
                response = await client.get(
                    f"{API_BASE_URL}/sessions/{self.current_session_id}"
                )
                if response.status_code == 200:
                    self.current_session = response.json()

                # Fetch findings
                response = await client.get(
                    f"{API_BASE_URL}/sessions/{self.current_session_id}/findings"
                )
                if response.status_code == 200:
                    self.findings = response.json()

                # Fetch sources
                response = await client.get(
                    f"{API_BASE_URL}/sessions/{self.current_session_id}/sources"
                )
                if response.status_code == 200:
                    self.sources = response.json()

                # Fetch perspectives
                response = await client.get(
                    f"{API_BASE_URL}/sessions/{self.current_session_id}/perspectives"
                )
                if response.status_code == 200:
                    self.perspectives = response.json()

        except Exception as e:
            self.error_message = f"Failed to fetch results: {str(e)}"

    async def load_session(self, session_id: str):
        """Load a past research session."""
        self.current_session_id = session_id
        self.phase = "completed"
        await self.fetch_results()

    async def fetch_history(self):
        """Fetch past research sessions."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{API_BASE_URL}/sessions",
                    params={"limit": 20},
                )
                if response.status_code == 200:
                    data = response.json()
                    self.past_sessions = data.get("sessions", [])
        except Exception as e:
            self.error_message = f"Failed to fetch history: {str(e)}"

    def select_finding(self, finding_id: str):
        """Select a finding for detail view."""
        self.selected_finding_id = finding_id

    def clear_selection(self):
        """Clear finding selection."""
        self.selected_finding_id = None

    def dismiss_error(self):
        """Dismiss error message."""
        self.error_message = ""
