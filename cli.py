#!/usr/bin/env python3
import argparse
import sys
from parsers import load_frames_from_file
from dummy_interface import DummyInterface
from threads import BinarySearchThread

def ask_callback_cli(prompt="Czy zjawisko wystąpiło?"):
    while True:
        ans = input(f"{prompt} (t/n): ").strip().lower()
        if ans in ('t', 'tak', 'yes', 'y'):
            return True
        elif ans in ('n', 'nie', 'no'):
            return False
        print("Nieprawidłowa odpowiedź. Wpisz t/n.")

def main():
    parser = argparse.ArgumentParser(description="CAN Simulator CLI – wyszukiwanie binarne")
    parser.add_argument("--file", required=True, help="Ścieżka do pliku z logiem CAN")
    parser.add_argument("--interval", type=float, default=0.1, help="Interwał odtwarzania [s]")
    parser.add_argument("--mode", choices=["find_start", "find_end"], default="find_start")
    args = parser.parse_args()

    frames = load_frames_from_file(args.file)
    if not frames:
        print("Plik jest pusty lub nie zawiera ramek.")
        sys.exit(1)

    can = DummyInterface()
    can.connect()

    done_event = threading.Event()

    def done_callback():
        done_event.set()

    thread = BinarySearchThread(can, print, ask_callback_cli, done_callback)
    thread.setup(frames, args.interval, mode=args.mode)
    thread.start()
    thread.join()

    can.disconnect()

if __name__ == "__main__":
    import threading
    main()
