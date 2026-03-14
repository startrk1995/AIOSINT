"""Tests for osint/core/cdn_filter.py — CDN/VPN IP range filter and popular domain filter."""
import pytest
from osint.core.cdn_filter import is_cdn_ip, is_popular_domain


def test_cloudflare_ipv4_returns_true():
    """104.16.0.1 is in Cloudflare's 104.16.0.0/13 range."""
    assert is_cdn_ip("104.16.0.1") is True


def test_fastly_ipv4_returns_true():
    """151.101.0.1 is in Fastly's 151.101.0.0/16 range."""
    assert is_cdn_ip("151.101.0.1") is True


def test_regular_public_ip_returns_false():
    """8.8.8.8 is Google DNS — not a CDN shared-infrastructure IP."""
    assert is_cdn_ip("8.8.8.8") is False


def test_invalid_string_returns_false():
    """Invalid IP strings must return False, not raise."""
    assert is_cdn_ip("not-an-ip") is False
    assert is_cdn_ip("") is False
    assert is_cdn_ip("999.999.999.999") is False


def test_cloudflare_ipv6_returns_true():
    """2606:4700::1 is in Cloudflare's 2606:4700::/32 range."""
    assert is_cdn_ip("2606:4700::1") is True


def test_private_ip_returns_false():
    """192.168.1.1 is RFC-1918 private — not a CDN range."""
    assert is_cdn_ip("192.168.1.1") is False


def test_cloudflare_network_boundary():
    """Spot-check another Cloudflare range: 173.245.48.0/20."""
    assert is_cdn_ip("173.245.48.1") is True


def test_aws_cloudfront_returns_true():
    """13.32.0.1 is in AWS CloudFront 13.32.0.0/15 range."""
    assert is_cdn_ip("13.32.0.1") is True


def test_akamai_returns_true():
    """23.32.0.1 is in Akamai 23.32.0.0/11 range."""
    assert is_cdn_ip("23.32.0.1") is True


# --- is_popular_domain tests ---

def test_gmail_is_popular():
    assert is_popular_domain("gmail.com") is True


def test_yahoo_variants_are_popular():
    assert is_popular_domain("yahoo.com") is True
    assert is_popular_domain("yahoo.co.uk") is True


def test_outlook_and_hotmail_are_popular():
    assert is_popular_domain("outlook.com") is True
    assert is_popular_domain("hotmail.com") is True


def test_protonmail_is_popular():
    assert is_popular_domain("protonmail.com") is True
    assert is_popular_domain("proton.me") is True


def test_icloud_is_popular():
    assert is_popular_domain("icloud.com") is True


def test_org_domain_is_not_popular():
    """Private/organizational domains should not be filtered."""
    assert is_popular_domain("example.com") is False
    assert is_popular_domain("acme-corp.org") is False


def test_case_insensitive():
    assert is_popular_domain("Gmail.COM") is True
