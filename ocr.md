# OCR Benchmark Arena - Claude Code Requirements

## Project Overview

Build a production-grade OCR benchmark application that compares multiple OCR solutions across three categories. The application allows users to upload a document (image or PDF), processes it through 8 different OCR engines, and provides professional evaluation using an LLM judge.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  LLM Tab    │  │ Open LLM Tab│  │Traditional  │              │
│  │             │  │             │  │  OCR Tab    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   OCR Service Router                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │              │              │                          │
│         ▼              ▼              ▼                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                    │
│  │ LLM OCR   │  │ Open LLM  │  │Traditional│                    │
│  │ Services  │  │ Services  │  │   OCR     │                    │
│  └───────────┘  └───────────┘  └───────────┘                    │
│         │              │              │                          │
│         └──────────────┴──────────────┘                          │
│                        │                                         │
│                        ▼                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LLM Evaluation Service                       │   │
│  │     (Grammar, Structure, Style Analysis)                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## OCR Engines Configuration

### Category 1: Commercial LLM APIs (via OpenRouter + Direct APIs)

| Engine | Provider | Model ID | API Type | Notes |
|--------|----------|----------|----------|-------|
| **GPT-5.2** | OpenRouter | `openai/gpt-5.2` | OpenRouter | Best for handwriting |
| **Gemini 3 Flash** | OpenRouter | `google/gemini-3-flash-preview` | OpenRouter | 15% better than 2.5, excellent for complex docs |
| **Mistral OCR 3** | Mistral Direct | `mistral-ocr-latest` | Mistral SDK | Dedicated OCR endpoint, $1/1000 pages |

### Category 2: Open-Source VLM OCR (via OpenRouter + Local)

| Engine | Provider | Model ID | API Type | Notes |
|--------|----------|----------|----------|-------|
| **Chandra** | Local/HuggingFace | `datalab-to/chandra` | Local vLLM | SOTA 83.1% on olmOCR-Bench |
| **Qwen3-VL-32B** | OpenRouter | `qwen/qwen3-vl-32b-instruct` | OpenRouter | Strong multilingual, 32 languages OCR |

### Category 3: Traditional OCR (Local Python packages)

| Engine | Package | Notes |
|--------|---------|-------|
| **PaddleOCR** | `paddleocr` | Excellent Asian language support |
| **EasyOCR** | `easyocr` | Good multilingual, easy setup |
| **Surya OCR** | `surya-ocr==0.17.0` | 90+ languages, layout analysis |

---

## Provider Strategy

### OpenRouter (Primary for LLM/VLM models)
- **Unified API**: OpenAI-compatible endpoint for all models
- **Available models**: GPT-5.2, Gemini 3 Flash, Qwen3-VL
- **PDF Support**: Built-in with `mistral-ocr` engine for preprocessing
- **Endpoint**: `https://openrouter.ai/api/v1/chat/completions`

### Mistral Direct API (For Mistral OCR 3)
- **Reason**: Mistral OCR uses dedicated `/ocr` endpoint, not chat completions
- **SDK**: `mistralai` Python package
- **Endpoint**: Dedicated OCR processor

### Local Execution (For Chandra + Traditional OCR)
- **Chandra**: Requires GPU, uses vLLM or HuggingFace transformers
- **Traditional OCR**: Pure Python packages, CPU/GPU

---

## Project Structure

```
ocr_benchmark_arena/
├── pyproject.toml              # Poetry/pip dependencies
├── requirements.txt            # Pip requirements
├── .env.example                # Environment variables template
├── README.md                   # Setup and usage guide
│
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration and settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py           # API endpoints
│   │   └── schemas.py          # Pydantic models
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract OCR service base
│   │   │
│   │   ├── llm/                # Category 1: Commercial LLMs
│   │   │   ├── __init__.py
│   │   │   ├── openrouter.py   # GPT-5.2, Gemini 3 Flash
│   │   │   └── mistral_ocr.py  # Mistral OCR 3 dedicated
│   │   │
│   │   ├── open_llm/           # Category 2: Open LLMs
│   │   │   ├── __init__.py
│   │   │   ├── chandra.py      # Chandra OCR (local)
│   │   │   └── qwen_vl.py      # Qwen3-VL via OpenRouter
│   │   │
│   │   ├── traditional/        # Category 3: Traditional OCR
│   │   │   ├── __init__.py
│   │   │   ├── paddle.py       # PaddleOCR
│   │   │   ├── easy.py         # EasyOCR
│   │   │   └── surya.py        # Surya OCR
│   │   │
│   │   └── evaluation/         # LLM Evaluation Service
│   │       ├── __init__.py
│   │       └── evaluator.py    # Grammar, structure, style checker
│   │
│   └── utils/
│       ├── __init__.py
│       ├── file_handler.py     # PDF/Image processing
│       ├── image_utils.py      # Image preprocessing
│       └── metrics.py          # Timing, token counting
│
├── streamlit_app/
│   ├── __init__.py
│   ├── app.py                  # Main Streamlit application
│   ├── components/
│   │   ├── __init__.py
│   │   ├── uploader.py         # File upload component
│   │   ├── results_display.py  # OCR results display
│   │   ├── evaluation_view.py  # Evaluation results
│   │   └── comparison.py       # Side-by-side comparison
│   └── styles/
│       └── custom.css          # Custom styling
│
└── tests/
    ├── __init__.py
    ├── test_services.py
    └── sample_docs/            # Test documents
        ├── simple_text.png
        ├── table_document.pdf
        └── handwritten.jpg
```

---

## Dependencies

### requirements.txt

```txt
# Core Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
streamlit>=1.31.0
python-multipart>=0.0.6
pydantic>=2.5.0
pydantic-settings>=2.1.0

# HTTP Clients
httpx>=0.26.0
aiohttp>=3.9.0
requests>=2.31.0

# OpenRouter & LLM APIs
openai>=1.12.0                  # OpenRouter uses OpenAI-compatible API
mistralai>=1.0.0                # Mistral OCR direct API

# Image & PDF Processing
Pillow>=10.2.0
pdf2image>=1.17.0
PyMuPDF>=1.23.0                 # fitz for PDF handling
python-magic>=0.4.27

# Traditional OCR
paddleocr>=2.7.0                # PaddleOCR
paddlepaddle>=2.6.0             # PaddlePaddle backend (CPU)
# paddlepaddle-gpu>=2.6.0       # Uncomment for GPU
easyocr>=1.7.0                  # EasyOCR
surya-ocr>=0.17.0               # Surya OCR

# Open LLM (Chandra) - Optional local inference
transformers>=4.38.0
torch>=2.2.0
accelerate>=0.27.0
# vllm>=0.3.0                   # Uncomment for vLLM inference

# Utilities
python-dotenv>=1.0.0
tenacity>=8.2.0                 # Retry logic
tiktoken>=0.6.0                 # Token counting
structlog>=24.1.0               # Structured logging
tqdm>=4.66.0

# Development
pytest>=8.0.0
pytest-asyncio>=0.23.0
black>=24.1.0
ruff>=0.2.0
```

---

## Environment Variables

### .env.example

```bash
# ===========================================
# OCR Benchmark Arena - Environment Variables
# ===========================================

# OpenRouter API (for GPT-5.2, Gemini 3 Flash, Qwen3-VL)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Mistral API (for Mistral OCR 3)
MISTRAL_API_KEY=xxxxxxxxxxxx

# Optional: OpenAI Direct (if not using OpenRouter for GPT)
# OPENAI_API_KEY=sk-xxxxxxxxxxxx

# Optional: Google AI (if not using OpenRouter for Gemini)
# GOOGLE_API_KEY=xxxxxxxxxxxx

# Chandra OCR (Local inference)
CHANDRA_ENABLED=true
CHANDRA_METHOD=hf              # 'hf' for HuggingFace, 'vllm' for vLLM server
CHANDRA_MODEL=datalab-to/chandra
# VLLM_API_BASE=http://localhost:8000/v1  # If using vLLM

# Traditional OCR Settings
PADDLEOCR_LANG=en              # Default language
EASYOCR_LANGS=en,cs,de,fr      # Comma-separated language codes
SURYA_LANGS=en                 # Surya languages

# Application Settings
API_HOST=0.0.0.0
API_PORT=8000
STREAMLIT_PORT=8501
MAX_FILE_SIZE_MB=50
TEMP_DIR=/tmp/ocr_benchmark

# Evaluation LLM (uses OpenRouter)
EVAL_MODEL=openai/gpt-5.2
EVAL_TEMPERATURE=0.1

# Logging
LOG_LEVEL=INFO
```

---

## API Endpoints

### FastAPI Routes

```python
# Health & Info
GET  /health                    # Health check
GET  /info                      # Available OCR engines info

# OCR Processing
POST /ocr/process               # Process document with all engines
POST /ocr/process/{engine}      # Process with specific engine

# Evaluation
POST /evaluate                  # Evaluate OCR output quality
POST /evaluate/compare          # Compare multiple OCR outputs

# Request Schema
{
    "file": UploadFile,         # Image or PDF
    "engines": ["gpt52", "gemini3", "mistral_ocr", ...],  # Optional filter
    "languages": ["en", "cs"],  # Hint for traditional OCR
    "include_evaluation": true  # Run LLM evaluation
}

# Response Schema
{
    "document_id": "uuid",
    "filename": "document.pdf",
    "results": {
        "gpt52": {
            "text": "...",
            "confidence": 0.95,
            "processing_time_ms": 1234,
            "tokens_used": 500,
            "cost_usd": 0.002
        },
        ...
    },
    "evaluation": {
        "grammar_score": 0.92,
        "structure_score": 0.88,
        "style_score": 0.85,
        "issues": [...],
        "recommendations": [...]
    }
}
```

---

## LLM Evaluation Prompt

### Document Quality Evaluation System Prompt

```python
EVALUATION_SYSTEM_PROMPT = """
You are an expert document quality analyst specializing in OCR output evaluation. 
Your task is to analyze extracted text for quality issues that may indicate OCR errors 
or original document problems.

Evaluate the following aspects:

## 1. GRAMMAR & SPELLING (Score 0-100)
- Identify misspellings that appear to be OCR errors (e.g., 'rn' misread as 'm')
- Check for broken words or merged words
- Detect character substitutions (0/O, 1/l/I, etc.)
- Note missing punctuation or incorrect punctuation

## 2. DOCUMENT STRUCTURE (Score 0-100)
- Assess preservation of paragraphs and sections
- Check table structure integrity
- Evaluate list formatting (numbered, bulleted)
- Verify heading hierarchy
- Check for proper line breaks vs run-on text

## 3. STYLE & CONSISTENCY (Score 0-100)
- Check consistent formatting throughout
- Identify encoding issues or garbled characters
- Assess reading order correctness
- Note any repeated or missing content
- Check header/footer handling

## 4. DETECTED ISSUES
List specific issues found with:
- Location (approximate position in text)
- Issue type (grammar/structure/style)
- Severity (critical/major/minor)
- Suggested correction if applicable

## 5. OVERALL QUALITY ASSESSMENT
Provide:
- Composite score (weighted average)
- OCR engine suitability assessment
- Recommendations for improvement

Respond in JSON format:
{
    "grammar": {"score": 0-100, "issues": [...]},
    "structure": {"score": 0-100, "issues": [...]},
    "style": {"score": 0-100, "issues": [...]},
    "detected_issues": [...],
    "composite_score": 0-100,
    "confidence": 0-1,
    "recommendations": [...],
    "summary": "Brief overall assessment"
}
"""

EVALUATION_USER_PROMPT = """
Analyze the following OCR-extracted text for quality issues:

--- DOCUMENT START ---
{ocr_text}
--- DOCUMENT END ---

Original document type: {doc_type}
OCR Engine used: {engine_name}
Expected language(s): {languages}

Provide your detailed quality evaluation.
"""
```

---

## Streamlit UI Layout

### Main Application Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 OCR Benchmark Arena                              [Settings] │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📤 Upload Document                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Drag and drop file here                                │   │
│  │  Supported: PNG, JPG, PDF (max 50MB)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  🌍 Language Selection: [English ▼] [+ Add Language]           │
│                                                                 │
│  [🚀 Process All Engines]  [⚙️ Select Engines...]              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📊 Results                                                     │
│  ┌─────────┬─────────────┬───────────────┐                     │
│  │ 🤖 LLMs │ 🔓 Open LLMs │ 📝 Traditional │                    │
│  ├─────────┴─────────────┴───────────────┤                     │
│  │                                        │                     │
│  │  [Tab Content - OCR Results]           │                     │
│  │                                        │                     │
│  │  ┌────────────────────────────────┐   │                     │
│  │  │ GPT-5.2          ⏱️ 1.2s      │   │                     │
│  │  │ Score: 94/100    💰 $0.003    │   │                     │
│  │  ├────────────────────────────────┤   │                     │
│  │  │ [Extracted Text...]            │   │                     │
│  │  └────────────────────────────────┘   │                     │
│  │                                        │                     │
│  │  ┌────────────────────────────────┐   │                     │
│  │  │ Gemini 3 Flash   ⏱️ 0.8s      │   │                     │
│  │  │ Score: 91/100    💰 $0.001    │   │                     │
│  │  ├────────────────────────────────┤   │                     │
│  │  │ [Extracted Text...]            │   │                     │
│  │  └────────────────────────────────┘   │                     │
│  │                                        │                     │
│  └────────────────────────────────────────┘                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📈 Evaluation Summary                                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Best Overall: GPT-5.2 (94/100)                         │   │
│  │  Fastest: Gemini 3 Flash (0.8s)                         │   │
│  │  Most Cost-Effective: PaddleOCR ($0.00)                 │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  Grammar Issues Found: 3                                 │   │
│  │  Structure Issues: 1                                     │   │
│  │  [View Detailed Report]                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Service Implementation Notes

### OpenRouter Service (GPT-5.2, Gemini 3 Flash, Qwen3-VL)

```python
# Key implementation points:
# 1. Use OpenAI-compatible client with OpenRouter base URL
# 2. Pass image as base64 in message content
# 3. Add OpenRouter-specific headers

from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

# For OCR, send image with extraction prompt
response = client.chat.completions.create(
    model="openai/gpt-5.2",  # or google/gemini-3-flash-preview
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Extract all text from this document. Preserve structure, tables, and formatting. Output in Markdown."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    extra_headers={
        "HTTP-Referer": "https://ocr-benchmark.app",
        "X-Title": "OCR Benchmark Arena"
    }
)
```

### Mistral OCR Service (Dedicated OCR API)

```python
# Mistral uses dedicated OCR endpoint, not chat completions
from mistralai import Mistral

client = Mistral(api_key=os.environ["MISTRAL_API_KEY"])

# Direct OCR processing
ocr_response = client.ocr.process(
    model="mistral-ocr-latest",  # or mistral-ocr-2512
    document={
        "type": "image_url",
        "image_url": image_url  # or base64
    },
    table_format="html",
    include_image_base64=True
)

# Response contains structured markdown with table support
```

### Chandra OCR Service (Local)

```python
# Option 1: HuggingFace Transformers
from transformers import AutoModel, AutoProcessor
from chandra.model.hf import generate_hf
from chandra.model.schema import BatchInputItem

model = AutoModel.from_pretrained("datalab-to/chandra").cuda()
model.processor = AutoProcessor.from_pretrained("datalab-to/chandra")

batch = [BatchInputItem(image=pil_image, prompt_type="ocr_layout")]
result = generate_hf(batch, model)[0]

# Option 2: vLLM Server (recommended for production)
# Start server: chandra_vllm
# Then use OpenAI-compatible client pointing to local server
```

---

## Running the Application

### Development Mode

```bash
# 1. Clone and setup
git clone <repo>
cd ocr_benchmark_arena
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start FastAPI backend
uvicorn app.main:app --reload --port 8000

# 4. Start Streamlit frontend (new terminal)
streamlit run streamlit_app/app.py --server.port 8501
```

### Production Mode

```bash
# Use Docker Compose (recommended)
docker-compose up -d

# Or manual:
# Backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Frontend
streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0
```

---

## Key Implementation Priorities

### Phase 1: Core Infrastructure
1. [ ] FastAPI app with file upload handling
2. [ ] OpenRouter service for GPT-5.2 and Gemini 3 Flash
3. [ ] Mistral OCR 3 direct integration
4. [ ] Basic Streamlit UI with upload and display

### Phase 2: Traditional OCR
5. [ ] PaddleOCR integration
6. [ ] EasyOCR integration  
7. [ ] Surya OCR integration

### Phase 3: Open LLM OCR
8. [ ] Qwen3-VL via OpenRouter
9. [ ] Chandra local inference (optional - requires GPU)

### Phase 4: Evaluation & Polish
10. [ ] LLM evaluation service
11. [ ] Comparison views and metrics
12. [ ] Export and reporting features

---

## Notes & Considerations

### API Availability Summary

| Model | Via OpenRouter | Direct API | Local |
|-------|----------------|------------|-------|
| GPT-5.2 | ✅ | ✅ (OpenAI) | ❌ |
| Gemini 3 Flash | ✅ | ✅ (Google) | ❌ |
| Mistral OCR 3 | ⚠️ (PDF only via preprocessing) | ✅ (Dedicated endpoint) | ❌ |
| Qwen3-VL | ✅ | ❌ | ✅ |
| Chandra | ❌ | ❌ | ✅ |
| PaddleOCR | ❌ | ❌ | ✅ |
| EasyOCR | ❌ | ❌ | ✅ |
| Surya OCR | ❌ | ❌ | ✅ |

### Cost Estimates (per 1000 pages)

| Engine | Estimated Cost |
|--------|---------------|
| GPT-5.2 | ~$5-10 |
| Gemini 3 Flash | ~$1-2 (or free tier) |
| Mistral OCR 3 | $1-2 |
| Qwen3-VL (OpenRouter) | ~$0.50-1 |
| Chandra (local) | GPU compute only |
| PaddleOCR | Free |
| EasyOCR | Free |
| Surya OCR | Free |

### GPU Requirements

- **Chandra**: Requires ~20GB VRAM (A100/H100 recommended)
- **Surya OCR**: Optional GPU, ~8GB VRAM for faster processing
- **PaddleOCR/EasyOCR**: Optional GPU acceleration

---

## Success Criteria

1. ✅ Single upload → 8 OCR engines process in parallel
2. ✅ Side-by-side comparison in categorized tabs
3. ✅ LLM-based quality evaluation with grammar/structure/style scoring
4. ✅ Performance metrics: latency, cost, accuracy scores
5. ✅ Export results as JSON/Markdown report
6. ✅ Support for images (PNG, JPG) and PDFs (multi-page)
7. ✅ Multilingual support with language hints