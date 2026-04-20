#!/usr/bin/env python3
"""
CAN Simulator CLI – wyszukiwanie binarne z linii poleceń.
Użycie: python cli.py --file log.txt --mode find_start --interval 0.1
"""

import argparse
import sys
import threading
from parsers import load_frames_from_file
from dummy_interface import DummyInterface
from threads import BinarySearchThread


def ask_callback_cli(prompt="Czy zjawisko wystąpiło?"):
    """Callback zadający pytanie użytkownikowi w konsoli."""
    while True:
        ans = input(f"{prompt} (t/n): ").strip().lower()
        if ans in ('t', 'tak', 'yes', 'y'):
            return True
        elif ans in ('n', 'nie', 'no'):
            return False
        print("Nieprawidłowa odpowiedź. Wpisz t/n.")


def log_callback(msg):
    """Wypisuje log na stdout."""
    print(msg)


def main():
    parser = argparse.ArgumentParser(
        description="Wyszukiwanie binarne ramki odpowiedzialnej za zjawisko na magistrali CAN (tryb CLI)."
    )
    parser.add_argument("--file", required=True, help="Ścieżka do pliku z logiem CAN")
    parser.add_argument("--interval", type=float, default=0.1, help="Interwał odtwarzania [s]")
    parser.add_argument("--mode", choices=["find_start", "find_end"], default="find_start",
                        help="Tryb: początek lub koniec zjawiska")
    parser.add_argument("--start", type=int, default=0, help="Indeks początkowej ramki (domyślnie 0)")
    parser.add_argument("--end", type=int, help="Indeks końcowej ramki (domyślnie ostatnia)")
    args = parser.parse_args()

    print(f"Wczytywanie pliku: {args.file}")
    frames = load_frames_from_file(args.file)
    if not frames:
        print("Plik jest pusty lub nie zawiera poprawnych ramek CAN.")
        sys.exit(1)
    print(f"Wczytano {len(frames)} ramek.")

    if args.end is None:
        args.end = len(frames) - 1
    if args.start < 0 or args.start >= len(frames):
        print(f"Nieprawidłowy indeks startowy. Dozwolony zakres: 0..{len(frames)-1}")
        sys.exit(1)
    if args.end < args.start or args.end >= len(frames):
        print(f"Nieprawidłowy indeks końcowy. Dozwolony zakres: {args.start}..{len(frames)-1}")
        sys.exit(1)

    print(f"Tryb: {args.mode}, interwał: {args.interval} s, zakres: [{args.start}..{args.end}]")

    # Interfejs offline – CLI nie wymaga fizycznego CAN
    can = DummyInterface()
    can.connect()

    done_event = threading.Event()

    def done_callback():
        done_event.set()

    thread = BinarySearchThread(can, log_callback, ask_callback_cli, done_callback)
    thread.setup(frames, args.interval, mode=args.mode, left=args.start, right=args.end)
    thread.start()
    thread.join()

    can.disconnect()
    print("\nZakończono.")


if __name__ == "__main__":
    main()
