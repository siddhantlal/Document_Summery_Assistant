# Development Approach

I built the Document Summary Assistant as a lightweight Flask application with a vanilla HTML, CSS, and JavaScript frontend. This kept the architecture easy to review and avoided unnecessary framework and build-tool dependencies while still supporting drag-and-drop uploads, responsive layouts, loading states, and accessible interactions.

The backend validates file extensions and byte signatures before processing. Text-based PDFs are extracted with pypdf in layout mode to retain page boundaries and approximate spacing. PNG and JPEG scans are processed by calling the Tesseract executable directly, avoiding an additional OCR wrapper. Temporary image files are always removed after success or failure.

Extracted text is sent to Gemini through Python's standard-library HTTP client, keeping the API key server-side without a provider SDK. The prompt treats document contents as untrusted data and requests schema-constrained JSON containing a faithful summary and key points based on the selected short, medium, or long length.

The application includes consistent error responses, upload and extraction limits, provider timeouts, and health reporting. Standard-library unit tests cover API contracts, validation, extraction, OCR cleanup, and Gemini failures. Docker provides Python, Gunicorn, Tesseract, and English language data, producing a reproducible deployment environment with only three Python runtime packages.
