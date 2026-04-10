class AppError(Exception):
    """Base application error."""


class ValidationError(AppError):
    """Raised when user input is invalid."""


class TranscriptError(AppError):
    """Raised when transcript loading fails."""


class SummarizationError(AppError):
    """Raised when LLM summarization fails."""


class ExportError(AppError):
    """Raised when writing output fails."""
