"""System pluginów CAN Simulator GUI."""
import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from can_simulator.gui.app import CanSimulatorApp


def discover_plugins(app: "CanSimulatorApp"):
    """Skanuje katalog plugins/ i rejestruje znalezione moduły."""
    plugins_path = Path(__file__).resolve().parent
    for _, name, ispkg in pkgutil.iter_modules([str(plugins_path)]):
        if ispkg or name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"plugins.{name}")
            if hasattr(mod, "register"):
                mod.register(app)
                print(f"Plugin załadowany: {name}")
        except Exception as e:
            print(f"Błąd ładowania pluginu {name}: {e}")
