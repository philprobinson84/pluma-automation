from .farmclass import Farmclass
from abc import ABCMeta, abstractmethod
from functools import wraps


class RelayBase(Farmclass, metaclass=ABCMeta):

    @abstractmethod
    def toggle(f):
        @wraps(f)
        def wrap(self, port, throw, *args, **kwargs):
            self.log('{}: Switching port {} to {}'.format(
                str(self), port, throw))
            f(self, port, throw, *args, **kwargs)
        return wrap
