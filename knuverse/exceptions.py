class RequestException(Exception):
    """
    Used for invalid requests.
    """


class UnexpectedResponseCodeException(Exception):
    """
    Raised when the server returns an unexpected response code.
    """


class HttpErrorException(Exception):
    """
    Used for HTTP errors. Status codes >= 400
    """


class BadRequestException(HttpErrorException):
    """
    Used for HTTP Bad Request(400) Errors
    """


class UnauthorizedException(HttpErrorException):
    """
    Used for HTTP Unauthorized(401) Errors
    """


class ForbiddenException(HttpErrorException):
    """
    Used for HTTP Forbidden(403) Errors
    """


class NotFoundException(HttpErrorException):
    """
    Used for HTTP Not Found(404) Errors
    """


class RateLimitedException(HttpErrorException):
    """
    Used for HTTP Rate Limited(429) Errors
    """


class InternalServerErrorException(HttpErrorException):
    """
    Used for HTTP Internal Server Error(500) Errors
    """
