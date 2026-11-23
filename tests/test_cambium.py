"""Cambium EasyPass voucher client against a local fake cnMaestro."""

import json

import aiohttp
from aiohttp import web
import pytest

from custom_components.usvegliu.cambium import (
    CambiumAuthError,
    CambiumClient,
    CambiumError,
    extract_vouchers,
)


@pytest.fixture
async def cloud():
    """HTTP stand-in for cnMaestro Cloud EasyPass."""
    state = {"requests": [], "token_ok": True, "vouchers": []}

    async def token(request: web.Request) -> web.Response:
        form = await request.post()
        state["requests"].append(("token", dict(form)))
        if not state["token_ok"]:
            return web.Response(status=401, text="no")
        assert form.get("grant_type") == "client_credentials"
        assert form.get("client_id") == "cid"
        assert form.get("client_secret") == "csecret"
        return web.json_response(
            {
                "access_token": "bearer-token",
                "redirect_uri": str(request.url.origin()),
            }
        )

    async def vouchers(request: web.Request) -> web.Response:
        auth = request.headers.get("Authorization", "")
        state["requests"].append((request.method, request.path, auth, await request.text()))
        if auth != "Bearer bearer-token":
            return web.Response(status=401, text="no")
        if request.method == "GET":
            return web.json_response({"data": list(state["vouchers"])})
        if request.path.endswith("/generate"):
            payload = json.loads(state["requests"][-1][3] or "{}")
            assert payload.get("count") == 1
            row = {
                "id": "cv-1",
                "code": "XY99ZZ",
                "name": payload.get("name") or payload.get("comment") or "",
            }
            state["vouchers"].append(row)
            return web.json_response({"data": [row]})
        if request.path.endswith("/remove"):
            payload = json.loads(state["requests"][-1][3] or "{}")
            ids = (
                payload.get("ids")
                or payload.get("id")
                or payload.get("vouchers")
                or payload.get("codes")
                or []
            )
            state["vouchers"] = [
                row for row in state["vouchers"] if row["id"] not in ids and row["code"] not in ids
            ]
            return web.Response(status=204)
        return web.Response(status=404)

    app = web.Application()
    app.router.add_post("/api/v2/access/token", token)
    app.router.add_route(
        "*",
        "/api/v2/easypass/{portal}/voucher_plans/{plan}/vouchers",
        vouchers,
    )
    app.router.add_route(
        "*",
        "/api/v2/easypass/{portal}/voucher_plans/{plan}/vouchers/generate",
        vouchers,
    )
    app.router.add_route(
        "*",
        "/api/v2/easypass/{portal}/voucher_plans/{plan}/vouchers/remove",
        vouchers,
    )
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]  # noqa: SLF001
    base = f"http://127.0.0.1:{port}"
    yield state, base
    await runner.cleanup()


def _client(session: aiohttp.ClientSession, base: str) -> CambiumClient:
    return CambiumClient(
        session,
        client_id="cid",
        client_secret="csecret",
        portal_name="GuestPortal",
        voucher_plan="StayPlan",
        token_url=f"{base}/api/v2/access/token",
    )


@pytest.mark.asyncio
async def test_list_create_delete_roundtrip(cloud):
    state, base = cloud
    async with aiohttp.ClientSession() as session:
        client = _client(session, base)
        # Force token + base_url from the fake cloud
        token = await client.async_ensure_token()
        assert token == "bearer-token"
        client._base_url = base  # noqa: SLF001

        listed = await client.async_list_vouchers()
        assert listed == []

        created = await client.async_create_voucher(
            name="Ada 2026-07-10/2026-07-17",
            time_limit_minutes=10080,
            authorized_guest_limit=10,
            rx_rate_limit_kbps=100000,
            tx_rate_limit_kbps=100000,
        )
        assert created.id == "cv-1"
        assert created.code == "XY99ZZ"
        assert "Ada" in created.name

        listed = await client.async_list_vouchers()
        assert [item.code for item in listed] == ["XY99ZZ"]

        await client.async_delete_voucher(created.id)
        listed = await client.async_list_vouchers()
        assert listed == []

    assert any(row[0] == "token" for row in state["requests"])


@pytest.mark.asyncio
async def test_bad_credentials_raise_auth_error(cloud):
    state, base = cloud
    state["token_ok"] = False
    async with aiohttp.ClientSession() as session:
        client = _client(session, base)
        with pytest.raises(CambiumAuthError):
            await client.async_ensure_token()


def test_extract_vouchers_tolerates_shapes():
    rows = extract_vouchers(
        {
            "data": [
                {"id": "1", "code": "AAAA", "name": "one"},
                {"voucher_id": "2", "passcode": "BBBB"},
            ]
        }
    )
    assert [row.code for row in rows] == ["AAAA", "BBBB"]
    assert rows[1].id == "2"

    single = extract_vouchers({"id": "x", "voucherCode": "CCCC", "comment": "stay"})
    assert single[0].code == "CCCC"
    assert single[0].name == "stay"

    assert extract_vouchers(None) == []
    assert extract_vouchers({"oops": True}) == []


def test_create_signature_matches_unifi_protocol():
    """Engine passes UniFi kwargs; Cambium must accept and ignore rate limits."""
    import inspect

    from custom_components.usvegliu.unifi import UnifiClient

    cambium = inspect.signature(CambiumClient.async_create_voucher)
    unifi = inspect.signature(UnifiClient.async_create_voucher)
    assert list(cambium.parameters) == list(unifi.parameters)
