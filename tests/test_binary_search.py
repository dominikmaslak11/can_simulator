import pytest
from threads.binary_search_thread import BinarySearchThread

class MockCan:
    def send_frame(self, *args, **kwargs):
        return True, "OK"

def mock_log(msg): pass
def mock_ask(): return True
def mock_done(): pass

def test_binary_thread_initial_state():
    thread = BinarySearchThread(MockCan(), mock_log, mock_ask, mock_done)
    assert thread.left == 0
    assert thread.right == 0
    assert thread.running is False

def test_binary_thread_setup():
    thread = BinarySearchThread(MockCan(), mock_log, mock_ask, mock_done)
    frames = [(0x123, b'\x01\x02', False, 0.0)] * 10
    thread.setup(frames, 0.1, mode='find_start')
    assert thread.left == 0
    assert thread.right == 9
    assert thread.mode == 'find_start'
