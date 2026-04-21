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
