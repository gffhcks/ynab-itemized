"""YNAB API exceptions."""


class YNABAPIError(Exception):
    """Base exception for YNAB API errors."""
    
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class YNABAuthError(YNABAPIError):
    """Authentication error with YNAB API."""
    pass


class YNABRateLimitError(YNABAPIError):
    """Rate limit exceeded error."""
    
    def __init__(self, message: str, retry_after: int = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class YNABNotFoundError(YNABAPIError):
    """Resource not found error."""
    pass


class YNABValidationError(YNABAPIError):
    """Validation error from YNAB API."""
    pass
