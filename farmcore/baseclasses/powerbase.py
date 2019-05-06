from .farmclass import Farmclass
import time


class PowerBase(Farmclass):
    reboot_delay = 0.5

    def on(self):
        raise NotImplemented('This method must be implimented by inheriting class')

    def off(self):
        raise NotImplemented('This method must be implimented by inheriting class')

    def reboot(self):
        self.off()
        time.sleep(self.reboot_delay)
        self.on()

    def __bool__(self):
        ''' Base class is falsey. Must inherit'''
        return True if type(self) is not PowerBase else False