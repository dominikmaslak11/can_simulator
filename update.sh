#!/bin/bash
# =============================================================================
# Ulepszenia Mostka vCAN: automatyczne ponawianie połączenia + filtrowanie ID
# =============================================================================

set -e

BASE_DIR="$(pwd)"
BRIDGE_FILE="${BASE_DIR}/bridge_client.py"
BRIDGE_TAB_FILE="${BASE_DIR}/gui/tabs/bridge_tab.py"
BACKUP_DIR="${BASE_DIR}/backup_bridge_enh_$(date +%Y%m%d_%H%M%S)"

echo "=== Ulepszanie Mostka vCAN: auto-reconnect + filtrowanie ID ==="

mkdir -p "$BACKUP_DIR"
cp "$BRIDGE_FILE" "$BRIDGE_TAB_FILE" "$BACKUP_DIR/" 2>/dev/null || true
echo "Kopie zapasowe w: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 1. Aktualizacja bridge_client.py – dodanie auto-reconnect i filtrowania
# -----------------------------------------------------------------------------
cat > "$BRIDGE_FILE" << 'EOF'
#!/usr/bin/env python3
"""
Mostek WebSocket -> wirtualny CAN (vcan0) z auto-reconnect i filtrowaniem ID.
"""

import json
import logging
import threading
import time
import subprocess
import sys
import argparse
from typing import List, Optional, Set

import websocket
import can

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("CAN-Bridge")


class VCanBridge:
    def __init__(self, url: str, token: Optional[str] = None,
                 filter_ids: Optional[List[int]] = None,
                 auto_reconnect: bool = True,
                 reconnect_delay: int = 5,
                 status_callback=None):
        self.url = url
        self.token = token
        self.filter_ids = set(filter_ids) if filter_ids else None
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        self.status_callback = status_callback

        self.ws = None
        self.bus = None
        self.running = False
        self.reconnect_thread = None
        self._setup_vcan()

    def _setup_vcan(self):
        """Tworzy wirtualny interfejs vcan0, jeśli nie istnieje."""
        try:
            subprocess.run(['ip', 'link', 'show', 'vcan0'], check=True, capture_output=True)
            logger.info("vcan0 już istnieje.")
        except subprocess.CalledProcessError:
            logger.info("Tworzenie vcan0...")
            subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', 'vcan0', 'type', 'vcan'], check=True)
            subprocess.run(['sudo', 'ip', 'link', 'set', 'vcan0', 'up'], check=True)
            logger.info("vcan0 utworzony i włączony.")
        self.bus = can.interface.Bus(channel='vcan0', interface='socketcan')

    def _should_forward(self, can_id: int) -> bool:
        """Sprawdza, czy ramka o danym ID powinna być przekazana."""
        if self.filter_ids is None:
            return True
        return can_id in self.filter_ids

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            can_id = int(data['id'], 16) if isinstance(data['id'], str) else data['id']

            if not self._should_forward(can_id):
                logger.debug(f"Pominięto ID 0x{can_id:X} (filtrowanie)")
                return

            payload = bytes(data['data'])
            is_extended = data.get('is_extended', False)
            msg = can.Message(arbitration_id=can_id, data=payload, is_extended_id=is_extended)
            self.bus.send(msg)
            if self.status_callback:
                self.status_callback(f"Wysłano: {msg}")
        except Exception as e:
            logger.error(f"Błąd ramki: {e}")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        if self.status_callback:
            self.status_callback(f"Błąd: {error}")

    def _on_close(self, ws, code, msg):
        logger.info("WebSocket zamknięty.")
        if self.status_callback:
            self.status_callback("Rozłączono")
        if self.auto_reconnect and self.running:
            self._start_reconnect()

    def _on_open(self, ws):
        logger.info("Połączono z serwerem.")
        if self.token:
            ws.send(self.token)
        if self.status_callback:
            self.status_callback("Połączono")

    def _start_reconnect(self):
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()

    def _reconnect_loop(self):
        while self.running:
            logger.info(f"Próba ponownego połączenia za {self.reconnect_delay} s...")
            time.sleep(self.reconnect_delay)
            if not self.running:
                break
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                wst = threading.Thread(target=self.ws.run_forever, daemon=True)
                wst.start()
                break  # po udanym połączeniu wychodzimy z pętli
            except Exception as e:
                logger.error(f"Błąd reconnect: {e}")

    def start(self):
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        wst = threading.Thread(target=self.ws.run_forever, daemon=True)
        wst.start()

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        if self.bus:
            self.bus.shutdown()
        if self.status_callback:
            self.status_callback("Zatrzymano")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='ws://localhost:8765')
    parser.add_argument('--token')
    parser.add_argument('--filter-ids', help='Lista ID CAN oddzielonych przecinkami, np. 0x123,0x456')
    parser.add_argument('--no-auto-reconnect', action='store_true', help='Wyłącz automatyczne ponawianie')
    args = parser.parse_args()

    filter_ids = None
    if args.filter_ids:
        try:
            filter_ids = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip()) for x in args.filter_ids.split(',')]
        except ValueError:
            logger.error("Nieprawidłowy format listy ID. Użyj liczb dziesiętnych lub szesnastkowych z 0x.")
            sys.exit(1)

    bridge = VCanBridge(
        url=args.url,
        token=args.token,
        filter_ids=filter_ids,
        auto_reconnect=not args.no_auto_reconnect,
        status_callback=print
    )
    bridge.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == "__main__":
    main()
EOF

chmod +x "$BRIDGE_FILE"
echo "bridge_client.py zaktualizowany."

# -----------------------------------------------------------------------------
# 2. Aktualizacja bridge_tab.py – dodanie pól w GUI
# -----------------------------------------------------------------------------
cat > "$BRIDGE_TAB_FILE" << 'EOF'
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from bridge_client import VCanBridge

logger = logging.getLogger(__name__)


class BridgeTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.bridge = None
        self.bridge_thread = None
        self.status_queue = queue.Queue()
        self.running = False

        self._create_widgets()
        self._process_queue()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="Mostek WebSocket → vcan0", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Adres WebSocket:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.url_var = tk.StringVar(value="ws://localhost:8765")
        ttk.Entry(frame, textvariable=self.url_var, width=40).grid(row=0, column=1, padx=5)

        ttk.Label(frame, text="Token (opcjonalny):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.token_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.token_var, width=30, show="*").grid(row=1, column=1, padx=5)

        ttk.Label(frame, text="Filtruj ID (opcjonalnie):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.filter_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.filter_var, width=40).grid(row=2, column=1, padx=5)
        ttk.Label(frame, text="(lista oddzielona przecinkami, np. 0x123,0x456)").grid(row=3, column=1, sticky=tk.W, padx=5)

        self.auto_reconnect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Automatycznie ponawiaj połączenie", variable=self.auto_reconnect_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="Start mostka", command=self.start_bridge)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop mostka", command=self.stop_bridge, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        status_frame = ttk.LabelFrame(self.parent, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        self.status_var = tk.StringVar(value="Zatrzymany")
        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W)

        log_frame = ttk.LabelFrame(self.parent, text="Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _process_queue(self):
        try:
            while True:
                msg = self.status_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass
        finally:
            self.parent.after(100, self._process_queue)

    def _append_log(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _status_callback(self, msg):
        self.status_queue.put(msg)

    def start_bridge(self):
        url = self.url_var.get().strip()
        token = self.token_var.get().strip() or None

        # Parsowanie filtrów ID
        filter_str = self.filter_var.get().strip()
        filter_ids = None
        if filter_str:
            try:
                filter_ids = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip())
                              for x in filter_str.split(',')]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format listy ID. Użyj liczb dziesiętnych lub szesnastkowych z 0x.")
                return

        self.bridge = VCanBridge(
            url=url,
            token=token,
            filter_ids=filter_ids,
            auto_reconnect=self.auto_reconnect_var.get(),
            status_callback=self._status_callback
        )
        self.bridge_thread = threading.Thread(target=self._run_bridge, daemon=True)
        self.bridge_thread.start()

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Uruchomiony")
        self._append_log("Mostek uruchomiony.")

    def _run_bridge(self):
        self.bridge.start()
        self.parent.after(0, self._bridge_stopped)

    def stop_bridge(self):
        if self.bridge:
            self.bridge.stop()
        self._bridge_stopped()

    def _bridge_stopped(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Zatrzymany")
        self._append_log("Mostek zatrzymany.")


def setup_bridge_tab(app, parent):
    BridgeTab(parent, app)
EOF

echo "bridge_tab.py zaktualizowany."

echo ""
echo "=== Ulepszenia Mostka vCAN zostały wprowadzone ==="
echo "Uruchom aplikację: sudo ./run.sh"
echo "Nowe funkcje w zakładce 'Mostek vCAN':"
echo "  - Automatyczne ponawianie połączenia (checkbox)"
echo "  - Filtrowanie ramek po ID (pole tekstowe)"
