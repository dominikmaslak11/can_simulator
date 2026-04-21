import time


class DisplayModes:
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
        self._configure_columns()

        if self.bit_view_active:
            for item in tree.get_children():
                values = tree.item(item, 'values')
                if len(values) >= 5:
                    data_hex = values[4]
                    bits_str = self._hex_to_bits(data_hex)
                    new_values = (values[0], values[1], values[2], values[3], bits_str)
                    if len(values) == 6:
                        new_values += (values[5],)
                    tree.item(item, values=new_values)
                    tree.item(item, tags=())
        else:
            for item in tree.get_children():
                values = tree.item(item, 'values')
                if len(values) >= 5:
                    bits_str = values[4]
                    data_hex = self._bits_to_hex(bits_str)
                    new_values = (values[0], values[1], values[2], values[3], data_hex)
                    if len(values) == 6:
                        new_values += (values[5],)
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
