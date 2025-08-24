from unittest.mock import MagicMock, patch

import pytest

import coleta_spotify as cs


def make_resp(status=200, text='ok', headers=None):
    m = MagicMock()
    m.status_code = status
    m.text = text
    m.json.return_value = {'ok': True} if status == 200 else {}
    m.headers = headers or {}
    return m


@patch('coleta_spotify.requests.request')
def test_retry_on_500_then_success(mock_request):
    # first call 500, second call 200
    mock_request.side_effect = [
        make_resp(500, 'server error'), make_resp(200, 'ok')]
    resp = cs._request_with_retry('get', 'http://example.test')
    assert resp is not None
    assert resp.status_code == 200


@patch('coleta_spotify.requests.request')
def test_retry_on_429_with_retry_after(mock_request):
    # first call 429 with Retry-After=1, second 200
    mock_request.side_effect = [make_resp(429, 'rate limited', headers={
                                          'Retry-After': '1'}), make_resp(200, 'ok')]
    resp = cs._request_with_retry('get', 'http://example.test')
    assert resp is not None
    assert resp.status_code == 200


@patch('coleta_spotify.requests.request')
def test_request_exception_then_success(mock_request):
    # first raises RequestException, second returns 200
    from requests import RequestException
    mock_request.side_effect = [RequestException(
        'conn fail'), make_resp(200, 'ok')]
    resp = cs._request_with_retry('get', 'http://example.test')
    assert resp is not None
    assert resp.status_code == 200
