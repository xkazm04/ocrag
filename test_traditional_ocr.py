"""Test script for traditional OCR engines."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from pathlib import Path

TEST_PDF = Path(__file__).parent / "test_invoices" / "invoice_czech_autodesk.pdf"


def test_pdf_to_images():
    """Test PDF to images conversion."""
    print("\n=== Testing PDF to Images Conversion ===")

    try:
        import fitz  # PyMuPDF
        print("PyMuPDF imported successfully")
    except ImportError as e:
        print(f"ERROR: PyMuPDF not installed: {e}")
        print("Run: pip install PyMuPDF")
        return None

    if not TEST_PDF.exists():
        print(f"ERROR: Test file not found: {TEST_PDF}")
        return None

    with open(TEST_PDF, "rb") as f:
        pdf_bytes = f.read()

    print(f"PDF file size: {len(pdf_bytes)} bytes")

    # Convert PDF to images
    images = []
    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    print(f"PDF pages: {len(pdf)}")

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")

        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        images.append(img)
        print(f"  Page {page_num + 1}: {img.size} pixels, mode={img.mode}")

    pdf.close()
    print(f"SUCCESS: Converted {len(images)} pages to images")
    return images


def test_paddleocr(images):
    """Test PaddleOCR."""
    print("\n=== Testing PaddleOCR ===")

    try:
        from paddleocr import PaddleOCR
        print("PaddleOCR imported successfully")
    except ImportError as e:
        print(f"ERROR: PaddleOCR not installed: {e}")
        return False

    try:
        # Initialize with minimal options
        print("Initializing PaddleOCR engine...")
        engine = PaddleOCR(lang="en")
        print("Engine initialized")

        import numpy as np

        for i, img in enumerate(images[:1]):  # Test first page only
            print(f"\nProcessing page {i + 1}...")

            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)
            print(f"  Image array shape: {img_array.shape}")

            # Use predict() method (new API)
            print("  Calling engine.predict()...")
            result = engine.predict(img_array)

            print(f"  Result type: {type(result)}")

            # New API returns OCRResult objects
            if result:
                print(f"  Result length: {len(result)}")
                ocr_result = result[0]
                print(f"  OCRResult type: {type(ocr_result)}")
                print(f"  OCRResult attributes: {[a for a in dir(ocr_result) if not a.startswith('_')]}")

                # Check for rec_texts attribute (new API)
                if hasattr(ocr_result, 'rec_texts'):
                    texts = ocr_result.rec_texts
                    print(f"  rec_texts count: {len(texts)}")
                    for j, text in enumerate(texts[:5]):
                        print(f"    [{j}]: {text}")
                elif hasattr(ocr_result, 'keys'):
                    # Dict-like result
                    print(f"  Keys: {ocr_result.keys()}")

        print("SUCCESS: PaddleOCR works!")
        return True

    except Exception as e:
        print(f"ERROR: PaddleOCR failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_easyocr(images):
    """Test EasyOCR."""
    print("\n=== Testing EasyOCR ===")

    try:
        import easyocr
        print("EasyOCR imported successfully")
    except ImportError as e:
        print(f"ERROR: EasyOCR not installed: {e}")
        return False

    try:
        print("Initializing EasyOCR reader...")
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        print("Reader initialized")

        import numpy as np

        for i, img in enumerate(images[:1]):  # Test first page only
            print(f"\nProcessing page {i + 1}...")

            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_array = np.array(img)
            print(f"  Image array shape: {img_array.shape}")

            print("  Calling reader.readtext()...")
            results = reader.readtext(img_array)

            print(f"  Results count: {len(results)}")
            # Show first few results
            for j, detection in enumerate(results[:3]):
                bbox, text, confidence = detection
                print(f"    [{j}] ({confidence:.2f}): {text[:50]}...")

        print("SUCCESS: EasyOCR works!")
        return True

    except Exception as e:
        print(f"ERROR: EasyOCR failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_suryaocr(images):
    """Test Surya OCR."""
    print("\n=== Testing Surya OCR ===")

    try:
        from surya.recognition import RecognitionPredictor
        from surya.detection import DetectionPredictor
        print("Surya OCR imported successfully")
    except ImportError as e:
        print(f"ERROR: Surya OCR not installed: {e}")
        return False

    try:
        # Check if FoundationPredictor exists (v0.17+)
        try:
            from surya.recognition import FoundationPredictor
            print("FoundationPredictor available (v0.17+ API)")
            has_foundation = True
        except ImportError:
            print("FoundationPredictor not available (older API)")
            has_foundation = False

        print("Initializing Surya predictors...")
        det_predictor = DetectionPredictor()
        print("  DetectionPredictor initialized")

        if has_foundation:
            foundation_predictor = FoundationPredictor()
            print("  FoundationPredictor initialized")
            rec_predictor = RecognitionPredictor(foundation_predictor)
        else:
            rec_predictor = RecognitionPredictor()
        print("  RecognitionPredictor initialized")

        # Inspect the rec_predictor signature
        import inspect
        sig = inspect.signature(rec_predictor.__call__)
        print(f"  RecognitionPredictor.__call__ signature: {sig}")

        for i, img in enumerate(images[:1]):  # Test first page only
            print(f"\nProcessing page {i + 1}...")

            if img.mode != 'RGB':
                img = img.convert('RGB')

            # New API: task_names are task types, not language codes
            # Supported: 'ocr_with_boxes', 'ocr_without_boxes', 'block_without_boxes', 'layout', 'table_structure'
            print("  Trying: rec_predictor([img], det_predictor=det_predictor)...")
            rec_results = rec_predictor([img], det_predictor=det_predictor)
            print(f"  Recognition result type: {type(rec_results)}")

            if rec_results:
                print(f"  Recognition results count: {len(rec_results)}")
                result = rec_results[0]
                print(f"  Result type: {type(result)}")
                print(f"  Result attributes: {[a for a in dir(result) if not a.startswith('_')]}")

                if hasattr(result, 'text_lines'):
                    text_lines = result.text_lines
                    print(f"  Text lines count: {len(text_lines)}")
                    for j, tl in enumerate(text_lines[:5]):
                        text = tl.text if hasattr(tl, 'text') else str(tl)
                        print(f"    [{j}]: {text[:50] if len(text) > 50 else text}")

            print("SUCCESS: Surya OCR works!")
            return True

    except Exception as e:
        print(f"ERROR: Surya OCR failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Traditional OCR Test Script")
    print("=" * 60)
    print(f"Test file: {TEST_PDF}")

    # First convert PDF to images
    images = test_pdf_to_images()

    if images:
        # Test each OCR engine
        results = {}
        results["PaddleOCR"] = test_paddleocr(images)
        results["EasyOCR"] = test_easyocr(images)
        results["SuryaOCR"] = test_suryaocr(images)

        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for engine, success in results.items():
            status = "PASS" if success else "FAIL"
            print(f"  {engine}: {status}")
    else:
        print("\nCannot run OCR tests without images")
