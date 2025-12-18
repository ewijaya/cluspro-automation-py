"""Tests for the auth module."""

import pytest

from cluspro.auth import (
    AuthenticationError,
    Credentials,
    CredentialSource,
    get_credentials,
    has_credentials,
    _get_credentials_from_env,
    _get_credentials_from_config,
)


class TestCredentials:
    """Tests for the Credentials dataclass."""

    def test_credentials_creation(self):
        """Test creating a Credentials object."""
        creds = Credentials(
            username="testuser",
            password="testpass",
            source=CredentialSource.ENVIRONMENT,
        )
        assert creds.username == "testuser"
        assert creds.password == "testpass"
        assert creds.source == CredentialSource.ENVIRONMENT


class TestCredentialSource:
    """Tests for CredentialSource enum."""

    def test_credential_source_values(self):
        """Test CredentialSource enum values."""
        assert CredentialSource.ENVIRONMENT.value == "environment"
        assert CredentialSource.CONFIG.value == "config"
        assert CredentialSource.INTERACTIVE.value == "interactive"
        assert CredentialSource.NONE.value == "none"


class TestGetCredentialsFromEnv:
    """Tests for _get_credentials_from_env."""

    def test_credentials_from_env_both_set(self, monkeypatch):
        """Test credentials loaded when both env vars are set."""
        monkeypatch.setenv("CLUSPRO_USERNAME", "envuser")
        monkeypatch.setenv("CLUSPRO_PASSWORD", "envpass")

        creds = _get_credentials_from_env()

        assert creds is not None
        assert creds.username == "envuser"
        assert creds.password == "envpass"
        assert creds.source == CredentialSource.ENVIRONMENT

    def test_credentials_from_env_only_username(self, monkeypatch):
        """Test returns None when only username is set."""
        monkeypatch.setenv("CLUSPRO_USERNAME", "envuser")
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        creds = _get_credentials_from_env()
        assert creds is None

    def test_credentials_from_env_only_password(self, monkeypatch):
        """Test returns None when only password is set."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.setenv("CLUSPRO_PASSWORD", "envpass")

        creds = _get_credentials_from_env()
        assert creds is None

    def test_credentials_from_env_neither_set(self, monkeypatch):
        """Test returns None when neither env var is set."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        creds = _get_credentials_from_env()
        assert creds is None


class TestGetCredentialsFromConfig:
    """Tests for _get_credentials_from_config."""

    def test_credentials_from_config_both_set(self):
        """Test credentials loaded from config when both are set."""
        config = {
            "credentials": {
                "username": "configuser",
                "password": "configpass",
            }
        }

        creds = _get_credentials_from_config(config)

        assert creds is not None
        assert creds.username == "configuser"
        assert creds.password == "configpass"
        assert creds.source == CredentialSource.CONFIG

    def test_credentials_from_config_only_username(self):
        """Test returns None when only username is in config."""
        config = {
            "credentials": {
                "username": "configuser",
            }
        }

        creds = _get_credentials_from_config(config)
        assert creds is None

    def test_credentials_from_config_only_password(self):
        """Test returns None when only password is in config."""
        config = {
            "credentials": {
                "password": "configpass",
            }
        }

        creds = _get_credentials_from_config(config)
        assert creds is None

    def test_credentials_from_config_empty_credentials(self):
        """Test returns None when credentials section is empty."""
        config = {"credentials": {}}

        creds = _get_credentials_from_config(config)
        assert creds is None

    def test_credentials_from_config_no_credentials_section(self):
        """Test returns None when credentials section is missing."""
        config = {"other": "config"}

        creds = _get_credentials_from_config(config)
        assert creds is None


class TestGetCredentials:
    """Tests for get_credentials."""

    def test_env_takes_priority_over_config(self, monkeypatch):
        """Test environment variables take priority over config."""
        monkeypatch.setenv("CLUSPRO_USERNAME", "envuser")
        monkeypatch.setenv("CLUSPRO_PASSWORD", "envpass")

        config = {
            "credentials": {
                "username": "configuser",
                "password": "configpass",
            }
        }

        creds = get_credentials(config=config, interactive=False)

        assert creds is not None
        assert creds.username == "envuser"
        assert creds.source == CredentialSource.ENVIRONMENT

    def test_falls_back_to_config(self, monkeypatch):
        """Test falls back to config when env vars not set."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        config = {
            "credentials": {
                "username": "configuser",
                "password": "configpass",
            }
        }

        creds = get_credentials(config=config, interactive=False)

        assert creds is not None
        assert creds.username == "configuser"
        assert creds.source == CredentialSource.CONFIG

    def test_returns_none_when_no_credentials(self, monkeypatch):
        """Test returns None when no credentials available and interactive=False."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        creds = get_credentials(config={}, interactive=False)
        assert creds is None

    def test_interactive_prompt(self, monkeypatch, mocker):
        """Test interactive prompt when enabled."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        # Mock click.prompt to return test values
        mocker.patch("click.prompt", side_effect=["promptuser", "promptpass"])
        mocker.patch("click.echo")

        creds = get_credentials(config={}, interactive=True)

        assert creds is not None
        assert creds.username == "promptuser"
        assert creds.password == "promptpass"
        assert creds.source == CredentialSource.INTERACTIVE


class TestHasCredentials:
    """Tests for has_credentials."""

    def test_has_credentials_from_env(self, monkeypatch):
        """Test returns True when env vars are set."""
        monkeypatch.setenv("CLUSPRO_USERNAME", "user")
        monkeypatch.setenv("CLUSPRO_PASSWORD", "pass")

        assert has_credentials() is True

    def test_has_credentials_from_config(self, monkeypatch):
        """Test returns True when config has credentials."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        config = {
            "credentials": {
                "username": "user",
                "password": "pass",
            }
        }

        assert has_credentials(config=config) is True

    def test_has_credentials_false_when_none(self, monkeypatch):
        """Test returns False when no credentials available."""
        monkeypatch.delenv("CLUSPRO_USERNAME", raising=False)
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        assert has_credentials(config={}) is False

    def test_has_credentials_false_partial_env(self, monkeypatch):
        """Test returns False when only partial env vars set."""
        monkeypatch.setenv("CLUSPRO_USERNAME", "user")
        monkeypatch.delenv("CLUSPRO_PASSWORD", raising=False)

        assert has_credentials(config={}) is False


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_authentication_error_message(self):
        """Test AuthenticationError can be raised with message."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Login failed")

        assert "Login failed" in str(exc_info.value)
