#!/usr/bin/env python3
"""
Lekki klient do zdalnego monitorowania ramek CAN przez WebSocket.
Obsługuje opcjonalny token autoryzacyjny (wysyłany natychmiast po połączeniu).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import json
import time
from collections import deque
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

try:
    import websocket
except ImportError:
    print("Brak biblioteki 'websocket-client'. Zainstaluj: pip install websocket-client")
    exit(1)

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Ostrzeżenie: Brak matplotlib. Wykres nie będzie dostępny.")


class RemoteCanClient:
    def __init__(self, root):
        self.root = root
        self.root.title("CAN Remote Monitor")
        self.root.geometry("900x700")

        self.ws = None
        self.ws_thread = None
        self.connected = False
        self.frames_queue = queue.Queue()
        self.data_series = {}

        self._create_widgets()
        self._process_queue()

    def _create_widgets(self):
        conn_frame = ttk.LabelFrame(self.root, text="Połączenie", padding=5)
        conn_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(conn_frame, text="Adres WebSocket:").grid(row=0, column=0, sticky=tk.W)
        self.url_var = tk.StringVar(value="ws://localhost:8765")
        ttk.Entry(conn_frame, textvariable=self.url_var, width=40).grid(row=0, column=1, padx=5)

        ttk.Label(conn_frame, text="Token (opcjonalny):").grid(row=1, column=0, sticky=tk.W)
        self.token_var = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.token_var, width=30, show="*").grid(row=1, column=1, padx=5)

        self.connect_btn = ttk.Button(conn_frame, text="Połącz", command=self.toggle_connection)
        self.connect_btn.grid(row=2, column=1, pady=5, sticky=tk.W)

        self.status_var = tk.StringVar(value="Rozłączony")
        ttk.Label(conn_frame, textvariable=self.status_var, foreground="red").grid(row=2, column=2, padx=10)

        plot_frame = ttk.LabelFrame(self.root, text="Wykres wartości", padding=5)
        plot_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(plot_frame, text="ID ramki (hex):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.plot_id_var = tk.StringVar(value="7E8")
        ttk.Entry(plot_frame, textvariable=self.plot_id_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(plot_frame, text="Indeks bajtu:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.plot_byte_var = tk.IntVar(value=0)
        ttk.Spinbox(plot_frame, from_=0, to=7, textvariable=self.plot_byte_var, width=3).grid(row=0, column=3, sticky=tk.W, padx=5)

        self.clear_plot_btn = ttk.Button(plot_frame, text="Wyczyść wykres", command=self.clear_plot)
        self.clear_plot_btn.grid(row=0, column=4, padx=10)

        if MATPLOTLIB_AVAILABLE:
            self.fig = Figure(figsize=(8, 3))
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.ax.set_xlabel("Czas (próbki)")
            self.ax.set_ylabel("Wartość bajtu")
            self.ax.grid(True)
        else:
            self.canvas = None

        table_frame = ttk.LabelFrame(self.root, text="Ostatnie ramki", padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("time", "id", "data")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        self.tree.heading("time", text="Czas (lokalny)")
        self.tree.heading("id", text="ID")
        self.tree.heading("data", text="Dane (hex)")
        self.tree.column("time", width=100)
        self.tree.column("id", width=80)
        self.tree.column("data", width=300)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.stats_var = tk.StringVar(value="Odebrano: 0 ramek")
        ttk.Label(self.root, textvariable=self.stats_var).pack(anchor=tk.W, padx=5, pady=2)

    def toggle_connection(self):
        if not self.connected:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Błąd", "Podaj adres WebSocket.")
            return

        self.status_var.set("Łączenie...")
        self.connect_btn.config(state=tk.DISABLED)

        def run_ws():
            token = self.token_var.get().strip()
            # Niestandardowe nagłówki nie zawsze działają, użyjemy wysłania tokena w on_open
            self.ws = websocket.WebSocketApp(
                url,
                on_open=lambda ws: self._on_open(ws, token),
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                subprotocols=None,
                header=None
            )
            # Dla samopodpisanych certyfikatów (tylko do testów!)
            if url.startswith("wss://"):
                import ssl
                self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            self.ws.run_forever()

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    def disconnect(self):
        if self.ws:
            self.ws.close()
        self.connected = False

    def _on_open(self, ws, token):
        logging.info("WebSocket otwarty")
        if token:
            logging.info(f"Wysyłanie tokena: {token[:4]}...")
            ws.send(token)
        self.connected = True
        self.frames_queue.put(("status", "Połączono" + (" (token wysłany)" if token else "")))
        self.frames_queue.put(("set_btn", "Rozłącz"))

    def _on_message(self, ws, message):
        try:
            frame = json.loads(message)
            self.frames_queue.put(("frame", frame))
        except json.JSONDecodeError:
            logging.error(f"Odebrano nie-JSON: {message[:100]}")

    def _on_error(self, ws, error):
        logging.error(f"Błąd WebSocket: {error}")
        self.frames_queue.put(("error", str(error)))

    def _on_close(self, ws, code, msg):
        logging.info(f"WebSocket zamknięty: kod={code}, msg={msg}")
        self.connected = False
        self.frames_queue.put(("status", "Rozłączony"))
        self.frames_queue.put(("set_btn", "Połącz"))

    def _process_queue(self):
        try:
            while True:
                msg = self.frames_queue.get_nowait()
                if msg[0] == "frame":
                    self._add_frame(msg[1])
                elif msg[0] == "status":
                    self.status_var.set(msg[1])
                    if msg[1] == "Rozłączony":
                        self.connect_btn.config(state=tk.NORMAL)
                elif msg[0] == "set_btn":
                    self.connect_btn.config(text=msg[1], state=tk.NORMAL)
                elif msg[0] == "error":
                    messagebox.showerror("Błąd WebSocket", msg[1])
                    self.status_var.set("Błąd")
                    self.connect_btn.config(text="Połącz", state=tk.NORMAL)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._process_queue)

    def _add_frame(self, frame):
        frame_id = frame.get("id", "?")
        data = frame.get("data", [])
        timestamp = frame.get("timestamp", time.time())
        local_time = time.strftime("%H:%M:%S", time.localtime(timestamp))

        hex_data = " ".join(f"{b:02X}" for b in data)
        item = self.tree.insert("", 0, values=(local_time, frame_id, hex_data))
        children = self.tree.get_children()
        if len(children) > 20:
            self.tree.delete(children[-1])

        self.stats_var.set(f"Odebrano: {len(children)} ramek")

        if MATPLOTLIB_AVAILABLE and data:
            try:
                plot_id = self.plot_id_var.get().strip().upper()
                if plot_id.startswith("0X"):
                    plot_id = plot_id[2:]
                if frame_id.upper().lstrip("0X") == plot_id:
                    byte_idx = self.plot_byte_var.get()
                    if byte_idx < len(data):
                        value = data[byte_idx]
                        key = (frame_id, byte_idx)
                        if key not in self.data_series:
                            self.data_series[key] = deque(maxlen=100)
                        self.data_series[key].append(value)
                        self._update_plot(key)
            except:
                pass

    def _update_plot(self, key):
        if not MATPLOTLIB_AVAILABLE:
            return
        series = self.data_series[key]
        if len(series) < 2:
            return
        self.ax.clear()
        self.ax.plot(list(series), 'b-')
        self.ax.set_xlabel("Czas (próbki)")
        self.ax.set_ylabel("Wartość bajtu")
        self.ax.grid(True)
        self.canvas.draw()

    def clear_plot(self):
        plot_id = self.plot_id_var.get().strip()
        byte_idx = self.plot_byte_var.get()
        key = (plot_id, byte_idx)
        if key in self.data_series:
            self.data_series[key].clear()
        if MATPLOTLIB_AVAILABLE:
            self.ax.clear()
            self.ax.grid(True)
            self.canvas.draw()


def main():
    root = tk.Tk()
    app = RemoteCanClient(root)
    root.mainloop()


if __name__ == "__main__":
    main()
