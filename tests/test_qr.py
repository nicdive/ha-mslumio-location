"""Guest web-app share URL and QR encoding."""

from custom_components.usvegliu.qr import guest_share_url, make_share_qr_svg


def test_guest_share_url_uses_request_host():
    assert guest_share_url("") == ""
    assert guest_share_url("TOKEN") == "/usvegliu/s/TOKEN"
    assert (
        guest_share_url("TOKEN", "https", "ha.lan:8123")
        == "https://ha.lan:8123/usvegliu/s/TOKEN"
    )
    assert (
        guest_share_url("TOKEN", "https, http", "ha.lan, other")
        == "https://ha.lan/usvegliu/s/TOKEN"
    )


def test_qr_svg_encodes_the_maison_url():
    url = "http://192.168.23.115:8123/usvegliu/s/stay-token"
    svg = make_share_qr_svg(url)
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "<script" not in svg.lower()
    assert make_share_qr_svg("") == ""
    assert make_share_qr_svg("   ") == ""
