import time
import threading
import logging

logger = logging.getLogger("SimulationThread")

class SimulationThread(threading.Thread):
    def __init__(self, can_if, log_callback):
        super().__init__(daemon=True)
        self.can = can_if
        self.log_cb = log_callback
        self.running = False
        self.paused = False
        self.frames = []               # dla trybu replay
        self.fixed_interval = 0.5
        self.loop = False
        self.speed = 1.0
        self.idx = 0

        # Tryb missing – lista ramek z GUI
        self.missing_frames = []       # lista słowników: {id, data, ext, interval, next_time}
        self.missing_timers = {}       # id -> next_time

        # Tryb error – lista ramek z GUI
        self.error_frames = []         # lista słowników: {id, data, ext, delay}
        self.error_interval = 10.0     # odstęp między sekwencjami

    def log(self, msg):
        logger.info(msg)
        if self.log_cb:
            self.log_cb(msg)

    # ------------------------------------------------------------------
    # Konfiguracja trybów
    # ------------------------------------------------------------------
    def setup_replay(self, frames, fixed_interval, loop, speed=1.0):
        self.mode = 'replay'
        self.frames = frames
        self.fixed_interval = fixed_interval
        self.loop = loop
        self.speed = speed
        self.idx = 0
        self.log(f"Setup replay: {len(frames)} ramek, interwał={fixed_interval}")

    def setup_missing_module(self, frames):
        """Przyjmuje listę ramek z tabeli GUI."""
        self.mode = 'missing'
        self.missing_frames = frames or []
        # Inicjalizacja timerów – każda ramka może być wysłana natychmiast
        now = time.time()
        for f in self.missing_frames:
            f['next_time'] = now
        self.log(f"Setup missing module: {len(self.missing_frames)} ramek z GUI")

    def setup_error_frames(self, interval, frames):
        """Przyjmuje interwał powtarzania sekwencji oraz listę ramek z tabeli GUI."""
        self.mode = 'error'
        self.error_interval = interval
        self.error_frames = frames or []
        self.log(f"Setup error frames: interwał sekwencji={interval}, ramek={len(self.error_frames)}")

    # ------------------------------------------------------------------
    # Główna pętla
    # ------------------------------------------------------------------
    def run(self):
        self.running = True
        self.log(f"Start symulacji, tryb={getattr(self, 'mode', 'replay')}")
        if self.mode == 'missing':
            self._run_missing()
        elif self.mode == 'error':
            self._run_error()
        else:
            self._run_replay()
        self.log("Wątek symulacji zakończony")

    def _run_replay(self):
        last_ts = None
        while self.running:
            if not self.paused:
                if self.idx >= len(self.frames):
                    if self.loop:
                        self.idx = 0
                        last_ts = None
                        self.log("--- Pętla od początku ---")
                    else:
                        break
                can_id, data, is_ext, ts = self.frames[self.idx]
                if ts is not None:
                    if last_ts is not None and ts > last_ts:
                        time.sleep((ts - last_ts) / self.speed)
                    last_ts = ts
                else:
                    time.sleep(self.fixed_interval / self.speed)

                success, msg = self.can.send_frame(can_id, data, is_ext)
                self.log(msg)
                self.idx += 1
            else:
                time.sleep(0.1)
        if not self.running:
            self.log("Zatrzymano odtwarzanie.")
        else:
            self.log("Zakończono odtwarzanie.")

    def _run_missing(self):
        """Wysyła każdą ramkę z listy GUI z jej własnym interwałem."""
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            now = time.time()
            for f in self.missing_frames:
                if now >= f['next_time']:
                    self.can.send_frame(f['id'], f['data'], f['ext'])
                    self.log(f"[Missing] ID=0x{f['id']:08X} Data={f['data'].hex().upper()}")
                    f['next_time'] = now + f['interval']
            time.sleep(0.01)  # mała pauza, aby nie obciążać CPU

    def _run_error(self):
        """Wysyła całą sekwencję ramek z tabeli, powtarzając co error_interval."""
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            for f in self.error_frames:
                if not self.running:
                    break
                self.can.send_frame(f['id'], f['data'], f['ext'])
                self.log(f"[Error] ID=0x{f['id']:08X} Data={f['data'].hex().upper()}")
                time.sleep(f['delay'])
            # Odstęp przed kolejną sekwencją
            time.sleep(self.error_interval)

    # ------------------------------------------------------------------
    # Sterowanie
    # ------------------------------------------------------------------
    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
