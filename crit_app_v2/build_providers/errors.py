"""Typed errors raised while validating and loading external builds."""

from enum import StrEnum

from crit_app_v2.build_providers.models import BuildProvider


class BuildErrorCategory(StrEnum):
    """Stable categories for build URL and provider failures."""

    INVALID_URL = "invalid_url"
    REJECTED = "rejected"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    UNEXPECTED_RESPONSE = "unexpected_response"


class BuildProviderError(Exception):
    """A normalized build-loading error safe to pass to presentation layers."""

    def __init__(
        self,
        category: BuildErrorCategory,
        provider: BuildProvider | None = None,
        status_code: int | None = None,
    ) -> None:
        """Create a normalized error with optional provider response details.

        Parameters
        ----------
        category
            Stable application-level category for the failure.
        provider
            Provider associated with the failure, if known.
        status_code
            HTTP response status when the failure came from an HTTP response.
        """
        self.category = category
        self.provider = provider
        self.status_code = status_code
        super().__init__(category.value)
