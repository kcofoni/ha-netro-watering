"""Tests for http_client.py classes and functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.netro_watering.http_client import (
    AiohttpClient,
    AiohttpResponse,
    AiohttpResponseContextManager,
    _mask_key_in_kwargs,
)


class TestAiohttpResponse:
    """Test suite for AiohttpResponse class."""

    @pytest.fixture
    def mock_aiohttp_response(self):
        """Create a mock aiohttp.ClientResponse."""
        mock_response = MagicMock(spec=aiohttp.ClientResponse)
        mock_response.status = 200
        mock_response.json = AsyncMock()
        mock_response.text = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.close = MagicMock()
        return mock_response

    def test_aiohttpresponse_init(self, mock_aiohttp_response, snapshot):
        """Test AiohttpResponse initialization."""
        response = AiohttpResponse(mock_aiohttp_response)

        result = {
            "status": response.status,
            "has_response": response._response is mock_aiohttp_response,
        }

        assert result == snapshot

    async def test_aiohttpresponse_json_simple_data(
        self, mock_aiohttp_response, snapshot
    ):
        """Test AiohttpResponse.json() with simple data."""
        test_data = {"message": "success", "data": [1, 2, 3]}
        mock_aiohttp_response.json.return_value = test_data

        response = AiohttpResponse(mock_aiohttp_response)

        with patch(
            "custom_components.netro_watering.http_client._LOGGER"
        ) as mock_logger:
            result = await response.json()

            assert result == test_data
            mock_logger.debug.assert_called_once()
            log_call_args = mock_logger.debug.call_args[0]

            result_data = {
                "returned_data": result,
                "log_message_template": log_call_args[0],
                "logged_data": log_call_args[1],
            }

            assert result_data == snapshot

    async def test_aiohttpresponse_json_with_sensitive_keys(
        self, mock_aiohttp_response, snapshot
    ):
        """Test AiohttpResponse.json() masks sensitive Netro keys."""
        test_data = {
            "serial": "ABC123456789",
            "key": "secret_api_key_12345",
            "message": "success",
            "devices": [
                {"serial": "DEF987654321", "name": "Controller1"},
                {"key": "another_secret", "id": 42},
            ],
            "nested": {
                "serial": "nested_serial",
                "key": "nested_key",
                "data": "normal_data",
            },
        }
        mock_aiohttp_response.json.return_value = test_data

        response = AiohttpResponse(mock_aiohttp_response)

        with patch(
            "custom_components.netro_watering.http_client._LOGGER"
        ) as mock_logger:
            result = await response.json()

            # Original data should be returned unchanged
            assert result == test_data

            # But logged data should be masked
            mock_logger.debug.assert_called_once()
            log_call_args = mock_logger.debug.call_args[0]
            logged_data = log_call_args[1]

            result_data = {
                "original_data_unchanged": result == test_data,
                "logged_data": logged_data,
                "sensitive_keys_masked": {
                    "serial_masked": "***" in str(logged_data),
                    "key_masked": "***" in str(logged_data),
                },
            }

            assert result_data == snapshot

    async def test_aiohttpresponse_text(self, mock_aiohttp_response, snapshot):
        """Test AiohttpResponse.text() method."""
        test_text = "This is a text response"
        mock_aiohttp_response.text.return_value = test_text

        response = AiohttpResponse(mock_aiohttp_response)
        result = await response.text()

        assert result == snapshot

    def test_aiohttpresponse_raise_for_status(self, mock_aiohttp_response, snapshot):
        """Test AiohttpResponse.raise_for_status() method."""
        response = AiohttpResponse(mock_aiohttp_response)

        # Should not raise when no exception
        response.raise_for_status()
        mock_aiohttp_response.raise_for_status.assert_called_once()

        # Test when raises exception
        mock_aiohttp_response.raise_for_status.side_effect = (
            aiohttp.ClientResponseError(
                request_info=MagicMock(), history=(), status=404, message="Not Found"
            )
        )

        with pytest.raises(aiohttp.ClientResponseError):
            response.raise_for_status()

        result = {
            "raise_for_status_called": mock_aiohttp_response.raise_for_status.call_count
            == 2,
            "exception_propagated": True,
        }

        assert result == snapshot

    async def test_aiohttpresponse_context_manager(
        self, mock_aiohttp_response, snapshot
    ):
        """Test AiohttpResponse as context manager."""
        response = AiohttpResponse(mock_aiohttp_response)

        async with response as ctx_response:
            assert ctx_response is response

        # Check that close was called on exit
        mock_aiohttp_response.close.assert_called_once()

        result = {
            "context_manager_works": True,
            "close_called_on_exit": mock_aiohttp_response.close.call_count == 1,
        }

        assert result == snapshot


class TestAiohttpClient:
    """Test suite for AiohttpClient class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock aiohttp.ClientSession."""
        session = AsyncMock(spec=aiohttp.ClientSession)
        session.get = MagicMock()
        session.post = MagicMock()
        session.put = MagicMock()
        session.delete = MagicMock()
        session.close = AsyncMock()
        return session

    def test_aiohttpclient_init_with_session(self, mock_session, snapshot):
        """Test AiohttpClient initialization with provided session."""
        client = AiohttpClient(session=mock_session)

        result = {
            "session_is_provided": client._session is mock_session,
            "own_session_flag": client._own_session,
        }

        assert result == snapshot

    def test_aiohttpclient_init_without_session(self, snapshot):
        """Test AiohttpClient initialization without session."""
        client = AiohttpClient()

        result = {
            "session_is_none": client._session is None,
            "own_session_flag": client._own_session,
        }

        assert result == snapshot

    async def test_aiohttpclient_context_manager_own_session(self, snapshot):
        """Test AiohttpClient as context manager when it creates its own session."""
        client = AiohttpClient()  # No session provided

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session_class.return_value = mock_session

            async with client as ctx_client:
                assert ctx_client is client
                assert client._session is mock_session

            # Session should be closed on exit
            mock_session.close.assert_called_once()

        result = {
            "context_manager_works": True,
            "session_created": True,
            "session_closed": True,
        }

        assert result == snapshot

    async def test_aiohttpclient_context_manager_provided_session(
        self, mock_session, snapshot
    ):
        """Test AiohttpClient as context manager with provided session."""
        client = AiohttpClient(session=mock_session)

        async with client as ctx_client:
            assert ctx_client is client
            assert client._session is mock_session

        # Provided session should NOT be closed
        mock_session.close.assert_not_called()

        result = {
            "context_manager_works": True,
            "provided_session_not_closed": mock_session.close.call_count == 0,
        }

        assert result == snapshot

    def test_aiohttpclient_get_without_session(self, snapshot):
        """Test AiohttpClient.get() without initialized session."""
        client = AiohttpClient()

        with pytest.raises(RuntimeError) as exc_info:
            client.get("http://example.com")

        result = {
            "error_message": str(exc_info.value),
            "error_type": type(exc_info.value).__name__,
        }

        assert result == snapshot

    def test_aiohttpclient_get_with_session(self, mock_session, snapshot):
        """Test AiohttpClient.get() with session."""
        client = AiohttpClient(session=mock_session)

        # Mock the session.get to return a coroutine
        mock_coro = AsyncMock()
        mock_session.get.return_value = mock_coro

        with patch(
            "custom_components.netro_watering.http_client._LOGGER"
        ) as mock_logger:
            result = client.get("http://example.com", params={"test": "value"})

            # Should return AiohttpResponseContextManager
            assert isinstance(result, AiohttpResponseContextManager)

            # Session.get should be called with adapted kwargs
            mock_session.get.assert_called_once()
            call_args = mock_session.get.call_args

            result_data = {
                "url": call_args[0][0],
                "kwargs_keys": list(call_args[1].keys()),
                "logger_called": mock_logger.debug.called,
            }

            assert result_data == snapshot

    def test_aiohttpclient_post_with_json(self, mock_session, snapshot):
        """Test AiohttpClient.post() with JSON data."""
        client = AiohttpClient(session=mock_session)

        mock_coro = AsyncMock()
        mock_session.post.return_value = mock_coro

        test_data = {"key": "secret123", "data": "test"}

        with patch(
            "custom_components.netro_watering.http_client._LOGGER"
        ) as mock_logger:
            result = client.post("http://example.com", json=test_data)

            assert isinstance(result, AiohttpResponseContextManager)

            # Check that logging masks sensitive data
            mock_logger.debug.assert_called_once()
            log_args = mock_logger.debug.call_args[0]

            result_data = {
                "method_called": "POST",
                "log_contains_masked_key": "***" in str(log_args),
                "session_post_called": mock_session.post.called,
            }

            assert result_data == snapshot

    def test_aiohttpclient_put_method(self, mock_session, snapshot):
        """Test AiohttpClient.put() method."""
        client = AiohttpClient(session=mock_session)

        mock_coro = AsyncMock()
        mock_session.put.return_value = mock_coro

        with patch(
            "custom_components.netro_watering.http_client._LOGGER"
        ) as mock_logger:
            result = client.put("http://example.com", json={"update": "data"})

            assert isinstance(result, AiohttpResponseContextManager)
            mock_session.put.assert_called_once()

            result_data = {
                "method_called": "PUT",
                "session_put_called": mock_session.put.called,
                "logger_called": mock_logger.debug.called,
            }

            assert result_data == snapshot

    def test_aiohttpclient_delete_method(self, mock_session, snapshot):
        """Test AiohttpClient.delete() method."""
        client = AiohttpClient(session=mock_session)

        mock_coro = AsyncMock()
        mock_session.delete.return_value = mock_coro

        with patch(
            "custom_components.netro_watering.http_client._LOGGER"
        ) as mock_logger:
            result = client.delete("http://example.com", params={"id": "123"})

            assert isinstance(result, AiohttpResponseContextManager)
            mock_session.delete.assert_called_once()

            result_data = {
                "method_called": "DELETE",
                "session_delete_called": mock_session.delete.called,
                "logger_called": mock_logger.debug.called,
            }

            assert result_data == snapshot

    def test_aiohttpclient_all_methods_without_session_error(self, snapshot):
        """Test that all HTTP methods raise RuntimeError without session."""
        client = AiohttpClient()

        methods_to_test = [
            ("get", lambda: client.get("http://example.com")),
            ("post", lambda: client.post("http://example.com")),
            ("put", lambda: client.put("http://example.com")),
            ("delete", lambda: client.delete("http://example.com")),
        ]

        results = []
        for method_name, method_call in methods_to_test:
            with pytest.raises(RuntimeError) as exc_info:
                method_call()

            results.append(
                {
                    "method": method_name,
                    "error_message": str(exc_info.value),
                    "error_type": type(exc_info.value).__name__,
                }
            )

        assert results == snapshot

    def test_aiohttpclient_adapt_kwargs(self, mock_session, snapshot):
        """Test AiohttpClient._adapt_kwargs() method."""
        client = AiohttpClient(session=mock_session)

        input_kwargs = {
            "headers": {"Content-Type": "application/json"},
            "params": {"test": "value"},
            "timeout": 30,
            "json": {"data": "test"},
            "data": "raw_data",
            "unknown_param": "should_be_ignored",
        }

        result = client._adapt_kwargs(input_kwargs)

        # Check that timeout is converted to ClientTimeout
        timeout_obj = result.get("timeout")
        has_correct_timeout = (
            timeout_obj is not None
            and hasattr(timeout_obj, "total")
            and timeout_obj.total == 30
        )

        result_data = {
            "headers": result.get("headers"),
            "params": result.get("params"),
            "json": result.get("json"),
            "data": result.get("data"),
            "has_timeout_object": has_correct_timeout,
            "unknown_param_ignored": "unknown_param" not in result,
            "result_keys": sorted(result.keys()),
        }

        assert result_data == snapshot


class TestAiohttpResponseContextManager:
    """Test suite for AiohttpResponseContextManager class."""

    async def test_response_context_manager(self, snapshot):
        """Test AiohttpResponseContextManager functionality."""
        # Create mock coroutine that returns a mock aiohttp response
        mock_aiohttp_response = MagicMock(spec=aiohttp.ClientResponse)
        mock_aiohttp_response.status = 200

        mock_coro = AsyncMock()
        mock_coro.__aenter__ = AsyncMock(return_value=mock_aiohttp_response)
        mock_coro.__aexit__ = AsyncMock()

        ctx_manager = AiohttpResponseContextManager(mock_coro)

        async with ctx_manager as response:
            assert isinstance(response, AiohttpResponse)
            assert response.status == 200
            assert response._response is mock_aiohttp_response

        # Check that both context managers were properly called
        mock_coro.__aenter__.assert_called_once()
        mock_coro.__aexit__.assert_called_once()

        result = {
            "context_manager_works": True,
            "returns_aiohttpresponse": True,
            "status_correct": True,
            "cleanup_called": True,
        }

        assert result == snapshot


class TestMaskKeyInKwargs:
    """Test suite for _mask_key_in_kwargs function."""

    def test_mask_key_in_kwargs_no_sensitive_data(self, snapshot):
        """Test _mask_key_in_kwargs with no sensitive data."""
        kwargs = {
            "headers": {"Content-Type": "application/json"},
            "params": {"test": "value"},
            "data": "some data",
        }

        result = _mask_key_in_kwargs(kwargs)

        # Should return a copy with no changes
        assert result == kwargs
        assert result is not kwargs  # Should be a copy
        assert result == snapshot

    def test_mask_key_in_kwargs_with_json_key(self, snapshot):
        """Test _mask_key_in_kwargs masks key in json data."""
        kwargs = {
            "json": {
                "key": "secret_api_key_12345",
                "data": "normal_data",
                "serial": "not_masked_here",  # Only 'key' is masked in json
            },
            "params": {"test": "value"},
        }

        result = _mask_key_in_kwargs(kwargs)

        # Original should be unchanged
        assert kwargs["json"]["key"] == "secret_api_key_12345"

        # Result should have masked key
        result_data = {
            "original_unchanged": kwargs["json"]["key"] == "secret_api_key_12345",
            "result_key_masked": "***" in result["json"]["key"],
            "other_json_data_unchanged": result["json"]["data"] == "normal_data",
            "serial_not_masked": result["json"]["serial"] == "not_masked_here",
            "params_unchanged": result["params"] == kwargs["params"],
            "is_copy": result is not kwargs,
        }

        assert result_data == snapshot

    def test_mask_key_in_kwargs_with_params_key(self, snapshot):
        """Test _mask_key_in_kwargs masks key in params data."""
        kwargs = {
            "params": {
                "key": "secret_param_key",
                "other": "value",
            },
            "json": {"data": "test"},
        }

        result = _mask_key_in_kwargs(kwargs)

        # Original should be unchanged
        assert kwargs["params"]["key"] == "secret_param_key"

        result_data = {
            "original_unchanged": kwargs["params"]["key"] == "secret_param_key",
            "result_key_masked": "***" in result["params"]["key"],
            "other_params_unchanged": result["params"]["other"] == "value",
            "json_unchanged": result["json"] == kwargs["json"],
            "is_copy": result is not kwargs,
        }

        assert result_data == snapshot

    def test_mask_key_in_kwargs_both_json_and_params(self, snapshot):
        """Test _mask_key_in_kwargs with keys in both json and params."""
        kwargs = {
            "json": {"key": "json_secret_key", "data": "test"},
            "params": {"key": "params_secret_key", "other": "value"},
            "headers": {"Content-Type": "application/json"},
        }

        result = _mask_key_in_kwargs(kwargs)

        result_data = {
            "json_key_masked": "***" in result["json"]["key"],
            "params_key_masked": "***" in result["params"]["key"],
            "json_data_unchanged": result["json"]["data"] == "test",
            "params_other_unchanged": result["params"]["other"] == "value",
            "headers_unchanged": result["headers"] == kwargs["headers"],
            "originals_unchanged": (
                kwargs["json"]["key"] == "json_secret_key"
                and kwargs["params"]["key"] == "params_secret_key"
            ),
        }

        assert result_data == snapshot

    def test_mask_key_in_kwargs_edge_cases(self, snapshot):
        """Test _mask_key_in_kwargs with edge cases."""
        test_cases = [
            # Non-dict json
            {"json": "not_a_dict", "params": {"test": "value"}},
            # Non-dict params
            {"json": {"key": "secret"}, "params": "not_a_dict"},
            # Empty dicts
            {"json": {}, "params": {}},
            # No json or params
            {"headers": {"test": "value"}},
        ]

        results = []
        for i, kwargs in enumerate(test_cases):
            result = _mask_key_in_kwargs(kwargs)
            results.append(
                {
                    "case": i,
                    "input": kwargs,
                    "output": result,
                    "is_copy": result is not kwargs,
                    "unchanged": result == kwargs,
                }
            )

        assert results == snapshot
