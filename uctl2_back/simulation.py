"""
    This module defines the Simulation class
"""
import datetime
import time
from typing import TYPE_CHECKING, Any, Callable, List, Set, Tuple

from uctl2_back.race_file import process_file

if TYPE_CHECKING:
    from uctl2_back.simulator import Simulator

# Type aliases
StagesWithInts = List[Tuple[Set[int], Set[int]]]


class Simulation:

    """
        Represents a Simulation

        A simulation is run by a simulator with pre computed times
    """

    def __init__(self, simulator: 'Simulator', tick_step: int) -> None:
        """
            Creates a new Simulation instance

            The tick_step parameter must be strictely positive.

            :param simulator: instance of the simulator that will run the simulation
            :param tick_step: speed of the simulation
            :raises ValueError: if tick_step is negative
        """
        if tick_step <= 0:
            raise ValueError('tick step must be strictely positive')

        self.simulator = simulator
        self.tick_step = tick_step

        self.stages_with_times: StagesWithInts = [(set(), set()) for stage in simulator.race_stages if stage.is_timed]
        self.race_time = simulator.start_time
        self.remaining_teams = list(simulator.race_teams)
        self.running = False

    def run(self, on_file_updated: Callable[[List[Any]], Any] = None, on_race_finished=Callable[[], Any]) -> None:
        """
            Runs the simulation

            :param on_file_updated: callback to a function to call when the file is updated
            :param on_race_finished: callback to a function to call when the race is over
        """
        last_call = time.time()
        self.running = True

        while self.running:
            current_time = time.time()
            loop_time = current_time - last_call
            last_call = current_time

            self.race_time += datetime.timedelta(seconds=self.tick_step * loop_time)

            stage_time_index = 0
            for i, stage in enumerate(self.simulator.race_stages):
                if not stage.is_timed:
                    continue

                stage_times = self.stages_with_times[stage_time_index]
                stage_time_index += 1

                for j, team in enumerate(self.remaining_teams):
                    if i == 0 or self.simulator.stages_inter_times[i - 1][j] <= self.race_time:
                        stage_times[0].add(team['bibNumber'])

                    if self.simulator.stages_inter_times[i][j] <= self.race_time:
                        stage_times[1].add(team['bibNumber'])

                        if stage_time_index == len(self.stages_with_times):
                            self.remaining_teams.pop(j)

            rows = process_file(self.simulator, self.stages_with_times)
            if not on_file_updated is None:
                on_file_updated(rows)

            if len(self.remaining_teams) == 0:
                self.running = False
                self.simulator.reset_simulation()

                if not on_race_finished is None:
                    on_race_finished()
                break

            self.simulator.socketio.sleep(1)
