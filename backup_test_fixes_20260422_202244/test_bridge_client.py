import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge_client import VCanBridge

class TestVCanBridge:
    def test_filter_ids(self):
        # Tworzymy mostek z filtrem
        bridge = VCanBridge("ws://dummy", filter_ids=[0x123, 0x456])
        assert bridge._should_forward(0x123) is True
        assert bridge._should_forward(0x456) is True
        assert bridge._should_forward(0x789) is False

    def test_no_filter(self):
        bridge = VCanBridge("ws://dummy")
        assert bridge._should_forward(0x123) is True
        assert bridge._should_forward(0x999) is True

    def test_parse_filter_string(self):
        # Testujemy logikę parsowania (w BridgeTab, ale możemy sprawdzić tutaj)
        filter_str = "0x100, 0x200, 512"
        ids = []
        for x in filter_str.split(','):
            x = x.strip()
            if x.startswith('0x'):
                ids.append(int(x, 16))
            else:
                ids.append(int(x))
        assert ids == [0x100, 0x200, 512]
