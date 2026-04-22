import pytest
import time
import threading
import socket
import struct
from can_interface import CanInterface

# Sprawdzenie, czy vcan jest dostępny
def vcan_available():
    try:
        s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
        s.bind(('vcan0',))
        s.close()
        return True
    except:
        return False

@pytest.mark.integration
class TestVirtualCANIntegration:
    @pytest.fixture(autouse=True)
    def setup_vcan(self):
        # Zakładamy, że vcan0 jest już skonfigurowane
        self.interface = 'vcan0'
        self.can = CanInterface(self.interface)
        if not vcan_available():
            pytest.skip("vcan0 nie jest dostępne")

    def test_can_send_and_receive(self):
        self.can.connect()
        received = []
        def recv_loop():
            while len(received) < 1:
                try:
                    data = self.can.sock.recv(16)
                    if data:
                        flags, dlc, _, payload = struct.unpack("<IB3s8s", data)
                        can_id = flags & 0x1FFFFFFF
                        received.append((can_id, payload[:dlc]))
                except socket.timeout:
                    continue
        threading.Thread(target=recv_loop, daemon=True).start()
        time.sleep(0.1)
        self.can.send_frame(0x123, b'\x01\x02\x03')
        time.sleep(0.5)
        assert len(received) >= 1
        assert received[0][0] == 0x123
        assert received[0][1] == b'\x01\x02\x03'
        self.can.disconnect()

    def test_cyclic_detector_with_vcan(self):
        from cyclic_detector import CyclicDetector
        self.can.connect()
        detector = CyclicDetector()
        detector.start_monitoring(0x123, 0.1)
        for i in range(5):
            self.can.send_frame(0x123, bytes([i]))
            time.sleep(0.1)
        assert detector.is_cyclic(0x123)
        self.can.disconnect()

    def test_replay_with_vcan(self):
        from threads.simulation_thread import SimulationThread
        self.can.connect()
        frames = [
            (0x100, b'\x01', False, 0.0),
            (0x101, b'\x02', False, 0.1),
            (0x102, b'\x03', False, 0.2)
        ]
        received = []
        def recv_loop():
            while self.can.connected:
                try:
                    data = self.can.sock.recv(16)
                    if data:
                        flags, dlc, _, payload = struct.unpack("<IB3s8s", data)
                        can_id = flags & 0x1FFFFFFF
                        received.append((can_id, payload[:dlc]))
                except socket.timeout:
                    continue
        recv_thread = threading.Thread(target=recv_loop, daemon=True)
        recv_thread.start()
        def log_cb(msg): pass
        thread = SimulationThread(self.can, log_cb)
        thread.setup_replay(frames, 0.05, loop=False)
        thread.start()
        thread.join(timeout=2.0)
        time.sleep(0.5)
        assert len(received) >= 3
        self.can.disconnect()
