import json
import os
import random
import logging

logger = logging.getLogger("RLAgent")


class RLAgent:
    """
    Prosty agent Q-learning do wyboru punktu startowego polowania.
    Stan: skwantowany indeks startowy (np. 10 przedziałów).
    Akcja: przesunięcie punktu startowego w lewo/prawo lub pozostanie.
    Nagroda: odwrotność liczby odtworzonych ramek do dezaktywacji (im mniej, tym lepiej).
    """
    def __init__(self, state_bins=10, alpha=0.1, gamma=0.9, epsilon=0.2, q_table_file="rl_q_table.json"):
        self.state_bins = state_bins
        self.alpha = alpha      # współczynnik uczenia
        self.gamma = gamma      # współczynnik dyskontowania
        self.epsilon = epsilon  # eksploracja
        self.q_table_file = q_table_file
        self.q_table = {}       # klucz: stan (int 0..state_bins-1), wartość: {akcja: wartość_q}
        self.actions = [-1, 0, 1]  # -1: zmniejsz indeks startowy, 0: bez zmian, +1: zwiększ
        self.last_state = None
        self.last_action = None
        self.load()

    def _discretize_state(self, start_index, total_frames):
        if total_frames <= 1:
            return 0
        ratio = start_index / (total_frames - 1)
        bin_idx = int(ratio * self.state_bins)
        return min(bin_idx, self.state_bins - 1)

    def choose_action(self, start_index, total_frames):
        state = self._discretize_state(start_index, total_frames)
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in self.actions}

        if random.random() < self.epsilon:
            action = random.choice(self.actions)
        else:
            # Wybierz akcję o najwyższej wartości Q
            q_values = self.q_table[state]
            max_q = max(q_values.values())
            best_actions = [a for a, q in q_values.items() if q == max_q]
            action = random.choice(best_actions)

        self.last_state = state
        self.last_action = action
        return action

    def update(self, reward, new_start_index, total_frames):
        if self.last_state is None:
            return
        new_state = self._discretize_state(new_start_index, total_frames)
        if new_state not in self.q_table:
            self.q_table[new_state] = {a: 0.0 for a in self.actions}

        old_value = self.q_table[self.last_state][self.last_action]
        next_max = max(self.q_table[new_state].values())
        new_value = old_value + self.alpha * (reward + self.gamma * next_max - old_value)
        self.q_table[self.last_state][self.last_action] = new_value

    def save(self):
        try:
            with open(self.q_table_file, 'w') as f:
                json.dump(self.q_table, f)
        except Exception as e:
            logger.error(f"Błąd zapisu Q-table: {e}")

    def load(self):
        if os.path.exists(self.q_table_file):
            try:
                with open(self.q_table_file, 'r') as f:
                    self.q_table = json.load(f)
                # Konwersja kluczy z powrotem na int (json zapisuje jako string)
                self.q_table = {int(k): {int(a): float(q) for a, q in v.items()} for k, v in self.q_table.items()}
            except Exception as e:
                logger.error(f"Błąd odczytu Q-table: {e}")
                self.q_table = {}
