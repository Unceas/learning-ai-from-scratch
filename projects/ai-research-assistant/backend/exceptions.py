"""Custom application exceptions for domain-level error handling."""


class AppException(Exception):

    def __init__(self, error: str, detail: str, status_code: int = 400):
        self.error = error
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class DocumentNotFoundError(AppException):

    def __init__(self):
        super().__init__(
            error="document_not_found",
            detail="The requested document does not exist.",
            status_code=404
        )


class DocumentProcessingError(AppException):

    def __init__(self):
        super().__init__(
            error="document_processing_failed",
            detail="The document could not be processed.",
            status_code=400
        )


class EmptyDocumentError(AppException):

    def __init__(self):
        super().__init__(
            error="empty_document",
            detail="No readable text was found in the document.",
            status_code=400
        )
