"""
    This module defines the Stage class
"""
from typing import Any, Dict


class Stage:

    def __init__(self, id: int, name: str, dst_from_start: int, length: int, is_timed: bool) -> None:
        """
            Creates a new stage

            :param id: id of the stage, should be positive and unique
            :param name: name of the stage
            :param dst_from_start: distance from start (in meters)
            :param length: length of the stage (in meters)
            :param is_timed: indicates if the stage is timed or not
        """
        if dst_from_start < 0:
            raise ValueError('Stage distance from start must be positive')

        if length < 0:
            raise ValueError('Stage length must be positive')

        self.id = id
        self.name = name
        self.dst_from_start = dst_from_start
        self.length = length
        self.is_timed = is_timed

    def serialize(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'start': self.dst_from_start,
            'length': self.length,
            'timed': self.is_timed
        }
