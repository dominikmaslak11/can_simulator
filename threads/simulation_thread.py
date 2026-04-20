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
        self.frames = []
        self.fixed_interval = 0.5
        self.loop = False
        self.speed = 1.0
        self.idx = 0

    def log(self, msg):
        logger.info(msg)
        if self.log_cb:
            self.log_cb(msg)

    def setup_replay(self, frames, fixed_interval, loop, speed=1.0):
        self.frames = frames
        self.fixed_interval = fixed_interval
        self.loop = loop
        self.speed = speed
        self.idx = 0
        self.log(f"Setup replay: {len(frames)} ramek, interwał={fixed_interval}, pętla={loop}, przysp={speed}")

    def setup_missing_module(self, interval_8f, interval_diag, interval_sporadic):
        self.mode = 'missing'
        self.interval_8f = interval_8f
        self.interval_diag = interval_diag
        self.interval_sporadic = interval_sporadic
        self.log(f"Setup missing module: 8F={interval_8f}, diag={interval_diag}, spor={interval_sporadic}")

    def setup_error_frames(self, interval, start_code):
        self.mode = 'error'
        self.interval = interval
        self.error_code = start_code
        self.log(f"Setup error frames: interwał={interval}, kod start={start_code}")

    def run(self):
        self.running = True
        self.log(f"Start symulacji, tryb={getattr(self, 'mode', 'replay')}")
        if hasattr(self, 'mode') and self.mode == 'missing':
            self._run_missing_module()
        elif hasattr(self, 'mode') and self.mode == 'error':
            self._run_error_frames()
        else:
            self._run_replay()
        self.log("Wątek symulacji zakończony")

    def _run_replay(self):
        while self.running:
            if not self.paused:
                if self.idx >= len(self.frames):
                    if self.loop:
                        self.idx = 0
                        self.log("--- Pętla od początku ---")
                    else:
                        break
                can_id, data, is_ext = self.frames[self.idx]
                success, msg = self.can.send_frame(can_id, data, is_ext)
                self.log(msg)
                self.idx += 1
                time.sleep(self.fixed_interval / self.speed)
            else:
                time.sleep(0.1)
        if not self.running:
            self.log("Zatrzymano odtwarzanie.")
        else:
            self.log("Zakończono odtwarzanie.")

    def _run_missing_module(self):
        counter_8F = 1
        sent_8F = 0
        last_8F = last_diag = last_sporadic = 0
        toggle = 0

        diag_frames = [
            (0x0C210005, b'\x01\x01\x00\x00\x00\x00\x00\x00', False),
            (0x0C220005, b'\x1E\xFF\x00\x00\x00\x2D\x00\x00', False),
            (0x0C230005, b'\x28\x0A\x00\x00\x00\x06\x00\x00', False),
            (0x08610005, b'\x06\x00\x00\x22\x02\x00\x0A\x01', False),
            (0x08620005, b'\x00\x00\x00\x00\x00\x00\x01\xEE', False),
            (0x19202324, b'\x02\x0F\xFF\xFF\x01\xFF\xFF\xFF', True),
            (0x19202324, b'\x04\x0F\xFF\xFF\xFF\xFF\xFF\xFF', True),
            (0x19202324, b'\x03\x0F\xFF\xFF\xFF\xFF\xFF\xFF', True),
            (0x19213536, b'\x01\x0F\xFF\xFF\xFF\xFF\xFF\xFF', True),
            (0x19213536, b'\x00\x0F\xFF\xFF\xFF\xFF\xFF\xFF', True),
            (0x18202423, b'\x02\x05\x00\x00\x00\x5A\x0F\xFF', True),
            (0x18202423, b'\x04\x05\x00\x00\x00\x0A\x0F\xFF', True),
            (0x18202423, b'\x03\x06\x00\x00\x00\x00\x0F\xFF', True),
            (0x18213635, b'\x01\x05\x00\x00\x00\x00\x0F\xFF', True),
            (0x18213635, b'\x00\x05\x00\x00\xAA\xA9\x0F\xFF', True),
            (0x112A6061, b'\x02\x0F\xFF\xFF\xFF\xFF\xFF\xFF', True),
            (0x102A6160, b'\x02\x05\x00\xFF\xFF\xFF\x0F\xFF', True),
        ]

        data_1cff = b'\x11\x00\x75\x30\x75\x30\x00\xDD'

        while self.running:
            now = time.time()
            if not self.paused:
                if now - last_8F >= self.interval_8f:
                    data = bytes([counter_8F & 0xFF, (counter_8F >> 8) & 0xFF]) + b'\x00'*6
                    self.can.send_frame(0x0C00008F, data, True)
                    self.log(f"[{sent_8F+1}] 0C00008F#{data.hex().upper()}")
                    self.can.send_frame(0x1CFF66F0, data_1cff, True)
                    self.log(f"      1CFF66F0#{data_1cff.hex().upper()}")
                    sent_8F += 1
                    counter_8F += 1
                    if counter_8F > 0xFFFF:
                        counter_8F = 1
                    last_8F = now

                if now - last_diag >= self.interval_diag:
                    self.log(">> Zestaw diagnostyczny")
                    for cid, cdata, cext in diag_frames:
                        self.can.send_frame(cid, cdata, cext)
                        time.sleep(0.01)
                    last_diag = now

                if now - last_sporadic >= self.interval_sporadic:
                    if toggle % 2 == 0:
                        d1 = b'\xFF\xFF\xFF\xFF\x9F\x01\xFF\xFF'
                        d2 = b'\x00\x96\x00\x00\x95\x01\x0F\xFF'
                    else:
                        d1 = b'\xFF\x00\xFF\xFF\x9F\x00\xFF\xFF'
                        d2 = b'\x00\x96\x00\x00\x95\x00\x0F\xFF'
                    self.can.send_frame(0x11204032, d1, True)
                    self.can.send_frame(0x10203240, d2, True)
                    self.log(">> Ramki sporadyczne")
                    toggle += 1
                    last_sporadic = now
            time.sleep(0.05)
        self.log("Symulacja modułu zakończona.")

    def _run_error_frames(self):
        sent = 0
        code = self.error_code
        while self.running:
            if not self.paused:
                data_err = bytes([0x00, code & 0xFF]) + b'\x00'*6
                self.can.send_frame(0x0C000005, data_err, False)
                self.log(f"[{sent+1}] 0C000005#{data_err.hex().upper()}")
                time.sleep(0.25)
                data_diag = bytes([0x00, 0x16, 0x0B, 0x04, 0x03, 0x09, 0xA0 | (code & 0x0F), 0x00])
                self.can.send_frame(0x14200032, data_diag, True)
                self.log(f"      14200032#{data_diag.hex().upper()}")
                sent += 1
                code += 1
                if code > 0xFF:
                    code = self.error_code
                time.sleep(self.interval - 0.25)
            else:
                time.sleep(0.1)
        self.log("Symulacja błędów zakończona.")

    def stop(self):
        self.running = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
