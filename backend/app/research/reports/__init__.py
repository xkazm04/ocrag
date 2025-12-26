"""Report generation module for research intelligence platform."""

from .router import router
from .service import ReportGenerationService
from .schemas import (
    GenerateReportRequest,
    ReportResponse,
    ReportFormat,
    ReportVariant,
    ReportData,
    ReportMetadata,
)


__all__ = [
    "router",
    "ReportGenerationService",
    "GenerateReportRequest",
    "ReportResponse",
    "ReportFormat",
    "ReportVariant",
    "ReportData",
    "ReportMetadata",
]
