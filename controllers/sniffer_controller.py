from .base_controller import BaseController
from tkinter import filedialog, messagebox
from datetime import datetime
import threading
import time
import tkinter as tk

class SnifferController(BaseController):
    def __init__(self, app):
        super().__init__(app)
        self.app.sniffer_queue = []
        self.app.sniffer_lock = threading.Lock()
        self.app.sniffer_last_data = {}       # ID -> ostatnie dane (hex)
        self.app.sniffer_last_bits = {}       # ID -> ostatnie bity (string)
        self.app.sniffer_keep_alive_var = None
        self.app.sniffer_overwrite_var = None
        self.app.sniffer_bit_view_var = None
        self.keep_alive_active = False
        self.overwrite_active = False
        self.bit_view_active = False
        self.keep_alive_timeout = 2.0
        self.alive_items = {}
        self.overwrite_items = {}

    def toggle_keep_alive(self):
        self.keep_alive_active = self.app.sniffer_keep_alive_var.get()
        if self.keep_alive_active:
            if self.overwrite_active:
                self.app.sniffer_overwrite_var.set(False)
                self.overwrite_active = False
                self.overwrite_items.clear()
            self._start_keep_alive_timer()

    def toggle_overwrite(self):
        self.overwrite_active = self.app.sniffer_overwrite_var.get()
        if self.overwrite_active:
            if self.keep_alive_active:
                self.app.sniffer_keep_alive_var.set(False)
                self.keep_alive_active = False
                self.alive_items.clear()
            self.clear_sniffer()

    def toggle_bit_view(self):
        self.bit_view_active = self.app.sniffer_bit_view_var.get()
        tree = self.app.sniffer_tree

        if self.bit_view_active:
            tree['columns'] = self.app.sniffer_columns_bit
            tree.heading('bits', text='Bity')
            tree.column('bits', width=600)

            for item in tree.get_children():
                values = tree.item(item, 'values')
                if len(values) >= 5:
                    data_hex = values[4]
                    bits_str = self._hex_to_bits(data_hex)
                    new_values = (values[0], values[1], values[2], values[3], bits_str)
                    tree.item(item, values=new_values)
                    # Reset kolorów
                    tree.item(item, tags=())
        else:
            tree['columns'] = self.app.sniffer_columns_normal
            tree.heading('data', text='Dane (hex)')
            tree.column('data', width=300)

            for item in tree.get_children():
                values = tree.item(item, 'values')
                if len(values) >= 5:
                    bits_str = values[4]
                    data_hex = self._bits_to_hex(bits_str)
                    new_values = (values[0], values[1], values[2], values[3], data_hex)
                    tree.item(item, values=new_values)
                    tree.item(item, tags=())

    def _hex_to_bits(self, hex_str):
        try:
            data = bytes.fromhex(hex_str)
            bits = []
            for byte in data:
                for i in range(7, -1, -1):
                    bits.append(str((byte >> i) & 1))
            return ' '.join([''.join(bits[i:i+8]) for i in range(0, len(bits), 8)])
        except:
            return ''

    def _bits_to_hex(self, bits_str):
        try:
            bits = bits_str.replace(' ', '')
            data = bytearray()
            for i in range(0, len(bits), 8):
                byte_bits = bits[i:i+8]
                if len(byte_bits) == 8:
                    data.append(int(byte_bits, 2))
            return data.hex().upper()
        except:
            return ''

    def _start_keep_alive_timer(self):
        def check_alive():
            if not self.keep_alive_active:
                return
            now = time.time()
            tree = self.app.sniffer_tree
            for item, (cid, last_ts) in list(self.alive_items.items()):
                if now - last_ts > self.keep_alive_timeout:
                    tree.tag_configure('grayed', foreground='gray')
                    tree.item(item, tags=('grayed',))
            self.app.root.after(1000, check_alive)
        self.app.root.after(1000, check_alive)

    def start_sniffer(self):
        if not self.app.can.connected:
            messagebox.showerror("Błąd", "Połącz się z CAN")
            return
        self.app.sniffer_running = True
        self.app.sniffer_start_btn.config(state='disabled')
        self.app.sniffer_stop_btn.config(state='normal')
        self.app.sniffer_status.set("Nasłuchiwanie...")

        def frame_callback(ts, can_id, data, is_ext):
            with self.app.sniffer_lock:
                self.app.sniffer_queue.append((ts, can_id, data, is_ext))
            self.app.root.after(10, self._process_queue)

        self.app.can.start_receiving(frame_callback)

    def stop_sniffer(self):
        self.app.can.stop_receiving()
        self.app.sniffer_running = False
        self.app.sniffer_start_btn.config(state='normal')
        self.app.sniffer_stop_btn.config(state='disabled')
        self.app.sniffer_status.set("Zatrzymany")

    def _process_queue(self):
        with self.app.sniffer_lock:
            frames, self.app.sniffer_queue = self.app.sniffer_queue, []
        if not frames:
            return
        tree = self.app.sniffer_tree
        filter_active = self.app.sniffer_filter_var.get()
        filter_ids = set()
        if filter_active:
            text = self.app.sniffer_filter_entry.get().strip()
            if text:
                try:
                    filter_ids = set(int(x.strip(), 16) for x in text.split(','))
                except ValueError:
                    pass

        if not self.keep_alive_active and not self.overwrite_active:
            children = tree.get_children()
            if len(children) > 1000:
                for i in range(len(children) - 1000):
                    tree.delete(children[i])

        # Konfiguracja tagu dla zmienionych bitów
        tree.tag_configure('changed', background='#FFB6C1')  # jasnoczerwony

        for ts, can_id, data, is_ext in frames:
            if filter_active and can_id not in filter_ids:
                continue
            timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]
            ext_str = "X" if is_ext else ""
            dlc = len(data)
            data_hex = data.hex().upper()
            bits_str = self._hex_to_bits(data_hex)

            # Określenie tagów (kolorowanie)
            tags = ()
            if self.bit_view_active:
                last_bits = self.app.sniffer_last_bits.get(can_id)
                if last_bits is not None and last_bits != bits_str:
                    tags = ('changed',)

            if self.keep_alive_active:
                item_to_update = None
                for item, (cid, _) in self.alive_items.items():
                    if cid == can_id:
                        item_to_update = item
                        break
                display_value = bits_str if self.bit_view_active else data_hex
                if item_to_update:
                    tree.item(item_to_update, values=(timestamp, f"0x{can_id:08X}", ext_str, dlc, display_value))
                    tree.tag_configure('alive', foreground='black')
                    final_tags = ('alive',) + tags
                    tree.item(item_to_update, tags=final_tags)
                    self.alive_items[item_to_update] = (can_id, ts)
                else:
                    item = tree.insert("", tk.END, values=(timestamp, f"0x{can_id:08X}", ext_str, dlc, display_value))
                    tree.tag_configure('alive', foreground='black')
                    final_tags = ('alive',) + tags
                    tree.item(item, tags=final_tags)
                    self.alive_items[item] = (can_id, ts)

                if self.bit_view_active:
                    self.app.sniffer_last_bits[can_id] = bits_str
                else:
                    self.app.sniffer_last_data[can_id] = data_hex

            elif self.overwrite_active:
                display_value = bits_str if self.bit_view_active else data_hex
                if can_id in self.overwrite_items:
                    item = self.overwrite_items[can_id]
                    tree.item(item, values=(timestamp, f"0x{can_id:08X}", ext_str, dlc, display_value))
                    tree.item(item, tags=tags)
                else:
                    item = tree.insert("", tk.END, values=(timestamp, f"0x{can_id:08X}", ext_str, dlc, display_value))
                    self.overwrite_items[can_id] = item
                    tree.item(item, tags=tags)

            else:
                display_value = bits_str if self.bit_view_active else data_hex
                item = tree.insert("", tk.END, values=(timestamp, f"0x{can_id:08X}", ext_str, dlc, display_value))
                tree.item(item, tags=tags)
                if self.bit_view_active:
                    self.app.sniffer_last_bits[can_id] = bits_str
                else:
                    self.app.sniffer_last_data[can_id] = data_hex

    def clear_sniffer(self):
        self.app.sniffer_tree.delete(*self.app.sniffer_tree.get_children())
        self.app.sniffer_last_data.clear()
        self.app.sniffer_last_bits.clear()
        self.alive_items.clear()
        self.overwrite_items.clear()

    def export_sniffer(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".log",
                                                filetypes=[("Logi", "*.log"), ("Wszystkie", "*.*")])
        if not filepath:
            return
        with open(filepath, 'w') as f:
            for item in self.app.sniffer_tree.get_children():
                values = self.app.sniffer_tree.item(item, 'values')
                if self.bit_view_active:
                    bits_str = values[4]
                    data_hex = self._bits_to_hex(bits_str)
                    f.write(f"{values[0]} can0 {values[1]}#{data_hex}\n")
                else:
                    f.write(f"{values[0]} can0 {values[1]}#{values[4]}\n")
        self.log(f"[Sniffer] Wyeksportowano do {filepath}")

    def toggle_filter(self):
        if self.app.sniffer_filter_var.get():
            self.app.sniffer_filter_entry.config(state='normal')
        else:
            self.app.sniffer_filter_entry.config(state='disabled')

    def apply_filter(self):
        pass
