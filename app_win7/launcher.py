from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from inference import YOLO11Seg


APP_NAME = "现代零售终端智慧运营平台"
MAX_UPLOAD_BYTES = 35 * 1024 * 1024


def bundled_root():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def default_web_root():
    root = bundled_root()
    packaged = root / "web_win7"
    return packaged if packaged.is_dir() else root / "app_win7" / "web"


def default_model_path():
    root = bundled_root()
    packaged = root / "runtime" / "best.onnx"
    if packaged.is_file():
        return packaged
    return root / "backend_original" / "text" / "best.onnx"


def log_path():
    local_app_data = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    directory = local_app_data / "ModernRetailTerminal" / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "application-win7.log"


def configure_logging():
    logging.basicConfig(
        filename=str(log_path()),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def json_bytes(payload):
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def threshold(query, name, default):
    try:
        value = float(query.get(name, [str(default)])[0])
    except (TypeError, ValueError):
        value = default
    return min(1.0, max(0.0, value))


def parse_image_part(content_type, body):
    envelope = (
        "Content-Type: {}\r\nMIME-Version: 1.0\r\n\r\n".format(content_type)
    ).encode("ascii") + body
    message = BytesParser(policy=policy.default).parsebytes(envelope)
    if not message.is_multipart():
        raise ValueError("上传内容不是有效的 multipart/form-data")
    for part in message.iter_parts():
        if part.get_content_disposition() != "form-data":
            continue
        if part.get_param("name", header="content-disposition") != "file":
            continue
        filename = part.get_filename() or "image.jpg"
        image_bytes = part.get_payload(decode=True)
        if not image_bytes:
            raise ValueError("图片文件内容为空")
        return filename, image_bytes
    raise ValueError("没有收到名称为 file 的图片文件")


class ApplicationState:
    def __init__(self, model_path):
        self.model_path = model_path
        self.model = None
        self.model_ready = False
        self.model_error = ""
        self.inference_lock = threading.Lock()
        self.shutdown_requested = threading.Event()
        self.server = None

    def load_model(self):
        if not self.model_path.is_file():
            self.model_error = "模型文件不存在：{}".format(self.model_path)
            logging.error(self.model_error)
            return
        try:
            started_at = time.time()
            self.model = YOLO11Seg(str(self.model_path))
            self.model_ready = True
            self.model_error = ""
            logging.info("Model loaded in %.3f seconds", time.time() - started_at)
        except Exception as exc:
            self.model_error = "模型加载失败：{}".format(exc)
            logging.exception("Model loading failed")

    def status_payload(self):
        if self.model_ready and self.model is not None:
            return {
                "status": "ready",
                "backend_ready": True,
                "message": "模型已就绪",
            }
        return {
            "status": "error" if self.model_error else "loading",
            "backend_ready": False,
            "message": self.model_error or "模型加载中",
        }

    def request_shutdown(self):
        if self.shutdown_requested.is_set():
            return
        self.shutdown_requested.set()
        logging.info("Application shutdown requested")
        if self.server is not None:
            self.server.shutdown()


class ApplicationServer(ThreadingHTTPServer):
    daemon_threads = True


class AppRequestHandler(BaseHTTPRequestHandler):
    app_state = None
    web_root = None
    server_version = "ModernRetailTerminalWin7/1.0"

    def log_message(self, format_string, *args):
        logging.info("HTTP %s - %s", self.address_string(), format_string % args)

    def send_json(self, status, payload):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(200, self.app_state.status_payload())
            return
        if parsed.path == "/api/ping":
            self.send_json(200, {"status": "ok"})
            return
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            return
        self.serve_static_file(parsed.path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/infer":
            self.run_inference(parsed.query)
            return
        if parsed.path == "/api/shutdown":
            self.send_json(200, {"status": "stopping", "message": "程序正在安全退出"})
            threading.Thread(target=self.app_state.request_shutdown).start()
            return
        self.send_json(404, {"status": "error", "message": "请求地址不存在"})

    def serve_static_file(self, url_path):
        relative = "index.html" if url_path in ("", "/") else urllib.parse.unquote(url_path.lstrip("/"))
        relative_path = Path(relative.replace("/", os.sep))
        if relative_path.is_absolute() or ".." in relative_path.parts:
            self.send_json(403, {"status": "error", "message": "无效文件路径"})
            return
        candidate = (self.web_root / relative_path).resolve()
        try:
            candidate.relative_to(self.web_root.resolve())
        except ValueError:
            self.send_json(403, {"status": "error", "message": "无效文件路径"})
            return
        if not candidate.is_file():
            self.send_json(404, {"status": "error", "message": "页面资源不存在"})
            return
        content = candidate.read_bytes()
        mime_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header(
            "Content-Type",
            "{}; charset=utf-8".format(mime_type)
            if mime_type.startswith("text/") or mime_type == "application/javascript"
            else mime_type,
        )
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(content)

    def run_inference(self, raw_query):
        status = self.app_state.status_payload()
        if not status["backend_ready"]:
            self.send_json(503, {"status": "error", "message": status["message"]})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0
        if content_length <= 0:
            self.send_json(400, {"status": "error", "message": "没有收到图片文件"})
            return
        if content_length > MAX_UPLOAD_BYTES:
            self.send_json(413, {"status": "error", "message": "单张图片不能超过 35 MB"})
            return
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("multipart/form-data"):
            self.send_json(415, {"status": "error", "message": "上传格式必须为 multipart/form-data"})
            return
        body = self.rfile.read(content_length)
        query = urllib.parse.parse_qs(raw_query)
        confidence = threshold(query, "conf_threshold", 0.25)
        iou = threshold(query, "iou_threshold", 0.45)
        try:
            filename, image_bytes = parse_image_part(content_type, body)
            with self.app_state.inference_lock:
                result_image, detections, total_score, score_details = (
                    self.app_state.model.infer_image_bytes(
                        image_bytes,
                        confidence,
                        iou,
                    )
                )
            result = {
                "detections": detections,
                "total_score": total_score,
                "score_details": score_details,
            }
            metadata = json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
            )
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(result_image)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Detection-Results", metadata)
            self.send_header(
                "X-Original-Filename",
                urllib.parse.quote(filename, safe=""),
            )
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(result_image)
        except ValueError as exc:
            self.send_json(400, {"status": "error", "message": str(exc)})
        except Exception as exc:
            logging.exception("Inference request failed")
            self.send_json(500, {"status": "error", "message": "推理请求失败：{}".format(exc)})


def parse_args():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--model", type=Path, default=None)
    return parser.parse_args()


def main():
    configure_logging()
    args = parse_args()
    web_root = default_web_root()
    model_path = args.model.resolve() if args.model else default_model_path()
    port = args.port or find_free_port()

    state = ApplicationState(model_path)
    AppRequestHandler.app_state = state
    AppRequestHandler.web_root = web_root
    try:
        server = ApplicationServer(("127.0.0.1", port), AppRequestHandler)
    except OSError:
        logging.exception("Frontend server could not start")
        return 2
    state.server = server
    threading.Thread(target=state.load_model, name="model-loader", daemon=True).start()

    page_url = "http://127.0.0.1:{}/".format(port)
    logging.info("Application page available at %s", page_url)
    if not args.no_browser:
        timer = threading.Timer(0.8, lambda: webbrowser.open(page_url, new=1))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        logging.info("Application stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
