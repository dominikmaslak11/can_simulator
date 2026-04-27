from datetime import datetime
from tkinter import messagebox
import threading
import tkinter as tk


class CoreMethods:
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

        tree.tag_configure('changed', background='#FFB6C1')

        for ts, can_id, data, is_ext in frames:
            if filter_active and can_id not in filter_ids:
                continue
            timestamp = datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]
            ext_str = "X" if is_ext else ""
            dlc = len(data)
            data_hex = data.hex().upper()
            bits_str = self._hex_to_bits(data_hex)
            decoded_str = self._decode_frame(can_id, data)

            tags = ()
            if self.bit_view_active:
                last_bits = self.app.sniffer_last_bits.get(can_id)
                if last_bits is not None and last_bits != bits_str:
                    tags = ('changed',)

            display_value = bits_str if self.bit_view_active else data_hex
            base_values = (timestamp, f"0x{can_id:08X}", ext_str, dlc, display_value)
            values = base_values + (decoded_str or "",) if self.dbc_decoding_active else base_values

            if self.keep_alive_active:
                item_to_update = None
                for item, (cid, _) in self.alive_items.items():
                    if cid == can_id:
                        item_to_update = item
                        break
                if item_to_update:
                    tree.item(item_to_update, values=values)
                    tree.tag_configure('alive', foreground='black')
                    final_tags = ('alive',) + tags
                    tree.item(item_to_update, tags=final_tags)
                    self.alive_items[item_to_update] = (can_id, ts)
                else:
                    item = tree.insert("", tk.END, values=values)
                    tree.tag_configure('alive', foreground='black')
                    final_tags = ('alive',) + tags
                    tree.item(item, tags=final_tags)
                    self.alive_items[item] = (can_id, ts)

                if self.bit_view_active:
                    self.app.sniffer_last_bits[can_id] = bits_str
                else:
                    self.app.sniffer_last_data[can_id] = data_hex

            elif self.overwrite_active:
                if can_id in self.overwrite_items:
                    item = self.overwrite_items[can_id]
                    tree.item(item, values=values)
                    tree.item(item, tags=tags)
                else:
                    item = tree.insert("", tk.END, values=values)
                    self.overwrite_items[can_id] = item
                    tree.item(item, tags=tags)

            else:
                item = tree.insert("", tk.END, values=values)
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

    def highlight_time_range(self, start_time, end_time):
        tree = self.app.sniffer_tree
        for item in tree.get_children():
            tags = tree.item(item, 'tags')
            if 'ml_highlight' in tags:
                new_tags = tuple(t for t in tags if t != 'ml_highlight')
                tree.item(item, tags=new_tags)

        tree.tag_configure('ml_highlight', background='#FFD700')

        count = 0
        for item in tree.get_children():
            values = tree.item(item, 'values')
            if len(values) < 1:
                continue
            time_str = values[0]
            try:
                dt = datetime.strptime(time_str, "%H:%M:%S.%f")
                ts = dt.timestamp()
            except:
                continue

            if start_time <= ts <= end_time:
                current_tags = tree.item(item, 'tags')
                if current_tags:
                    new_tags = current_tags + ('ml_highlight',)
                else:
                    new_tags = ('ml_highlight',)
                tree.item(item, tags=new_tags)
                count += 1

        if count > 0:
            for item in tree.get_children():
                if 'ml_highlight' in tree.item(item, 'tags'):
                    tree.see(item)
                    break

        self.app.sniffer_status.set(f"Podświetlono {count} ramek.")


    def set_highlighted_ids(self, ids):
        """Ustawia listę ID do podświetlenia (iterable)."""
        self.highlighted_ids = set(ids)
        self.refresh_treeview()

