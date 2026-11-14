"""
HTTP management interface for the e-ink calendar display.
Provides endpoints to view the latest render and trigger manual refreshes.
"""

import json
import logging
import os
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

import chore_wheel
import display_config as config

logger = logging.getLogger(__name__)

RENDER_DIR = Path(__file__).parent / "renders"
STATIC_DIR = Path(__file__).parent / "static"


def _find_latest_render(manager=None):
    """Find the most recent calendar render PNG."""
    candidates = []

    if manager and manager.last_render_path:
        latest_render = Path(manager.last_render_path)
        if latest_render.exists():
            candidates.append(latest_render)

    for render_dir in (RENDER_DIR, Path(config.DEBUG_RENDER_PATH)):
        if render_dir.exists():
            candidates.extend(render_dir.glob("calendar_*.png"))

    if not candidates:
        return None

    return max(candidates, key=lambda render: render.stat().st_mtime)


def _render_preview(manager=None):
    """Render a preview PNG, using the manager when available."""
    if manager and hasattr(manager, "render_calendar"):
        png_path = manager.render_calendar()
        if png_path:
            return png_path

    from direct_renderer import render_calendar_direct

    Path(config.DEBUG_RENDER_PATH).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = Path(config.DEBUG_RENDER_PATH) / f"calendar_{timestamp}.png"
    return render_calendar_direct(str(output_path))


class ManagementHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the management interface."""

    manager = None  # set by start_server

    def log_message(self, fmt, *args):
        logger.info(fmt, *args)

    def _request_path(self):
        """Return the request path without any query string."""
        return urlsplit(self.path).path

    # --- routes -------------------------------------------------------

    def do_GET(self):
        path = self._request_path()
        if path == "/":
            self._serve_index()
        elif path == "/render":
            self._serve_latest_render()
        elif path == "/status":
            self._serve_status()
        elif path == "/chore-wheel/status":
            self._json_response(200, {"assignments": chore_wheel.get_assigned_names()})
        else:
            self.send_error(404)

    def do_POST(self):
        path = self._request_path()
        if path == "/refresh":
            self._handle_refresh()
        elif path == "/render-only":
            self._handle_render_only()
        elif path == "/chore-wheel/rotate-back":
            self._handle_chore_rotate_back()
        elif path == "/chore-wheel/rotate-forward":
            self._handle_chore_rotate_forward()
        else:
            self.send_error(404)

    # --- handlers -----------------------------------------------------

    def _serve_latest_render(self):
        render = _find_latest_render(self.manager)
        if render is None:
            self.send_error(404, "No renders available")
            return
        data = render.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.end_headers()
        self.wfile.write(data)

    def _serve_status(self):
        render = _find_latest_render(self.manager)
        status = {
            "last_render": render.name if render else None,
            "last_render_time": datetime.fromtimestamp(render.stat().st_mtime).isoformat() if render else None,
            "display_enabled": config.DISPLAY_ENABLED,
        }
        if self.manager:
            status["last_update_time"] = (
                datetime.fromtimestamp(self.manager.last_update_time).isoformat()
                if self.manager.last_update_time
                else None
            )
        body = json.dumps(status, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_render_only(self):
        logger.info("Manual render-only triggered via web interface")
        try:
            png_path = _render_preview(self.manager)
            if png_path:
                self._json_response(200, {"ok": True, "render_path": png_path})
            else:
                self._json_response(500, {"ok": False, "error": "Render failed"})
        except Exception as e:
            logger.error(f"Manual render-only failed: {e}")
            self._json_response(500, {"error": str(e)})

    def _handle_chore_rotate_back(self):
        logger.info("Chore wheel rotated back via web interface")
        chore_wheel.rotate_back()
        self._json_response(200, {"ok": True, "assignments": chore_wheel.get_assigned_names()})

    def _handle_chore_rotate_forward(self):
        logger.info("Chore wheel rotated forward via web interface")
        chore_wheel.rotate_forward()
        self._json_response(200, {"ok": True, "assignments": chore_wheel.get_assigned_names()})

    def _handle_refresh(self):
        if self.manager is None:
            self._json_response(503, {"error": "No display manager available"})
            return
        logger.info("Manual refresh triggered via web interface")
        try:
            success = self.manager.update_display()
            code = 200 if success else 500
            self._json_response(code, {"ok": success})
        except Exception as e:
            logger.error(f"Manual refresh failed: {e}")
            self._json_response(500, {"error": str(e)})

    def _serve_index(self):
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            self.send_error(500, "index.html not found")
            return
        html = index_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def _json_response(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_server(manager=None, host="0.0.0.0", port=8080):
    """Start the management HTTP server in a daemon thread.

    Args:
        manager: CalendarDisplayManager instance (for refresh support).
        host: Bind address.
        port: Bind port.

    Returns:
        The HTTPServer instance.
    """
    ManagementHandler.manager = manager
    server = HTTPServer((host, port), ManagementHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Management web server listening on http://{host}:{port}")
    return server
