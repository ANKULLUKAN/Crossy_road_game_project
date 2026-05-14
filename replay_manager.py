import copy


class ReplayManager:


    def __init__(self):
        self.recorded_moves = []
        self.is_replaying = False
        self.replay_index = 0
        self.replay_tick = 0
        self.initial_state = None



    def save_initial_state(self, state: dict):

        self.initial_state = copy.deepcopy(state)



    def record_move(self, tick: int, move: str):

        if not self.is_replaying:
            self.recorded_moves.append((tick, move))



    def start_replay(self):

        self.is_replaying = True
        self.replay_index = 0
        self.replay_tick = 0

    def stop_replay(self):

        self.is_replaying = False

    def get_moves_for_current_tick(self):

        moves = []

        while self.replay_index < len(self.recorded_moves):

            move_tick, move = self.recorded_moves[self.replay_index]

            if move_tick != self.replay_tick:
                break

            moves.append(move)
            self.replay_index += 1

        return moves

    def advance_tick(self):

        self.replay_tick += 1

    def has_finished(self):
        
        return self.replay_index >= len(self.recorded_moves)