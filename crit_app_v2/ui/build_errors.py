"""Presentation messages for normalized build-provider errors."""

from crit_app_v2.build_providers import (
    BuildErrorCategory,
    BuildProvider,
    BuildProviderError,
)


def build_error_message(error: BuildProviderError) -> str:
    """Return concise feedback for a normalized build-loading failure."""
    if error.category is BuildErrorCategory.INVALID_URL:
        return "Invalid or unsupported URL. Enter a valid Etro or XIVGear build URL."

    provider = error.provider
    provider_name = (
        {
            BuildProvider.ETRO: "Etro",
            BuildProvider.XIV_GEAR: "XIVGear",
        }.get(provider)
        if provider is not None
        else None
    )

    if error.category is BuildErrorCategory.REJECTED:
        if provider_name is None:
            return "The build URL or build was rejected. Check the link and try again."
        return (
            f"{provider_name} rejected this URL or build. "
            "Check that you copied the full gearset link."
        )

    if error.category is BuildErrorCategory.PROVIDER_UNAVAILABLE:
        if error.provider is BuildProvider.XIV_GEAR:
            if error.status_code in (408, 429):
                return "XIVGear is temporarily unavailable. Please try again later."
            if error.status_code is not None and error.status_code >= 500:
                return (
                    "XIVGear couldn't load this build. Check the link or try again "
                    "later."
                )
        return f"Could not reach {provider_name or 'the build provider'}. Please try again later."

    return (
        f"{provider_name or 'The build provider'} returned an unexpected response. "
        "Please try again later."
    )
