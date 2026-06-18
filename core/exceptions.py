"""
Temu Open Platform API — Exceptions typées

Hiérarchie :
    TemuAPIError
    ├── AuthError        401 / 403 / signature invalide
    ├── RateLimitError   429 / quota dépassé
    ├── NotFoundError    404
    ├── ServerError      5xx
    └── NetworkError     timeout, connexion perdue

Auteur  : Allan ABATUCI
Modifié : 2026-06-09
"""


class TemuAPIError(Exception):
    """Base de toutes les erreurs Temu. Toujours capturer celle-ci en dernier recours."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: str | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code   = status_code
        self.error_code    = error_code
        self.response_body = response_body

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"status_code={self.status_code!r}, "
            f"error_code={self.error_code!r}, "
            f"message={str(self)!r})"
        )


class AuthError(TemuAPIError):
    """Credentials invalides, signature incorrecte, ou token expiré (401/403)."""


class RateLimitError(TemuAPIError):
    """Quota d'appels API dépassé (429). Contient retry_after si fourni."""

    def __init__(self, message: str, retry_after: int | None = None, **kwargs) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NotFoundError(TemuAPIError):
    """Ressource introuvable (404)."""


class ServerError(TemuAPIError):
    """Erreur serveur Temu (5xx)."""


class NetworkError(TemuAPIError):
    """Erreur réseau bas niveau (timeout, connexion interrompue)."""
