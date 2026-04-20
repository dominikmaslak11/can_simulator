import pytest
import time
from cyclic_detector import CyclicDetector


class TestCyclicDetector:
    def test_alert_detection_and_regular_period(self):
        detector = CyclicDetector(alert_id=0x123, expected_period=1.0, tolerance=0.2)
        now = 1000.0
        assert not detector.feed_frame(0x123, b'', False, now)
        assert detector.alert_active
        now += 1.0
        assert not detector.feed_frame(0x123, b'', False, now)
        assert detector.alert_active

    def test_deactivation_detection(self):
        detector = CyclicDetector(alert_id=0x123, expected_period=1.0, tolerance=0.2)
        now = 1000.0
        detector.feed_frame(0x123, b'', False, now)
        now += 1.3
        deactivated = detector.feed_frame(0x456, b'', False, now)
        assert deactivated
        assert not detector.alert_active

    def test_tolerance_window(self):
        detector = CyclicDetector(alert_id=0x123, expected_period=1.0, tolerance=0.1)
        now = 1000.0
        detector.feed_frame(0x123, b'', False, now)
        now += 1.09
        assert not detector.feed_frame(0x123, b'', False, now)
        assert detector.alert_active
        now += 1.2
        deactivated = detector.feed_frame(0x456, b'', False, now)
        assert deactivated

    def test_candidate_window(self):
        detector = CyclicDetector(alert_id=0x123, expected_period=0.5, tolerance=0.2)
        now = 1000.0
        detector.feed_frame(0x123, b'1', False, now)      # alert
        now += 0.1
        detector.feed_frame(0x200, b'2', True, now)       # kandydat
        now += 0.1
        detector.feed_frame(0x300, b'3', False, now)      # kandydat
        now += 0.7  # czas poza tolerancją – następna ramka wywoła dezaktywację
        deactivated = detector.feed_frame(0x400, b'4', True, now)
        assert deactivated

        # Okno 0.9 s – powinno objąć wszystkie trzy ramki (0x200, 0x300, 0x400)
        candidates = detector.get_candidate_window(window_before=0.9)
        assert len(candidates) == 3
        assert candidates[0][0] == 0x200
        assert candidates[1][0] == 0x300
        assert candidates[2][0] == 0x400

    def test_reset(self):
        detector = CyclicDetector(alert_id=0x123, expected_period=1.0)
        now = 1000.0
        detector.feed_frame(0x123, b'', False, now)
        detector.reset()
        assert not detector.alert_active
        assert detector.last_seen is None
        assert len(detector.candidates) == 0
