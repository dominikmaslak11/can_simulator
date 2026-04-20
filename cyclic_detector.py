import time
import logging
logger = logging.getLogger("CyclicDetector")

class CyclicDetector:
    def __init__(self, alert_id, expected_period, tolerance=0.2):
        self.alert_id = alert_id
        self.expected_period = expected_period
        self.tolerance = tolerance
        self.last_seen = None
        self.alert_active = False
        self.candidates = []
        self.max_candidates = 100
        self.deactivation_time = None

    def reset(self):
        self.last_seen = None
        self.alert_active = False
        self.candidates.clear()
        self.deactivation_time = None

    def feed_frame(self, can_id, data, is_extended, timestamp):
        self.candidates.append((can_id, data, is_extended, timestamp))
        if len(self.candidates) > self.max_candidates:
            self.candidates.pop(0)

        if can_id == self.alert_id:
            if self.last_seen is not None:
                delta = timestamp - self.last_seen
                if delta <= self.expected_period * (1 + self.tolerance):
                    self.alert_active = True
                else:
                    self.alert_active = True
            else:
                self.alert_active = True
            self.last_seen = timestamp
            return False

        if self.last_seen is not None and self.alert_active:
            now = timestamp
            if now - self.last_seen > self.expected_period * (1 + self.tolerance):
                self.alert_active = False
                self.deactivation_time = now
                return True
        return False

    def get_candidate_window(self, window_before=0.5):
        if self.deactivation_time is None:
            return []
        cutoff = self.deactivation_time - window_before
        return [c for c in self.candidates if cutoff <= c[3] <= self.deactivation_time]
