import pytest
import subprocess
import time
import threading
import socket
import struct
import os

AF_CAN = 29
PF_CAN = AF_CAN
CAN_RAW = 1


def build_can_frame(can_id, data, is_extended=False):
    flags = can_id
    if is_extended:
        flags |= 0x80000000
    data = bytes(data[:8]).ljust(8, b'\x00')
    return struct.pack("<IB3s8s", flags, len(data), b'\x00'*3, data)


class VirtualCAN:
    """Kontekst do tworzenia i usuwania wirtualnego interfejsu CAN."""
    def __init__(self, iface='vcan0'):
        self.iface = iface

    def __enter__(self):
        subprocess.run(['sudo', 'ip', 'link', 'add', 'dev', self.iface, 'type', 'vcan'], check=True)
        subprocess.run(['sudo', 'ip', 'link', 'set', 'up', self.iface], check=True)
        time.sleep(0.1)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        subprocess.run(['sudo', 'ip', 'link', 'delete', self.iface], check=False)


@pytest.mark.integration
class TestVirtualCANIntegration:
    """Testy integracyjne wykorzystujące wirtualny CAN."""

    def test_can_send_and_receive(self):
        """Test podstawowego wysyłania i odbierania ramek przez vcan."""
        with VirtualCAN('vcan0'):
            rx_sock = socket.socket(PF_CAN, socket.SOCK_RAW, CAN_RAW)
            rx_sock.bind(('vcan0',))

            tx_sock = socket.socket(PF_CAN, socket.SOCK_RAW, CAN_RAW)
            tx_sock.bind(('vcan0',))

            received = []
            def receiver():
                while len(received) < 1:
                    frame = rx_sock.recv(16)
                    received.append(frame)

            recv_thread = threading.Thread(target=receiver)
            recv_thread.start()

            frame = build_can_frame(0x123, b'\x01\x02\x03', False)
            tx_sock.send(frame)
            recv_thread.join(timeout=1.0)

            assert len(received) == 1

            tx_sock.close()
            rx_sock.close()

    def test_cyclic_detector_with_vcan(self):
        """Test wykrywania cykliczności z wykorzystaniem vcan."""
        from cyclic_detector import CyclicDetector

        with VirtualCAN('vcan0'):
            tx_sock = socket.socket(PF_CAN, socket.SOCK_RAW, CAN_RAW)
            tx_sock.bind(('vcan0',))

            detector = CyclicDetector(alert_id=0x123, expected_period=0.2, tolerance=0.1)

            # Wyślij pierwszą ramkę
            frame = build_can_frame(0x123, b'\x01', False)
            tx_sock.send(frame)
            detector.feed_frame(0x123, b'\x01', False, time.time())

            # Wyślij drugą ramkę w oczekiwanym oknie
            time.sleep(0.2)
            tx_sock.send(frame)
            detector.feed_frame(0x123, b'\x01', False, time.time())
            assert detector.alert_active

            # Poczekaj dłużej niż okres + tolerancja
            time.sleep(0.35)
            # Wyślij inną ramkę, powinna wywołać dezaktywację
            tx_sock.send(build_can_frame(0x456, b'\x02', False))
            deactivated = detector.feed_frame(0x456, b'\x02', False, time.time())
            assert deactivated
            assert not detector.alert_active

            tx_sock.close()

    def test_replay_with_vcan(self):
        """Test odtwarzania ramek przez wirtualny CAN."""
        from threads.simulation_thread import SimulationThread
        from dummy_interface import DummyInterface

        with VirtualCAN('vcan0'):
            # Użyjemy prawdziwego SocketCAN, aby zweryfikować odtwarzanie
            from socketcan_interface import SocketCANInterface
            can = SocketCANInterface('vcan0')
            can.connect()

            # Odbiornik
            rx_sock = socket.socket(PF_CAN, socket.SOCK_RAW, CAN_RAW)
            rx_sock.bind(('vcan0',))
            received = []

            def receiver():
                start = time.time()
                while time.time() - start < 2.0:
                    try:
                        rx_sock.settimeout(0.5)
                        frame = rx_sock.recv(16)
                        received.append(frame)
                    except socket.timeout:
                        pass

            recv_thread = threading.Thread(target=receiver)
            recv_thread.start()

            # Ramki do odtworzenia
            frames = [
                (0x100, b'\x01\x02', False),
                (0x200, b'\x03\x04', True),
                (0x300, b'\x05\x06', False),
            ]

            log = []
            thread = SimulationThread(can, log.append)
            thread.setup_replay(frames, fixed_interval=0.1, loop=False)
            thread.start()
            thread.join(timeout=2.0)

            recv_thread.join(timeout=2.5)

            # Powinny zostać odebrane 3 ramki
            assert len(received) >= 3

            can.disconnect()
            rx_sock.close()
