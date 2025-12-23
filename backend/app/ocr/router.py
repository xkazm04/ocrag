"""OCR Benchmark API routes."""
import uuid
import time
import asyncio
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from app.ocr.schemas import (
    OCREngine, OCRProcessResponse, OCRResult,
    OCRInfoResponse, EngineInfo, OCRCategory, EvaluationResult
)
from app.ocr.services import (
    OpenRouterOCR, MistralOCR, QwenOCR,
    PaddleOCR, EasyOCRService, SuryaOCR, OCREvaluator
)

router = APIRouter(prefix="/ocr", tags=["OCR Benchmark"])

# Initialize services
SERVICES = {
    "gpt": OpenRouterOCR("gpt"),
    "gemini": OpenRouterOCR("gemini"),
    "mistral": MistralOCR(),
    "qwen": QwenOCR(),
    "paddle": PaddleOCR(),
    "easy": EasyOCRService(),
    "surya": SuryaOCR(),
}

ENGINE_INFO = {
    "gpt": ("GPT-5.2", OCRCategory.LLM, "Best for complex documents", "$5-10"),
    "gemini": ("Gemini 3 Flash", OCRCategory.LLM, "Fast and accurate", "$1-2"),
    "mistral": ("Mistral OCR", OCRCategory.LLM, "Dedicated OCR model", "$1-2"),
    "qwen": ("Qwen2 VL 72B", OCRCategory.OPEN_LLM, "Strong multilingual", "$0.50"),
    "paddle": ("PaddleOCR", OCRCategory.TRADITIONAL, "Asian language support", "Free"),
    "easy": ("EasyOCR", OCRCategory.TRADITIONAL, "Easy multilingual", "Free"),
    "surya": ("Surya OCR", OCRCategory.TRADITIONAL, "90+ languages", "Free"),
}


@router.get("/info", response_model=OCRInfoResponse)
async def get_ocr_info():
    """Get available OCR engines and their status."""
    engines = []
    for engine_id, service in SERVICES.items():
        name, category, desc, cost = ENGINE_INFO[engine_id]
        engines.append(EngineInfo(
            id=engine_id,
            name=name,
            category=category,
            available=service.is_available(),
            description=desc,
            cost_per_1k_pages=cost
        ))
    return OCRInfoResponse(engines=engines)


@router.post("/process", response_model=OCRProcessResponse)
async def process_document(
    file: UploadFile = File(...),
    engines: Optional[str] = Query(None, description="Comma-separated engine IDs"),
    languages: str = Query("en", description="Comma-separated language codes"),
    include_evaluation: bool = Query(False, description="Run LLM evaluation")
):
    """Process document with selected OCR engines."""
    # Validate file type
    if not file.content_type:
        raise HTTPException(400, "Unknown file type")

    allowed = ["image/png", "image/jpeg", "image/jpg", "image/webp", "application/pdf"]
    if file.content_type not in allowed:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    # Read file
    image_bytes = await file.read()
    doc_id = f"ocr_{uuid.uuid4().hex[:12]}"
    lang_list = [l.strip() for l in languages.split(",")]

    # Select engines
    if engines:
        engine_ids = [e.strip() for e in engines.split(",")]
    else:
        engine_ids = list(SERVICES.keys())

    # Process with selected engines in parallel
    start_time = time.perf_counter()
    tasks = []
    for engine_id in engine_ids:
        if engine_id in SERVICES:
            service = SERVICES[engine_id]
            if service.is_available():
                tasks.append(_process_with_engine(
                    service, image_bytes, file.filename, lang_list
                ))

    results_list = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = (time.perf_counter() - start_time) * 1000

    # Build results dict
    results = {}
    for result in results_list:
        if isinstance(result, OCRResult):
            results[result.engine] = result
        elif isinstance(result, Exception):
            # Log but continue
            pass

    # Run evaluation if requested
    evaluation = None
    if include_evaluation and results:
        evaluation = await _evaluate_results(results, lang_list[0])

    return OCRProcessResponse(
        document_id=doc_id,
        filename=file.filename or "unknown",
        results=results,
        evaluation=evaluation,
        total_time_ms=total_time
    )


@router.post("/process/{engine_id}", response_model=OCRResult)
async def process_single_engine(
    engine_id: str,
    file: UploadFile = File(...),
    languages: str = Query("en")
):
    """Process document with a single OCR engine."""
    if engine_id not in SERVICES:
        raise HTTPException(404, f"Unknown engine: {engine_id}")

    service = SERVICES[engine_id]
    if not service.is_available():
        raise HTTPException(503, f"Engine {engine_id} not available")

    image_bytes = await file.read()
    lang_list = [l.strip() for l in languages.split(",")]

    return await service.process(image_bytes, file.filename, lang_list)


async def _process_with_engine(service, image: bytes, filename: str, langs: list):
    """Process image with a single engine."""
    return await service.process(image, filename, langs)


async def _evaluate_results(
    results: dict[str, OCRResult],
    language: str
) -> dict[str, EvaluationResult]:
    """Evaluate all successful OCR results."""
    evaluator = OCREvaluator()
    if not evaluator.is_available():
        return None

    evaluation = {}
    for engine_id, result in results.items():
        if result.success and result.text:
            eval_result = await evaluator.evaluate(
                result.text, engine_id, language
            )
            evaluation[engine_id] = eval_result

    return evaluation
