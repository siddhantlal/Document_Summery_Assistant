# Development Approach

I built the Document Summary Assistant as a focused Python package with a thin Flask entry point and a vanilla HTML, CSS, and JavaScript frontend. Configuration, HTTP routing, document extraction, provider communication, and public errors live in separate modules, keeping each responsibility independently testable without unnecessary framework or build-tool dependencies.

The document boundary validates upload size, binary content, file extensions, and byte signatures before processing. Text-based PDFs are extracted with pypdf in layout mode to retain page boundaries and approximate spacing. PNG and JPEG scans are processed by calling the Tesseract executable directly, avoiding an additional OCR wrapper. Temporary image files are always removed after success or failure.

Extracted text is sent to NVIDIA's OpenAI-compatible NIM endpoint through the OpenAI Python SDK, keeping the API key server-side. The prompt treats document contents as untrusted data and requests JSON containing a faithful summary and key points. Nemotron's streamed reasoning is discarded, while final content is collected, validated, and returned to the web layer as an immutable named result.

The application includes consistent error responses, upload and extraction limits, provider timeouts, and health reporting. Unit tests mirror the focused modules and cover API contracts, invalid values, extraction, OCR cleanup, and NVIDIA failures. Docker provides Python, Gunicorn, Tesseract, and English language data for reproducible deployment.
