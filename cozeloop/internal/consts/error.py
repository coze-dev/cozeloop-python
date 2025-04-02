# Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

from pydantic import BaseModel


class LoopError(Exception):
    """
    Base class for all exceptions raised by the loop package.
    """


class InvalidParamError(LoopError):
    """
    Invalid parameter error.
    """
    def __init__(self, detail: str = "") -> None:
        super().__init__("Invalid parameter" + (f". {detail}" if detail else ""))


class AuthInfoRequiredError(LoopError):
    """
    Auth info required error.
    """
    def __init__(self):
        super().__init__("Api token or jwt oauth info is required.")


class InternalError(LoopError):
    """
    Internal error.
    """
    def __init__(self, detail: str = "") -> None:
        super().__init__("Internal error occurred" + (f". {detail}" if detail else ""))


class ParsePrivateKeyError(LoopError):
    """
    Failed to parse private key error.
    """
    def __init__(self):
        super().__init__("Failed to parse private key.")


class HeaderParentError(LoopError):
    """
    Invalid header parent error.
    """
    def __init__(self):
        super().__init__("Invalid traceparent header.")


class NetworkError(LoopError):
    """
    Network error.
    """
    def __init__(self):
        super().__init__("Network error occurred.")


class ClientClosedError(LoopError):
    """
    Noop client not supported error.
    """
    def __init__(self):
        super().__init__("Client is already closed.")


class RemoteServiceError(LoopError):
    """
    Call remote services errors.
    """
    def __init__(self, http_code: int, error_code: int, error_message: str, log_id: str):
        """
        Initialize a RemoteServiceError instance.

        :param http_code: HTTP status code
        :param error_code: Error code
        :param error_message: Error message
        :param log_id: Log ID for debugging
        """
        self.http_code = http_code
        self.error_code = error_code
        self.error_message = error_message
        self.log_id = log_id
        super().__init__(self.__str__())

    def __str__(self):
        """
        Return a string representation of the error.

        :return: A formatted string with all error information.
        """
        return (f"remote service error, {self.error_message} [http_code={self.http_code} error_code={self.error_code} "
                f"logid={self.log_id}]")


class AuthErrorFormat(BaseModel):
    """
    Represents the authentication error format returned by the Coze API.
    """
    error_message: str
    error_code: str
    error: str


# Enums for error code in AuthErrorFormat
# The user has not completed authorization yet, please try again later
AUTHORIZATION_PENDING = "authorization_pending"
# The request is too frequent, please try again later
SLOW_DOWN = "slow_down"
# The user has denied the authorization
ACCESS_DENIED = "access_denied"
# The token is expired
EXPIRED_TOKEN = "expired_token"


class AuthError(LoopError):
    """
    Authentication error.
    """
    def __init__(self, auth_err: AuthErrorFormat, http_code: int, log_id: str):
        self.http_code = http_code
        self.error_message = auth_err.error_message
        self.code = auth_err.error_code
        self.params = auth_err.error
        self.log_id = log_id
        super().__init__(self.__str__())

    def __str__(self):
        """
        Return a string representation of the authentication error.

        :return: A formatted string with all error information.
        """
        return (f"authentication error, {self.error_message} [httpcode={self.http_code} code={self.code} "
                f"param={self.params} logid={self.log_id}]")

