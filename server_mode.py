import socket
import threading
import logging
import time

logger = logging.getLogger("CanServer")


class CanServer:
    def __init__(self, can_interface, port=5555):
        self.can = can_interface
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        self.client_lock = threading.Lock()
        self.forward_thread = None

    def start(self):
        if self.running:
            return
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('', self.port))
        self.server_socket.listen(5)
        self.running = True
        logger.info(f"Serwer CAN nasłuchuje na porcie {self.port}")

        def accept_loop():
            while self.running:
                try:
                    client_sock, addr = self.server_socket.accept()
                    logger.info(f"Nowy klient: {addr}")
                    with self.client_lock:
                        self.clients.append(client_sock)
                except:
                    break

        threading.Thread(target=accept_loop, daemon=True).start()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        with self.client_lock:
            for c in self.clients:
                c.close()
            self.clients.clear()
        logger.info("Serwer CAN zatrzymany")

    def get_client_count(self):
        with self.client_lock:
            return len(self.clients)

    def handle_eval(self, conn, addr, data):
        """Wykonuje kod Pythona (zdalna konsola)."""
        import io, sys, traceback
        code = data.decode("utf-8", errors="ignore")
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = stdout_capture, stderr_capture
        result = ""
        try:
            exec(code, {"can": self.can})
            result = stdout_capture.getvalue()
            if stderr_capture.getvalue():
                result += "\nSTDERR:\n" + stderr_capture.getvalue()
        except Exception:
            result = traceback.format_exc()
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr
        if not result:
            result = "(pusto)"
        try:
            conn.sendall(result.encode("utf-8"))
        except:
            pass
