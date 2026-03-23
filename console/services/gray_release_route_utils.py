def extract_actual_route_name(route):
    original_name = route.get("original_name", "")
    if original_name and "|" in original_name:
        parts = original_name.split("|", 2)
        if len(parts) >= 2 and parts[1]:
            return parts[1]

    route_name = route.get("name", "")
    if route_name and "|" in route_name:
        parts = route_name.split("|", 2)
        if len(parts) >= 2 and parts[1]:
            return parts[1]

    return route_name


def extract_region_app_id(route):
    region_app_id = route.get("region_app_id", "")
    if region_app_id:
        return str(region_app_id)

    original_name = route.get("original_name", "")
    if original_name and "|" in original_name:
        return original_name.split("|", 1)[0]

    route_name = route.get("name", "")
    if route_name and "|" in route_name:
        return route_name.split("|", 1)[0]

    return ""


def route_name_candidates(route):
    candidates = []
    for candidate in [
        route.get("name", ""),
        route.get("original_name", ""),
        extract_actual_route_name(route),
    ]:
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates
