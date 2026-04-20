#!/usr/bin/env python3
import sys
import os
import logging
import traceback
from datetime import datetime

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("can_simulator.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CANSimulator")

def excepthook(exc_type, exc_value, exc_tb):
    logger.critical("Nieobsłużony wyjątek", exc_info=(exc_type, exc_value, exc_tb))
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = excepthook

logger.info("=== CAN Simulator GUI ===")
logger.info(f"Czas: {datetime.now()}, Python: {sys.version}")

try:
    import tkinter as tk
    from gui.app import CanSimulatorApp
except Exception as e:
    logger.critical("Import error", exc_info=True)
    sys.exit(1)

if __name__ == "__main__":
    root = tk.Tk()
    app = CanSimulatorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
