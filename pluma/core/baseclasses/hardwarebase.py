from .hierarchy import Hierarchy
from .logging import Logging


class HardwareBase(Hierarchy, Logging):
    """ Contains functionality common to all pluma objects """

    def __repr__(self):
        return f'[{self.__class__.__name__}]'
