"""CDN/VPN IP range filter — excludes shared-infrastructure IPs from OSINT pivots."""
import ipaddress
from functools import lru_cache

# Known CDN/shared-infrastructure CIDR ranges to exclude from IP pivots.
# Sources: Cloudflare published ranges, Fastly, Akamai, AWS CloudFront.
_CDN_NETWORKS = [
    # Cloudflare
    "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "104.16.0.0/13", "104.24.0.0/14",
    "108.162.192.0/18", "131.0.72.0/22", "141.101.64.0/18",
    "162.158.0.0/15", "172.64.0.0/13", "173.245.48.0/20",
    "188.114.96.0/20", "190.93.240.0/20", "197.234.240.0/22",
    "198.41.128.0/17",
    # Cloudflare IPv6
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32",
    "2405:b500::/32", "2405:8100::/32", "2a06:98c0::/29",
    "2c0f:f248::/32",
    # Fastly
    "23.235.32.0/20", "43.249.72.0/22", "103.244.50.0/24",
    "103.245.222.0/23", "103.245.224.0/24", "104.156.80.0/20",
    "151.101.0.0/16", "157.52.64.0/18", "167.82.0.0/17",
    "167.82.128.0/20", "167.82.160.0/20", "167.82.224.0/20",
    "172.111.64.0/18", "185.31.16.0/22", "199.27.72.0/21",
    "199.232.0.0/16",
    # Akamai (representative ranges)
    "23.32.0.0/11", "23.64.0.0/14", "23.192.0.0/11",
    "96.16.0.0/15", "96.6.0.0/15",
    # AWS CloudFront (representative ranges)
    "13.32.0.0/15", "13.35.0.0/16", "52.84.0.0/15",
    "54.182.0.0/16", "54.192.0.0/16", "54.230.0.0/16",
    "64.252.64.0/18", "70.132.0.0/18", "204.246.164.0/22",
    "204.246.168.0/22", "205.251.192.0/19", "216.137.32.0/19",
]


@lru_cache(maxsize=1)
def _get_networks() -> tuple:
    return tuple(ipaddress.ip_network(cidr, strict=False) for cidr in _CDN_NETWORKS)


def is_cdn_ip(ip: str) -> bool:
    """Return True if ip falls within a known CDN/shared-infrastructure range.

    Args:
        ip: IPv4 or IPv6 address string.

    Returns:
        True if the IP belongs to a known CDN/VPN/shared-infra range, False otherwise.
        Returns False for invalid IP strings (caller's responsibility to validate).
    """
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in _get_networks())
