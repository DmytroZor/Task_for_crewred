class ApplicationError(Exception):
    status_code = 400
    detail = "Application error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    detail = "Resource not found"


class ConflictError(ApplicationError):
    status_code = 409
    detail = "Resource conflict"


class BusinessRuleError(ApplicationError):
    status_code = 422
    detail = "Business rule violation"


class ExternalServiceError(ApplicationError):
    status_code = 503
    detail = "External service is unavailable"
