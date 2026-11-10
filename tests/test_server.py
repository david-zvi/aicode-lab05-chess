import http.client
import json
import threading
from collections.abc import Iterator
from typing import Any

import pytest

from server import make_server


@pytest.fixture
def port() -> Iterator[int]:
    server = make_server(port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_port
    server.shutdown()
    server.server_close()


def request(
    port: int,
    method: str,
    path: str,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
) -> tuple[int, str, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request(method, path, body, headers or {})
        response = connection.getresponse()
        return response.status, response.getheader("Content-Type", ""), response.read()
    finally:
        connection.close()


def post_action(port: int, body: bytes) -> tuple[int, Any]:
    code, _, data = request(port, "POST", "/api/action", body)
    return code, json.loads(data)


def test_state_is_the_starting_board(port: int) -> None:
    code, content_type, data = request(port, "GET", "/api/state")
    assert code == 200
    assert content_type == "application/json"
    view = json.loads(data)
    assert view["turn"] == "w"
    assert view["board"]["e2"] == "wP"
    assert view["board"]["e8"] == "bK"
    assert len(view["board"]) == 32


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/", "text/html; charset=utf-8"),
        ("/app.js", "text/javascript; charset=utf-8"),
        ("/style.css", "text/css; charset=utf-8"),
    ],
)
def test_static_files(port: int, path: str, content_type: str) -> None:
    code, served_type, data = request(port, "GET", path)
    assert code == 200
    assert served_type == content_type
    assert data


def test_unknown_get_path_is_404(port: int) -> None:
    code, content_type, data = request(port, "GET", "/missing")
    assert code == 404
    assert content_type == "application/json"
    assert json.loads(data) == {"error": "Not found"}


def test_post_to_other_path_is_404(port: int) -> None:
    code, _, data = request(port, "POST", "/api/state", b"{}")
    assert code == 404
    assert json.loads(data) == {"error": "Not found"}


def test_empty_body_is_rejected(port: int) -> None:
    code, _ = post_action(port, b"")
    assert code == 400


def test_oversize_body_is_rejected_before_reading(port: int) -> None:
    # Only the header claims 1MB+; the server must answer without waiting for it.
    code, _, data = request(
        port, "POST", "/api/action", b"{}", {"Content-Length": "1000001"}
    )
    assert code == 400
    assert "error" in json.loads(data)


def test_invalid_json_is_rejected(port: int) -> None:
    code, _ = post_action(port, b"{not json")
    assert code == 400


def test_non_object_is_rejected(port: int) -> None:
    code, _ = post_action(port, b"[1, 2]")
    assert code == 400


def test_illegal_move_is_rejected(port: int) -> None:
    body = json.dumps({"action": "move", "source": "e2", "target": "e5"}).encode()
    code, data = post_action(port, body)
    assert code == 400
    assert data["error"]


def test_legal_move_updates_the_board(port: int) -> None:
    body = json.dumps({"action": "move", "source": "e2", "target": "e4"}).encode()
    code, view = post_action(port, body)
    assert code == 200
    assert view["board"]["e4"] == "wP"
    assert "e2" not in view["board"]
    assert view["turn"] == "b"
    _, _, state = request(port, "GET", "/api/state")
    assert json.loads(state)["board"]["e4"] == "wP"
