"""Async client for the Services Manager REST API."""

from urllib.parse import quote

import httpx

from config import TOKEN_SERVICE_MANAGER, URL_API_SERVICE_MANAGER


class ServiceManagerAPIError(RuntimeError):
    """An HTTP or configuration error returned while calling the API."""


def _url(path: str) -> str:
    if not URL_API_SERVICE_MANAGER:
        raise ServiceManagerAPIError("Falta configurar url_api_service_manager en .env.")
    if not TOKEN_SERVICE_MANAGER:
        raise ServiceManagerAPIError("Falta configurar token_service_manager en .env.")
    return f"{URL_API_SERVICE_MANAGER}/api/v1{path}"


async def request(method: str, path: str, *, params=None, payload=None):
    headers = {"Authorization": f"Bearer {TOKEN_SERVICE_MANAGER}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(
                method,
                _url(path),
                params=params,
                json=payload,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise ServiceManagerAPIError(f"No se pudo conectar con Services Manager: {exc}") from exc

    if not response.is_success:
        try:
            body = response.json()
            detail = body.get("error", body.get("message", str(body))) if isinstance(body, dict) else str(body)
        except ValueError:
            detail = response.text or response.reason_phrase
        raise ServiceManagerAPIError(f"API respondió {response.status_code}: {detail}")

    if response.status_code == 204 or not response.content:
        return None
    return response.json()


async def list_services(*, search=None, tag_id=None, visible=None, system_service=None, page=1, per_page=10):
    params = {"page": page, "per_page": per_page}
    if search is not None:
        params["search"] = search
    if tag_id is not None:
        params["tag_id"] = tag_id
    if visible is not None:
        params["visible"] = visible
    if system_service is not None:
        params["system_service"] = system_service
    return await request("GET", "/services", params=params)


async def create_service(name: str, description: str):
    return await request(
        "POST", "/services", payload={"name": name, "description": description}
    )


async def get_service(unit_name: str, *, visible=None, system_service=None):
    """Load one service, including the live active state, from its detail route."""
    service = await request("GET", f"/services/{quote(unit_name, safe='')}")
    if visible is not None and service.get("visible") is not visible:
        return None
    if system_service is not None and service.get("system_service") is not system_service:
        return None
    return service


async def get_service_tags(unit_name: str):
    return await request("GET", f"/services/{quote(unit_name, safe='')}/tags")


async def get_tags():
    return await request("GET", "/tags")


async def discover(batch_size=100):
    return await request("POST", "/discovery", payload={"batch_size": batch_size})


async def set_visibility(unit_name: str, visible: bool):
    return await request(
        "PUT", f"/services/{quote(unit_name, safe='')}/visibility", payload={"visible": visible}
    )


async def set_alias(unit_name: str, alias: str):
    return await request(
        "PUT", f"/services/{quote(unit_name, safe='')}/alias", payload={"alias": alias}
    )


async def set_description(unit_name: str, description: str):
    """Call the description endpoint planned for Services Manager."""
    return await request(
        "PUT", f"/services/{quote(unit_name, safe='')}/description",
        payload={"description": description},
    )


async def control_service(unit_name: str, action: str):
    return await request("POST", f"/services/{quote(unit_name, safe='')}/{action}")


async def set_startup_mode(unit_name: str, mode: str):
    return await request(
        "PUT", f"/services/{quote(unit_name, safe='')}/startup-mode", payload={"mode": mode}
    )


async def get_service_directory():
    return await request("GET", "/settings/service-directory")


async def set_service_directory(path: str):
    return await request("PUT", "/settings/service-directory", payload={"path": path})


async def create_tag(name: str):
    return await request("POST", "/tags", payload={"name": name})


async def delete_tag(name: str):
    return await request("DELETE", f"/tags/{quote(name, safe='')}")


async def add_service_tag(unit_name: str, tag_name: str):
    return await request(
        "PUT", f"/services/{quote(unit_name, safe='')}/tags/{quote(tag_name, safe='')}"
    )


async def remove_service_tag(unit_name: str, tag_name: str):
    return await request(
        "DELETE", f"/services/{quote(unit_name, safe='')}/tags/{quote(tag_name, safe='')}"
    )
