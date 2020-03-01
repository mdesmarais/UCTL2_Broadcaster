import csv
import logging

import aiohttp

import race_file
from team_state import TeamState


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
        self.stagesNumber = 0
        self.distance = 0 if lastState is None else lastState.distance
        self.teams = []

        # Sets default race status from the previous state (is there is one)
        self.status = RaceStatus.UNKNOWN if lastState is None else lastState.status

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


def readRaceState(reader, config, loopTime, lastState):
    """
        Extracts the state of the race from the given DictReader

        If a line contains invalid data, then it is skipped.

        :param reader: lines of the race file
        :ptype reader: DictReader
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype looTime: int
        :param lastState: last state of the race, could be None
        :ptype lastState: RaceState
        :return: the current state of the race
        :rtype: RaceState
    """
    logger = logging.getLogger(__name__)

    raceState = RaceState(lastState)

    totalStagesNumber = 0
    stagesRead = 0

    raceStarted = True
    raceFinished = True

    for index, record in enumerate(reader):
        if lastState is None:
            totalStagesNumber = race_file.computeCheckpointsNumber(record)
            raceState.distance = race_file.getFloat(record, race_file.DISTANCE_FORMAT)

            if raceState.distance is None:
                logger.error('Could not get race length')

        raceState.stagesNumber = totalStagesNumber - 1

        teamStarted = not record[race_file.START_FORMAT] == race_file.EMPTY_VALUE_FORMAT
        teamFinished = not record[race_file.FINISH_FORMAT] == race_file.EMPTY_VALUE_FORMAT

        if raceStarted and not teamStarted:
            raceStarted = False
        
        if raceFinished and not teamFinished:
            raceFinished = False

        bibNumber = race_file.getInt(record, race_file.BIB_NUMBER_FORMAT)
        if bibNumber is None:
            logger.error('Bib number error')
            continue
        
        intermediateTimes = race_file.readIntermediateTimes(record)
        splitTimes = race_file.readSplitTimes(record)
        stagesRead += len(splitTimes)
        currentStage = -1

        stepDistance = 0

        if len(splitTimes) > 0:
            currentStage = len(splitTimes) - 1

            stageDistanceFromStart = config['stages'][currentStage]['start']

            if stageDistanceFromStart is None:
                logger.error('Could not compute checkpoint distance from start (id=%d) for team %d', currentStage, bibNumber)
                continue

            # Computing some estimations : covered distance since the last loop (step distance)
            if  stageDistanceFromStart > 0:
                if intermediateTimes[currentStage] > 0:
                    averageSpeed = stageDistanceFromStart / intermediateTimes[currentStage]
                stepDistance = averageSpeed * loopTime * config['tickStep']
        else:
            # Default pace when we don't known each team's pace yet
            stepDistance = 2.5 * loopTime * config['tickStep']

        try:
            if lastState is not None:
                lastTeamState = lastState.teams[index]
            else:
                lastTeamState = None
        except ValueError:
            lastTeamState = None

        # Creates a new team state for each team in the file
        # The name of the team if set if the column TEAM_NAME_FORMAT
        teamState = TeamState(bibNumber, record[race_file.TEAM_NAME_FORMAT], lastTeamState)
        teamState.currentStage = currentStage if not teamFinished else raceState.stagesNumber
        teamState.intermediateTimes = intermediateTimes
        teamState.splitTimes = splitTimes

        if teamFinished or teamState.currentStageChanged:
            teamState.coveredDistance = stageDistanceFromStart + config['stages'][currentStage]['length']
        else:
            teamState.coveredDistance += stepDistance

        raceState.teams.append(teamState)

    # Updating the status of the race for the current state
    if raceFinished:
        raceState.setStatus(RaceStatus.FINISHED)
    elif raceStarted:
        raceState.setStatus(RaceStatus.RUNNING)
    else:
        raceState.setStatus(RaceStatus.WAITING)
    return raceState


def readRaceStateFromFile(filePath, config, loopTime, lastState):
    """
        Extracts the current state of the race from the given race file

        A race file is a csv file where values are separated by a tabulation (\t).
        If the given file can not be read then None is returned.
        If a line contains invalid data, then it is skipped.

        :param filePath: path to the file that contains race data
        :ptype filePath: str
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype loopTime: int
        :param lastState: last state of the race, could be None
        :ptype lastState: RaceState
        :return: a state contained in the race file
        :rtype: RaceState
    """
    logger = logging.getLogger(__name__)

    raceState = None

    try:
        with open(config['raceFile'], 'r', encoding=config['encoding']) as raceFile:
            reader = csv.DictReader(raceFile, delimiter='\t')
            raceState = readRaceState(reader, config, loopTime, lastState)
    except IOError as e:
        logger.error('IOError : %s', e)
    
    return raceState

async def readRaceStateFromUrl(filePath, config, loopTime, lastState, session, url):
    """
        Extracts the current state of the race from the given race file

        A race file is a csv file where values are separated by a tabulation (\t).
        If the given file can not be read then None is returned.
        If a line contains invalid data, then it is skipped.

        :param filePath: path to the file that contains race data
        :ptype filePath: str
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype loopTime: int
        :param lastState: last state of the race, could be None
        :ptype lastState: RaceState
        :param session: async http session
        :ptype session: aiohttp.ClientSession
        :param url: url of the race file
        :ptype url: str
        :return: a state contained in the race file
        :rtype: RaceState
    """
    logger = logging.getLogger(__name__)

    raceState = None

    try:
        async with session.get(url) as r:
            content = await r.text(encoding=config['encoding'])
            print('file downloaded')
        reader = csv.DictReader(content.split('\n'), delimiter='\t')

        raceState = readRaceState(reader, config, loopTime, lastState)
    except IOError as e:
        logger.error('IOError : %s', e)
    except aiohttp.client_exceptions.ServerDisconnectedError:
        return await readRaceStateFromUrl(filePath, config, loopTime, lastState, session, url)
    
    return raceState
