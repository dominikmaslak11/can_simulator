from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk

try:
    import cantools
    CANTTOOLS_AVAILABLE = True
except ImportError:
    CANTTOOLS_AVAILABLE = False


class DbcHandler:
    def load_dbc_file(self):
        if not CANTTOOLS_AVAILABLE:
            messagebox.showerror("Błąd", "Biblioteka 'cantools' nie jest zainstalowana.")
            return
        filepath = filedialog.askopenfilename(
            title="Wybierz plik DBC",
            filetypes=[("Pliki DBC", "*.dbc"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return
        try:
            self.dbc_db = cantools.database.load_file(filepath)
            self.dbc_decoding_active = True
            self.app.sniffer_dbc_status.config(text=f"DBC: {filepath.split('/')[-1]}")
            self.log(f"[Sniffer] Wczytano plik DBC: {filepath}")
            self._configure_columns()
            self._refresh_decoded_column()
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać pliku DBC:\n{e}")

    def unload_dbc(self):
        self.dbc_db = None
        self.dbc_decoding_active = False
        self.app.sniffer_dbc_status.config(text="Brak DBC")
        self._configure_columns()
        self.log("[Sniffer] Wyłączono dekodowanie DBC")

    def _configure_columns(self):
        tree = self.app.sniffer_tree
        base = self.columns_bit_base if self.bit_view_active else self.columns_normal_base
        if self.dbc_decoding_active:
            columns = base + ('decoded',)
        else:
            columns = base

        tree['columns'] = columns
        tree.heading('timestamp', text='Czas')
        tree.heading('id', text='ID')
        tree.heading('ext', text='EXT')
        tree.heading('dlc', text='DLC')
        if self.bit_view_active:
            tree.heading('bits', text='Bity')
            tree.column('bits', width=600)
        else:
            tree.heading('data', text='Dane (hex)')
            tree.column('data', width=300)

        if self.dbc_decoding_active:
            tree.heading('decoded', text='Zdekodowane')
            tree.column('decoded', width=300)

    def _refresh_decoded_column(self):
        tree = self.app.sniffer_tree
        for item in tree.get_children():
            values = tree.item(item, 'values')
            if len(values) >= 4:
                id_str = values[1]
                try:
                    can_id = int(id_str, 16)
                except ValueError:
                    continue
                raw_val = values[4]
                if self.bit_view_active:
                    data_hex = self._bits_to_hex(raw_val)
                else:
                    data_hex = raw_val
                try:
                    data = bytes.fromhex(data_hex)
                except ValueError:
                    continue
                decoded_str = self._decode_frame(can_id, data)
                new_values = values[:5] + (decoded_str or "",)
                if len(values) == 6:
                    pass
                tree.item(item, values=new_values)

    def _decode_frame(self, can_id, data):
        if not self.dbc_decoding_active or self.dbc_db is None:
            return None
        try:
            message = self.dbc_db.get_message_by_frame_id(can_id)
            decoded = message.decode(data)
            parts = []
            for sig_name, value in decoded.items():
                sig = message.get_signal_by_name(sig_name)
                unit = sig.unit if sig.unit else ""
                parts.append(f"{sig_name}: {value}{unit}".strip())
            return ", ".join(parts) if parts else ""
        except Exception:
            return None

    def show_signal_browser(self):
        if not self.dbc_decoding_active or self.dbc_db is None:
            messagebox.showinfo("Brak DBC", "Najpierw wczytaj plik DBC.")
            return

        tree = self.app.sniffer_tree
        selection = tree.selection()
        if not selection:
            messagebox.showinfo("Brak zaznaczenia", "Zaznacz ramkę w tabeli, aby wyświetlić sygnały.")
            return

        item = selection[0]
        values = tree.item(item, 'values')
        if len(values) < 4:
            return

        id_str = values[1]
        try:
            can_id = int(id_str, 16)
        except ValueError:
            messagebox.showerror("Błąd", f"Nieprawidłowy format ID: {id_str}")
            return

        raw_val = values[4]
        if self.bit_view_active:
            data_hex = self._bits_to_hex(raw_val)
        else:
            data_hex = raw_val

        try:
            data = bytes.fromhex(data_hex)
        except Exception:
            messagebox.showerror("Błąd", "Nie można odczytać danych ramki.")
            return

        try:
            message = self.dbc_db.get_message_by_frame_id(can_id)
            decoded = message.decode(data)
        except Exception as e:
            messagebox.showerror("Błąd dekodowania", f"Nie udało się zdekodować ramki:\n{e}")
            return

        win = tk.Toplevel(self.app.root)
        win.title(f"Sygnały dla ID 0x{can_id:08X}")
        win.geometry("650x450")
        win.transient(self.app.root)
        win.grab_set()

        info_frame = ttk.Frame(win)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(info_frame, text=f"ID: 0x{can_id:08X} | DLC: {len(data)} | Dane: {data_hex}",
                  font=('Arial', 9, 'bold')).pack(anchor=tk.W)

        tree_frame = ttk.Frame(win)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ('name', 'value', 'unit', 'min', 'max')
        tree_signals = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        tree_signals.heading('name', text='Sygnał')
        tree_signals.heading('value', text='Wartość')
        tree_signals.heading('unit', text='Jednostka')
        tree_signals.heading('min', text='Min')
        tree_signals.heading('max', text='Max')

        tree_signals.column('name', width=220)
        tree_signals.column('value', width=100)
        tree_signals.column('unit', width=80)
        tree_signals.column('min', width=80)
        tree_signals.column('max', width=80)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree_signals.yview)
        tree_signals.configure(yscrollcommand=vsb.set)
        tree_signals.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        for sig_name, value in decoded.items():
            sig = message.get_signal_by_name(sig_name)
            unit = sig.unit if sig.unit else ""
            min_val = f"{sig.minimum:.3f}" if sig.minimum is not None else "-"
            max_val = f"{sig.maximum:.3f}" if sig.maximum is not None else "-"
            tree_signals.insert("", tk.END, values=(sig_name, f"{value:.3f}", unit, min_val, max_val))

        ttk.Button(win, text="Zamknij", command=win.destroy).pack(pady=10)

    def open_dbc_editor(self):
        """Otwiera okno edytora DBC."""
        if not self.dbc_db:
            messagebox.showinfo("Brak DBC", "Najpierw wczytaj plik DBC.")
            return

        win = tk.Toplevel(self.app.root)
        win.title("Edytor DBC")
        win.geometry("800x600")
        win.transient(self.app.root)
        win.grab_set()

        tree = ttk.Treeview(win, columns=('message', 'signal', 'start', 'length'), show='headings')
        tree.heading('message', text='ID (hex)')
        tree.heading('signal', text='Sygnał')
        tree.heading('start', text='Start bit')
        tree.heading('length', text='Długość')

        for msg in self.dbc_db.messages:
            for sig in msg.signals:
                tree.insert('', tk.END, values=(
                    f"0x{msg.frame_id:08X}",
                    sig.name,
                    sig.start,
                    sig.length
                ))

        tree.pack(fill=tk.BOTH, expand=True)
        ttk.Button(win, text="Zapisz jako...", command=lambda: self.save_dbc_as()).pack(pady=10)

    def save_dbc_as(self):
        """Zapisuje aktualną bazę DBC do nowego pliku."""
        from tkinter import filedialog
        import cantools

        filepath = filedialog.asksaveasfilename(defaultextension=".dbc", filetypes=[("Pliki DBC", "*.dbc")])
        if not filepath:
            return
        try:
            cantools.database.dump_file(self.dbc_db, filepath)
            self.log(f"[DBC] Zapisano do {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd zapisu", str(e))
