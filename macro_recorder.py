import json
import time
import threading

class MacroRecorder:
    def __init__(self, app):
        self.app = app
        self.recording = False
        self.playing = False
        self.events = []
        self.start_time = None
        self.hooks = []

    def start_recording(self):
        self.recording = True
        self.events = []
        self.start_time = time.time()
        self._install_hooks()
        self.app.log("[Makro] Rozpoczęto nagrywanie.")

    def stop_recording(self):
        self.recording = False
        self._remove_hooks()
        self.app.log(f"[Makro] Zakończono nagrywanie. Zarejestrowano {len(self.events)} zdarzeń.")

    def record_event(self, event_type, **kwargs):
        if not self.recording:
            return
        timestamp = time.time() - self.start_time
        self.events.append({
            "time": timestamp,
            "type": event_type,
            "args": kwargs
        })

    def _install_hooks(self):
        # Podpinamy się do wysyłania ramek w CanInterface
        original_send = self.app.can.send_frame
        def hooked_send(can_id, data, is_extended=None):
            self.record_event("send_frame", id=can_id, data=data.hex(), ext=is_extended)
            return original_send(can_id, data, is_extended)
        self.app.can.send_frame = hooked_send
        self.hooks.append(("send_frame", original_send))

        # Hooki na zmianę zakładek, przyciski itp. można dodać analogicznie
        # (na potrzeby podstawowej wersji wystarczy nagrywanie wysyłania)

    def _remove_hooks(self):
        for hook_name, original in self.hooks:
            setattr(self.app.can, hook_name, original)
        self.hooks.clear()

    def save(self, filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0",
                "events": self.events
            }, f, indent=2)
        self.app.log(f"[Makro] Zapisano do {filepath}")

    def load(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.events = data.get("events", [])
        self.app.log(f"[Makro] Wczytano {len(self.events)} zdarzeń z {filepath}")

    def play(self, loop=False):
        if self.playing:
            return
        self.playing = True
        self.app.log("[Makro] Rozpoczęto odtwarzanie.")
        def player():
            while True:
                for ev in self.events:
                    if not self.playing:
                        break
                    time.sleep(ev['time'] if not loop else ev['time'] / 10)  # uproszczone
                    if ev['type'] == 'send_frame':
                        args = ev['args']
                        self.app.can.send_frame(args['id'], bytes.fromhex(args['data']), args['ext'])
                if not loop:
                    break
            self.playing = False
            self.app.root.after(0, self._play_done)
        threading.Thread(target=player, daemon=True).start()

    def _play_done(self):
        self.app.log("[Makro] Odtwarzanie zakończone.")
        self.app.macro_play_btn.config(state='normal')
        self.app.macro_stop_btn.config(state='disabled')

    def stop_playback(self):
        self.playing = False
