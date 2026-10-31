"""UniFi Integration API client against a local fake controller."""

import json

import aiohttp
from aiohttp import web
import pytest

from custom_components.ms_lumio.unifi import (
    UnifiAuthError,
    UnifiClient,
    UnifiConnectionError,
    extract_vouchers,
)


@pytest.fixture
async def controller():
    """HTTP stand-in for the UDM integration API."""
    state = {"requests": []}

    async def info(request: web.Request) -> web.Response:
        state["requests"].append(("info", request.path, request.headers.get("X-API-KEY")))
        if request.headers.get("X-API-KEY") != "test-api-key":
            return web.Response(status=401, text="no")
        return web.json_response({"application": "network"})

    async def missing(request: web.Request) -> web.Response:
        state["requests"].append(("missing", request.path, None))
        return web.Response(status=404, text="no")

    async def sites(request: web.Request) -> web.Response:
        _assert_key(request)
        return web.json_response(
            {"offset": 0, "limit": 25, "count": 1, "totalCount": 1, "data": [{"id": "site-1", "name": "Default"}]}
        )

    async def vouchers(request: web.Request) -> web.Response:
        _assert_key(request)
        raw = await request.text()
        state["requests"].append((request.method, str(request.url), raw))
        if request.method == "POST":
            payload = json.loads(raw)
            assert payload["count"] == 1
            assert payload["name"] == "Jean Dupont 2026-07-10/2026-07-17"
            assert payload["timeLimitMinutes"] == 11520
            assert payload["authorizedGuestLimit"] == 10
            assert payload["rxRateLimitKbps"] == 100000
            assert payload["txRateLimitKbps"] == 100000
            assert "test-api-key" not in str(request.url)
            return web.json_response(
                {
                    "vouchers": [
                        {
                            "id": "voucher-1",
                            "code": "ABCD12",
                            "name": payload["name"],
                            "timeLimitMinutes": payload["timeLimitMinutes"],
                            "authorizedGuestLimit": 10,
                            "rxRateLimitKbps": 100000,
                            "txRateLimitKbps": 100000,
                        }
                    ]
                },
                status=201,
            )
        if request.method == "DELETE":
            if request.match_info.get("voucher_id") == "missing":
                return web.Response(status=404)
            return web.Response(status=204)
        offset = int(request.query.get("offset", "0"))
        if offset == 0:
            return web.json_response(
                {
                    "offset": 0,
                    "limit": 200,
                    "totalCount": 2,
                    "data": [{"id": "v1", "code": "AAAA", "name": "one"}],
                }
            )
        return web.json_response(
            {
                "offset": offset,
                "limit": 200,
                "totalCount": 2,
                "data": [{"id": "v2", "code": "BBBB", "name": "two"}],
            }
        )

    async def redirect(request: web.Request) -> web.Response:
        state["requests"].append(("redirect", request.path, request.headers.get("X-API-KEY")))
        raise web.HTTPFound(location="http://evil.example/steal")

    def _assert_key(request: web.Request) -> None:
        assert request.headers.get("X-API-KEY") == "test-api-key"
        assert "test-api-key" not in str(request.url)

    app = web.Application()
    app.router.add_get("/proxy/network/integration/v1/info", missing)
    app.router.add_get("/integration/v1/info", info)
    app.router.add_get("/integration/v1/sites", sites)
    app.router.add_route("*", "/integration/v1/sites/{site_id}/hotspot/vouchers", vouchers)
    app.router.add_route(
        "*", "/integration/v1/sites/{site_id}/hotspot/vouchers/{voucher_id}", vouchers
    )
    app.router.add_get("/redirect/v1/info", redirect)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield port, state
    finally:
        await runner.cleanup()


def _client(session: aiohttp.ClientSession, port: int, **kwargs: object) -> UnifiClient:
    params = {
        "host": "127.0.0.1",
        "port": port,
        "api_key": "test-api-key",
        "verify_ssl": False,
        "site_id": "site-1",
        "scheme": "http",
    }
    params.update(kwargs)
    return UnifiClient(session, **params)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_probe_falls_back_to_the_second_prefix(controller):
    port, state = controller
    async with aiohttp.ClientSession() as session:
        client = _client(session, port)
        prefix = await client.async_probe_base_path()
    assert prefix == "/integration"
    assert state["requests"][0][1].endswith("/proxy/network/integration/v1/info")
    assert state["requests"][1][1].endswith("/integration/v1/info")


@pytest.mark.asyncio
async def test_create_list_and_delete_roundtrip(controller):
    port, _state = controller
    async with aiohttp.ClientSession() as session:
        client = _client(session, port, base_path="/integration")
        sites = await client.async_list_sites()
        assert [(site.id, site.name) for site in sites] == [("site-1", "Default")]
        created = await client.async_create_voucher(
            name="Jean Dupont 2026-07-10/2026-07-17",
            time_limit_minutes=11520,
            authorized_guest_limit=10,
            rx_rate_limit_kbps=100000,
            tx_rate_limit_kbps=100000,
        )
        assert created.code == "ABCD12"
        listed = await client.async_list_vouchers()
        assert [voucher.id for voucher in listed] == ["v1", "v2"]
        await client.async_delete_voucher("missing")


@pytest.mark.asyncio
async def test_rejected_key_and_redirect(controller):
    port, state = controller
    async with aiohttp.ClientSession() as session:
        client = _client(session, port, api_key="wrong-key", base_path="/integration")
        with pytest.raises(UnifiAuthError):
            await client.async_get_info()
        redirected = _client(session, port, base_path="/redirect")
        with pytest.raises(UnifiConnectionError) as caught:
            await redirected.async_get_info()
    assert str(caught.value) == "redirect_refused"
    assert not any(path.startswith("http://evil") for _, path, _ in state["requests"])


def test_tls_verification_flag_and_envelopes():
    client = UnifiClient(
        None,  # type: ignore[arg-type]
        host="192.168.1.1",
        port=443,
        api_key="secret",
        verify_ssl=False,
    )
    assert client._ssl() is False
    client.verify_ssl = True
    assert client._ssl() is None
    parsed = extract_vouchers(
        {"data": [{"id": "abc", "code": "ZZ", "name": "note"}]}
    )
    assert parsed[0].code == "ZZ"


def test_api_key_is_not_part_of_the_url():
    client = UnifiClient(
        None,  # type: ignore[arg-type]
        host="192.168.1.1",
        port=443,
        api_key="super-secret-key",
        verify_ssl=True,
        base_path="/proxy/network/integration",
        site_id="site",
    )
    url = client._url("/v1/sites/site/hotspot/vouchers")
    assert "super-secret-key" not in url
    assert url.startswith("https://192.168.1.1:443/proxy/network/integration/v1/")
