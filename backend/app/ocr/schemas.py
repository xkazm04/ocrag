"""OCR Benchmark Pydantic schemas."""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class OCRCategory(str, Enum):
    """OCR engine categories."""
    LLM = "llm"
    OPEN_LLM = "open_llm"
    TRADITIONAL = "traditional"


class OCREngine(str, Enum):
    """Available OCR engines."""
    GPT = "gpt"
    GEMINI = "gemini"
    MISTRAL = "mistral"
    QWEN = "qwen"
    PADDLE = "paddle"
    EASY = "easy"
    SURYA = "surya"


class OCRResult(BaseModel):
    """Result from a single OCR engine."""
    engine: str
    category: OCRCategory
    text: str = ""
    success: bool = True
    error: Optional[str] = None
    processing_time_ms: float = 0
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    confidence: Optional[float] = None


class EvaluationIssue(BaseModel):
    """Single evaluation issue."""
    location: str = ""
    issue_type: str = ""
    severity: str = "minor"
    description: str = ""
    suggestion: Optional[str] = None


class EvaluationResult(BaseModel):
    """LLM evaluation result."""
    grammar_score: float = 0
    structure_score: float = 0
    style_score: float = 0
    composite_score: float = 0
    confidence: float = 0
    issues: list[EvaluationIssue] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str = ""


class OCRProcessRequest(BaseModel):
    """Request for OCR processing."""
    engines: Optional[list[OCREngine]] = None
    languages: list[str] = Field(default=["en"])
    include_evaluation: bool = False


class OCRProcessResponse(BaseModel):
    """Response from OCR processing."""
    document_id: str
    filename: str
    results: dict[str, OCRResult] = Field(default_factory=dict)
    evaluation: Optional["ComparativeEvaluation"] = None
    total_time_ms: float = 0


class EngineInfo(BaseModel):
    """Information about an OCR engine."""
    id: str
    name: str
    category: OCRCategory
    available: bool
    description: str
    cost_per_1k_pages: Optional[str] = None


class OCRInfoResponse(BaseModel):
    """Response with available OCR engines."""
    engines: list[EngineInfo]
    categories: list[str] = ["llm", "open_llm", "traditional"]


class EngineScore(BaseModel):
    """Score breakdown for a single engine."""
    engine_id: str
    engine_name: str
    category: str
    accuracy_score: float = 0  # Text accuracy percentage
    completeness_score: float = 0  # How complete the extraction is
    formatting_score: float = 0  # Structure/formatting preservation
    overall_score: float = 0  # Weighted average
    rank: int = 0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class ComparativeEvaluation(BaseModel):
    """Comparative evaluation of all OCR results."""
    engines: list[EngineScore] = Field(default_factory=list)
    best_overall: Optional[str] = None
    best_accuracy: Optional[str] = None
    best_formatting: Optional[str] = None
    summary: str = ""
    methodology: str = ""
