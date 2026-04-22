from tkinter import filedialog, messagebox
import csv


class ExportMethods:
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
                else:
                    data_hex = values[4]
                f.write(f"{values[0]} can0 {values[1]}#{data_hex}\n")
        self.log(f"[Sniffer] Wyeksportowano do {filepath}")

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Pliki CSV", "*.csv"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        tree = self.app.sniffer_tree
        columns = tree['columns']
        headers = [tree.heading(col)['text'] for col in columns]

        rows = []
        for item in tree.get_children():
            values = tree.item(item, 'values')
            if self.bit_view_active and len(values) >= 5:
                bits_str = values[4]
                data_hex = self._bits_to_hex(bits_str)
                values = list(values)
                values[4] = data_hex
                values = tuple(values)
            rows.append(values)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            self.log(f"[Sniffer] Wyeksportowano {len(rows)} ramek do CSV: {filepath}")
        except Exception as e:
            messagebox.showerror("Błąd eksportu", f"Nie udało się zapisać pliku:\n{e}")

    def export_asc(self):
        """Eksportuje zawartość tabeli do pliku w formacie Vector ASC."""
        from tkinter import filedialog
        import datetime

        filepath = filedialog.asksaveasfilename(
            defaultextension=".asc",
            filetypes=[("Pliki ASC", "*.asc"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        tree = self.app.sniffer_tree

        with open(filepath, 'w', encoding='utf-8') as f:
            # Nagłówek ASC
            f.write("date %s\n" % datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
            f.write("base hex  timestamps absolute\n")
            f.write("internal events logged\n")
            f.write("// Eksport z CAN Simulator GUI\n")

            # Przeliczenie czasu startu (pierwsza ramka)
            first_item = tree.get_children()[0] if tree.get_children() else None
            if first_item:
                first_values = tree.item(first_item, 'values')
                start_time_str = first_values[0]
                try:
                    dt = datetime.datetime.strptime(start_time_str, "%H:%M:%S.%f")
                    start_sec = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6
                except:
                    start_sec = 0.0
            else:
                start_sec = 0.0

            for item in tree.get_children():
                values = tree.item(item, 'values')
                if len(values) < 5:
                    continue
                timestamp_str = values[0]
                try:
                    dt = datetime.datetime.strptime(timestamp_str, "%H:%M:%S.%f")
                    current_sec = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6
                    relative_time = current_sec - start_sec
                except:
                    relative_time = 0.0

                # ID – usuwamy prefiks "0x"
                id_str = values[1].replace("0x", "").upper()
                # EXT (kolumna 2) – pomijamy, ASC ma własny format dla extended
                dlc = values[3]   # kolumna 3 to DLC (ale w snifferze nie ma osobnej kolumny DLC? trzeba dostosować)
                # W snifferze kolumny: timestamp, id, ext, dlc, data
                # Jeśli nie ma dlc, obliczamy z danych
                data_hex = values[4]
                if ' ' in data_hex:   # widok bitowy
                    # Konwertujemy bity na hex
                    data_hex = self._bits_to_hex(data_hex)
                data_bytes = bytes.fromhex(data_hex)
                dlc = len(data_bytes)

                # Format ASC:   timestamp 1  IDx  Rx  d 8 01 02 03 ...
                # Dla uproszczenia użyjemy "1" jako kanał, "Rx" jako kierunek
                line = f" {relative_time:12.6f} 1  {id_str}x  Rx  d {dlc}"
                for byte in data_bytes:
                    line += f" {byte:02X}"
                f.write(line + "\n")

        self.log(f"[Sniffer] Wyeksportowano do ASC: {filepath}")

    def export_parquet(self):
        """Eksportuje zawartość tabeli do pliku Parquet."""
        from tkinter import filedialog
        import pyarrow as pa
        import pyarrow.parquet as pq

        filepath = filedialog.asksaveasfilename(
            defaultextension=".parquet",
            filetypes=[("Pliki Parquet", "*.parquet"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        tree = self.app.sniffer_tree
        rows = []
        for item in tree.get_children():
            values = tree.item(item, 'values')
            if len(values) >= 5:
                timestamp = values[0]
                can_id = int(values[1], 16)
                data_hex = values[4]
                if ' ' in data_hex:
                    data_hex = self._bits_to_hex(data_hex)
                rows.append({
                    'timestamp': timestamp,
                    'can_id': can_id,
                    'data': data_hex,
                    'dlc': len(bytes.fromhex(data_hex))
                })

        if rows:
            table = pa.Table.from_pylist(rows)
            pq.write_table(table, filepath)
            self.log(f"[Sniffer] Wyeksportowano {len(rows)} ramek do Parquet: {filepath}")

    def export_mdf4(self):
        """Eksportuje zawartość tabeli do pliku MDF4."""
        from tkinter import filedialog
        import asammdf
        import numpy as np
        from datetime import datetime

        filepath = filedialog.asksaveasfilename(
            defaultextension=".mf4",
            filetypes=[("Pliki MDF4", "*.mf4"), ("Wszystkie pliki", "*.*")]
        )
        if not filepath:
            return

        tree = self.app.sniffer_tree
        signals = {}
        timestamps = []

        for item in tree.get_children():
            values = tree.item(item, 'values')
            if len(values) >= 5:
                ts_str = values[0]
                try:
                    dt = datetime.strptime(ts_str, "%H:%M:%S.%f")
                    t = dt.hour*3600 + dt.minute*60 + dt.second + dt.microsecond/1e6
                except:
                    t = 0.0
                timestamps.append(t)
                can_id = values[1]
                data_hex = values[4]
                if ' ' in data_hex:
                    data_hex = self._bits_to_hex(data_hex)
                data_bytes = bytes.fromhex(data_hex)
                for i, byte in enumerate(data_bytes):
                    sig_name = f"{can_id}_B{i}"
                    signals.setdefault(sig_name, []).append(byte)

        if timestamps:
            mdf = asammdf.MDF()
            timestamps_np = np.array(timestamps, dtype=np.float64)
            for name, values in signals.items():
                if len(values) == len(timestamps):
                    sig = asammdf.Signal(
                        samples=np.array(values, dtype=np.uint8),
                        timestamps=timestamps_np,
                        name=name,
                        unit=''
                    )
                    mdf.append(sig)
            mdf.save(filepath, overwrite=True)
            self.log(f"[Sniffer] Wyeksportowano do MDF4: {filepath}")
