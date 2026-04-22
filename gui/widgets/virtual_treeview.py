import tkinter as tk
from tkinter import ttk
import logging

logger = logging.getLogger("VirtualTreeview")

class VirtualTreeview(ttk.Treeview):
    """Treeview z obsługą wirtualną dla dużej liczby wierszy."""
    def __init__(self, master, columns, displaycolumns=None, **kwargs):
        super().__init__(master, columns=columns, displaycolumns=displaycolumns, **kwargs)
        self._data = []
        self._virtual_mode = True
        self._bind_virtual_events()

    def _bind_virtual_events(self):
        self.bind('<<TreeviewOpen>>', self._on_virtual_event)
        self.bind('<<TreeviewClose>>', self._on_virtual_event)
        self.bind('<ButtonPress-1>', self._on_virtual_event)

    def _on_virtual_event(self, event):
        if not self._virtual_mode:
            return
        self._refresh_view()

    def set_data(self, data):
        """Ustawia dane i odświeża widok."""
        self._data = data
        self._refresh_view()

    def _refresh_view(self):
        """Odświeża widok na podstawie widocznych elementów."""
        self.delete(*self.get_children())
        if not self._data:
            return

        # Wyświetl tylko pierwsze 1000 wierszy (lub dostosuj)
        visible_items = self._data[:1000]
        for item in visible_items:
            self.insert('', tk.END, values=item)

    def append(self, values):
        """Dodaje pojedynczy wiersz."""
        self._data.append(values)
        if not self._virtual_mode or len(self.get_children()) < 1000:
            self.insert('', tk.END, values=values)

    def clear(self):
        self._data.clear()
        self.delete(*self.get_children())

    def get_all_items(self):
        return self._data
