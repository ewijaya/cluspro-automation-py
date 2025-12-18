"""
Authentication module for ClusPro automation.

Handles credential management and authentication methods.
Supports multiple credential sources with priority:
1. Environment variables (CLUSPRO_USERNAME, CLUSPRO_PASSWORD)
2. Configuration file (~/.cluspro/settings.yaml)
3. Interactive prompt
"""

import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import click

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class CredentialSource(Enum):
    """Tracks where credentials came from."""

    ENVIRONMENT = "environment"
    CONFIG = "config"
    INTERACTIVE = "interactive"
    NONE = "none"


@dataclass
class Credentials:
    """Container for ClusPro credentials."""

    username: str
    password: str
    source: CredentialSource


def _get_credentials_from_env() -> Optional[Credentials]:
    """
    Get credentials from environment variables.

    Looks for CLUSPRO_USERNAME and CLUSPRO_PASSWORD.
    Both must be set for credentials to be returned.

    Returns:
        Credentials if both env vars are set, None otherwise
    """
    username = os.environ.get("CLUSPRO_USERNAME")
    password = os.environ.get("CLUSPRO_PASSWORD")

    if username and password:
        logger.debug("Credentials loaded from environment variables")
        return Credentials(
            username=username, password=password, source=CredentialSource.ENVIRONMENT
        )

    if username or password:
        logger.debug("Partial credentials in environment (both required)")

    return None


def _get_credentials_from_config(config: dict) -> Optional[Credentials]:
    """
    Get credentials from configuration dictionary.

    Looks for credentials.username and credentials.password in config.
    Both must be set for credentials to be returned.

    Args:
        config: Configuration dictionary

    Returns:
        Credentials if both config values are set, None otherwise
    """
    creds_config = config.get("credentials", {})
    username = creds_config.get("username")
    password = creds_config.get("password")

    if username and password:
        logger.debug("Credentials loaded from config file")
        return Credentials(
            username=username, password=password, source=CredentialSource.CONFIG
        )

    if username or password:
        logger.debug("Partial credentials in config (both required)")

    return None


def _get_credentials_interactive() -> Credentials:
    """
    Prompt user for credentials interactively.

    Uses click.prompt for username and password input.
    Password input is hidden.

    Returns:
        Credentials from user input
    """
    click.echo("ClusPro account login required.")
    username = click.prompt("Username")
    password = click.prompt("Password", hide_input=True)

    logger.debug("Credentials obtained via interactive prompt")
    return Credentials(
        username=username, password=password, source=CredentialSource.INTERACTIVE
    )


def get_credentials(
    config: Optional[dict] = None,
    interactive: bool = True,
) -> Optional[Credentials]:
    """
    Get credentials from available sources.

    Priority order:
    1. Environment variables (CLUSPRO_USERNAME, CLUSPRO_PASSWORD)
    2. Config file (credentials.username, credentials.password)
    3. Interactive prompt (if interactive=True)

    Args:
        config: Configuration dictionary (optional)
        interactive: Whether to prompt user if no credentials found (default: True)

    Returns:
        Credentials if available, None if not available and interactive=False

    Example:
        >>> creds = get_credentials(config=my_config)
        >>> if creds:
        ...     print(f"Using {creds.source.value} credentials")
    """
    # Try environment variables first
    creds = _get_credentials_from_env()
    if creds:
        return creds

    # Try config file
    if config:
        creds = _get_credentials_from_config(config)
        if creds:
            return creds

    # Interactive prompt as fallback
    if interactive:
        return _get_credentials_interactive()

    logger.debug("No credentials available")
    return None


def has_credentials(config: Optional[dict] = None) -> bool:
    """
    Check if credentials are available (without prompting).

    Checks environment variables and config file only.
    Does not prompt for interactive input.

    Args:
        config: Configuration dictionary (optional)

    Returns:
        True if credentials are available, False otherwise

    Example:
        >>> if has_credentials():
        ...     print("Account login available")
        ... else:
        ...     print("Using guest mode")
    """
    # Check environment
    if _get_credentials_from_env():
        return True

    # Check config
    if config and _get_credentials_from_config(config):
        return True

    return False
