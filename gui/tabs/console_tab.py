"""Wbudowana konsola Python (Tkinter)."""
import tkinter as tk
from tkinter import ttk
import code
import sys

class ConsoleWidget(tk.Frame):
    def __init__(self, app, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app
        self.interp = code.InteractiveConsole(locals={"app": app})
        self.create_widgets()
        self.redirect_output()

    def create_widgets(self):
        self.output = tk.Text(self, state='disabled', wrap='word', bg='black', fg='white')
        self.output.pack(fill=tk.BOTH, expand=True)

        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.X)

        self.input_field = ttk.Entry(bottom)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.input_field.bind("<Return>", self.execute)

        ttk.Button(bottom, text="Wyczyść", command=self.clear_output).pack(side=tk.RIGHT)

    def redirect_output(self):
        import io
        self._stdout_orig = sys.stdout
        self._stderr_orig = sys.stderr
        sys.stdout = self
        sys.stderr = self

    def write(self, text):
        self.output.configure(state='normal')
        self.output.insert(tk.END, text)
        self.output.see(tk.END)
        self.output.configure(state='disabled')

    def flush(self):
        pass

    def execute(self, event=None):
        code = self.input_field.get()
        self.input_field.delete(0, tk.END)
        self.write(f">>> {code}\n")
        self.interp.push(code)

    def clear_output(self):
        self.output.configure(state='normal')
        self.output.delete('1.0', tk.END)
        self.output.configure(state='disabled')

    def destroy(self):
        sys.stdout = self._stdout_orig
        sys.stderr = self._stderr_orig
        super().destroy()
