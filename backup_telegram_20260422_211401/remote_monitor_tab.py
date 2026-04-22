import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import queue
import logging
import time
import ssl

from broadcaster import CANWebSocketServer

logger = logging.getLogger(__name__)


class RemoteMonitorTab:
    """Zakładka do zarządzania zdalnym monitoringiem CAN przez WebSocket."""

    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.server = None
        self.server_thread = None
        self.loop = None
        self.status_var = tk.StringVar(value="Serwer zatrzymany")
        self.port_var = tk.IntVar(value=8765)
        self.token_var = tk.StringVar()
        self.clients_var = tk.StringVar(value="0")

        self.use_ssl = tk.BooleanVar(value=False)
        self.cert_file = tk.StringVar()
        self.key_file = tk.StringVar()

        
        self.incoming_filter_var = tk.StringVar()

        
        self.allowed_ids_var = tk.StringVar()
        self.log_to_file_var = tk.BooleanVar(value=False)

        self._create_widgets()
        self._setup_queue()
        self._setup_logging()

    def _create_widgets(self):
        frame = ttk.LabelFrame(self.parent, text="Ustawienia serwera WebSocket", padding=10)
        frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.port_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(frame, text="Token (opcjonalny):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(frame, textvariable=self.token_var, width=30, show="*").grid(row=1, column=1, sticky=tk.W, padx=5)

        self.ssl_check = ttk.Checkbutton(frame, text="Użyj WSS (bezpieczne połączenie)", variable=self.use_ssl, command=self._toggle_ssl)
        self.ssl_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=2)

        ttk.Label(frame, text="Certyfikat (cert.pem):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.cert_entry = ttk.Entry(frame, textvariable=self.cert_file, width=40)
        self.cert_entry.grid(row=3, column=1, sticky=tk.W, padx=5)
        ttk.Button(frame, text="Przeglądaj", command=lambda: self._browse_file(self.cert_file, "PEM files", "*.pem")).grid(row=3, column=2, padx=5)

        ttk.Label(frame, text="Klucz prywatny (key.pem):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.key_entry = ttk.Entry(frame, textvariable=self.key_file, width=40)
        self.key_entry.grid(row=4, column=1, sticky=tk.W, padx=5)
        ttk.Button(frame, text="Przeglądaj", command=lambda: self._browse_file(self.key_file, "PEM files", "*.pem")).grid(row=4, column=2, padx=5)

        self.gen_btn = ttk.Button(frame, text="Generuj certyfikat testowy", command=self._generate_self_signed_cert)
        self.gen_btn.grid(row=5, column=1, pady=5)

        # Ukryj początkowo pola certyfikatów
        self.cert_entry.grid_remove()
        self.key_entry.grid_remove()
        self.gen_btn.grid_remove()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=10)

        self.start_btn = ttk.Button(btn_frame, text="Start serwera", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = ttk.Button(btn_frame, text="Stop serwera", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        status_frame = ttk.LabelFrame(self.parent, text="Status", padding=10)
        status_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(status_frame, textvariable=self.status_var).pack(anchor=tk.W)
        ttk.Label(status_frame, text="Aktywni klienci:").pack(anchor=tk.W)
        ttk.Label(status_frame, textvariable=self.clients_var).pack(anchor=tk.W)

        log_frame = ttk.LabelFrame(self.parent, text="Log serwera", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.simulate_btn = None

    def _toggle_ssl(self):
        if self.use_ssl.get():
            self.cert_entry.grid()
            self.key_entry.grid()
            self.gen_btn.grid()
        else:
            self.cert_entry.grid_remove()
            self.key_entry.grid_remove()
            self.gen_btn.grid_remove()

    def _browse_file(self, var, filetypes_desc, pattern):
        path = filedialog.askopenfilename(filetypes=[(filetypes_desc, pattern), ("All files", "*.*")])
        if path:
            var.set(path)

    def _generate_self_signed_cert(self):
        from tkinter import simpledialog
        days = simpledialog.askinteger("Certyfikat", "Ważność certyfikatu (dni):", initialvalue=365)
        if not days:
            return
        import subprocess, os
        cert_path = os.path.join(os.getcwd(), "cert.pem")
        key_path = os.path.join(os.getcwd(), "key.pem")
        cmd = f'openssl req -x509 -newkey rsa:4096 -keyout {key_path} -out {cert_path} -days {days} -nodes -subj "/CN=localhost"'
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            self.cert_file.set(cert_path)
            self.key_file.set(key_path)
            messagebox.showinfo("Sukces", f"Certyfikat wygenerowany:\n{cert_path}\n{key_path}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wygenerować certyfikatu:\n{e}")

    def _setup_queue(self):
        self.queue = queue.Queue()
        self.parent.after(100, self._process_queue)

    def _process_queue(self):
        try:
            while True:
                func, args = self.queue.get_nowait()
                func(*args)
        except queue.Empty:
            pass
        finally:
            self.parent.after(100, self._process_queue)

    def _setup_logging(self):
        class TextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                def append():
                    self.text_widget.configure(state=tk.NORMAL)
                    self.text_widget.insert(tk.END, msg + '\n')
                    self.text_widget.see(tk.END)
                    self.text_widget.configure(state=tk.DISABLED)
                self.text_widget.after(0, append)

        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logging.getLogger('broadcaster').addHandler(handler)
        logging.getLogger('broadcaster').setLevel(logging.INFO)

    def log(self, message):
        self.queue.put((self._append_log, [message]))

    def _append_log(self, message):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def start_server(self):
        port = self.port_var.get()
        token = self.token_var.get() or None

        ssl_ctx = None
        if self.use_ssl.get():
            cert = self.cert_file.get()
            key = self.key_file.get()
            if not cert or not key:
                messagebox.showerror("Błąd", "Wybierz pliki certyfikatu i klucza.")
                return
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_ctx.load_cert_chain(cert, key)

                # Parsuj filtr ID przychodzących
        filter_str = self.incoming_filter_var.get().strip()
        incoming_filter = None
        if filter_str:
            try:
                incoming_filter = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip())
                                   for x in filter_str.split(',') if x.strip()]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format filtru ID.")
                return
                # Parsuj dozwolone ID
        allowed_str = self.allowed_ids_var.get().strip()
        allowed_ids = None
        if allowed_str:
            try:
                allowed_ids = [int(x.strip(), 16) if x.strip().startswith('0x') else int(x.strip())
                               for x in allowed_str.split(',') if x.strip()]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowy format listy dozwolonych ID.")
                return
        self.server = CANWebSocketServer(port=port, token=token, ssl_context=ssl_ctx)
        self.server.allowed_client_ids = allowed_ids
        self.server.log_to_file = self.log_to_file_var.get()
        self.server.can_interface = self.app.can
        self.server.incoming_filter_ids = incoming_filter
        # Przekaż referencję do interfejsu CAN
        self.server.can_interface = self.app.can

        def run_asyncio():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.loop = loop
            try:
                loop.run_until_complete(self.server.start())
                self.queue.put((self.status_var.set, ["Serwer działa"]))
                self.queue.put((self._set_buttons_state, [tk.DISABLED, tk.NORMAL]))
                self.queue.put((self.log, ["Serwer uruchomiony"]))
                asyncio.ensure_future(self._update_client_count())
                loop.run_forever()
            except Exception as e:
                self.queue.put((self._show_error, [f"Błąd serwera: {e}"]))
            finally:
                self.queue.put((self.status_var.set, ["Serwer zatrzymany"]))
                self.queue.put((self._set_buttons_state, [tk.NORMAL, tk.DISABLED]))
                self.queue.put((self.log, ["Serwer zatrzymany"]))
                self.loop = None

        self.server_thread = threading.Thread(target=run_asyncio, daemon=True)
        self.server_thread.start()
        self._hook_can_source()

    async def _update_client_count(self):
        while self.server and self.server.is_running:
            count = self.server.client_count
            self.queue.put((self.clients_var.set, [str(count)]))
            await asyncio.sleep(1.0)

    def _hook_can_source(self):
        possible_managers = ['can_manager', 'can_reader', 'can_sniffer', 'player']
        hooked = False
        for attr in possible_managers:
            if hasattr(self.app, attr):
                manager = getattr(self.app, attr)
                if hasattr(manager, 'add_frame_callback'):
                    manager.add_frame_callback(self._on_can_frame)
                    self.log(f"Podpięto do {attr}.add_frame_callback")
                    hooked = True
                    break
                elif hasattr(manager, 'register_callback'):
                    manager.register_callback(self._on_can_frame)
                    self.log(f"Podpięto do {attr}.register_callback")
                    hooked = True
                    break
        if not hooked:
            self.log("Nie znaleziono menedżera CAN – użyj przycisku 'Symuluj ramkę' do testów")
            self.queue.put((self._add_simulate_button, []))

    def _add_simulate_button(self):
        if self.simulate_btn:
            return
        sim_frame = ttk.Frame(self.parent)
        sim_frame.pack(fill=tk.X, padx=10, pady=5)
        self.simulate_btn = ttk.Button(sim_frame, text="Symuluj ramkę testową",
                                       command=self._simulate_can_frame)
        self.simulate_btn.pack()

    def _simulate_can_frame(self):
        frame = {
            "id": "0x7E8",
            "data": [0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88],
            "timestamp": time.time()
        }
        self._on_can_frame(frame)
        self.log("Wysłano symulowaną ramkę")

    def _on_can_frame(self, frame_dict):
        if self.server and self.server.is_running and self.loop:
            asyncio.run_coroutine_threadsafe(
                self.server.broadcast_frame_async(frame_dict),
                self.loop
            )

    def stop_server(self):
        if self.server and self.loop:
            async def shutdown():
                await self.server.stop()
                self.loop.stop()

            asyncio.run_coroutine_threadsafe(shutdown(), self.loop)
            self.server_thread.join(timeout=2.0)
            self.server = None

    def _set_buttons_state(self, start_state, stop_state):
        self.start_btn.config(state=start_state)
        self.stop_btn.config(state=stop_state)

    def _show_error(self, msg):
        messagebox.showerror("Błąd", msg)


def setup_remote_monitor_tab(app, parent_frame):
    """
    Konfiguruje zawartość zakładki zdalnego monitoringu.
    Wywoływana z app.py z już utworzoną ramką.
    """
    RemoteMonitorTab(parent_frame, app)
