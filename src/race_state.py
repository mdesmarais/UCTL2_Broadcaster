
class RaceStatus:

    """
        Represents all available options for the status of the race
    """

    UNKNOWN = -1
    WAITING = 0
    RUNNING = 1
    FINISHED = 2


class RaceState:

    """
        Represents a state of the race contained in a race file
    """

    def __init__(self, lastState=None):
        self.lastStatus = RaceStatus.UNKNOWN
        self.teams = []
        self.segmentsNumber = 0

        self.status = RaceStatus.UNKNOWN if lastState is None else lastState.status

    def addTeam(self, team):
        """
            Adds a team to the current race state

            :param team: team to add
            :ptype team: dict
        """
        self.teams.append(team)

    def statusChanged(self):
        """
            Checks if the status of the race state have changed after read the race file

            :return: True if the race status have changed, False if not
            :rtype: bool
        """
        return not self.status == self.lastStatus

    def setStatus(self, status):
        """
            Changes the current status to another one

            If the new status is different than the last one, then the method statusChanged will return True.
        """
        self.lastStatus = self.status
        self.status = status


def computeRaceStatus(segmentsRead, totalSegments):
    """
        Computes the race status according to the number of segments read

        The number of segments in the race file is equal to the number of segments per line
        times the number of teams

        :param segmentsRead: number of segments read
        :ptype segmentsRead: int
        :param totalSegments: number of segments in the race file
        :ptype totalSegments: int
        :return: the status of the race
        :rtype: RaceStatus
    """
    if segmentsRead == 0:
        return RaceStatus.WAITING
    elif segmentsRead == totalSegments:
        return RaceStatus.FINISHED
    else:
        return RaceStatus.RUNNING