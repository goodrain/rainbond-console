import ipaddress


def validate_endpoint_address(address):
    def parse_ip():
        try:
            for item in address:
                if item == ".":
                    return ipaddress.IPv4Address(address)
                elif item == ":":
                    return ipaddress.IPv6Address(address)
        except ipaddress.AddressValueError:
            return None
        return None

    errs = []
    ip = parse_ip()
    if ip is None:
        errs.append("{} must be a valid IP address".format(address))
        return errs
    if ip.is_unspecified:
        errs.append("{} may not be unspecified (0.0.0.0)".format(address))
    if ip.is_loopback:
        errs.append("{} may not be in the loopback range (127.0.0.0/8)".format(address))
    if ip.is_link_local:
        errs.append("{} may not be in the link-local range (169.254.0.0/16)".format(address))
    if ip.is_link_local:
        errs.append("{} may not be in the link-local multicast range (224.0.0.0/24)".format(address))
    return errs
