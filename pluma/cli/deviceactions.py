import time
from enum import Enum

from pluma.core.baseclasses import Logger
from pluma import Board
from pluma.test import TaskFailed
from pluma.cli import DeviceActionBase, DeviceActionRegistry

log = Logger()


@DeviceActionRegistry.register()
class PowerOnAction(DeviceActionBase):
    def execute(self):
        self.board.power.on()


@DeviceActionRegistry.register()
class PowerOffAction(DeviceActionBase):
    def execute(self):
        self.board.power.off()


@DeviceActionRegistry.register()
class PowerCycleAction(DeviceActionBase):
    def execute(self):
        self.board.power.off()
        time.sleep(1)
        self.board.power.on()


@DeviceActionRegistry.register()
class LoginAction(DeviceActionBase):
    def execute(self):
        self.board.login()


@DeviceActionRegistry.register()
class WaitAction(DeviceActionBase):
    def __init__(self, board: Board, duration: int):
        super().__init__(board)
        self.duration = duration

        if self.duration < 0:
            DeviceActionBase.parsing_error(self.__class__,
                                           'Wait duration must be a positive number, but got "{self.duration}" instead.')

    def validate(self):
        return self.duration >= 0

    def execute(self):
        time.sleep(self.duration)


@DeviceActionRegistry.register()
class WaitForPatternAction(DeviceActionBase):
    def __init__(self, board: Board, pattern: str, timeout: int = None):
        super().__init__(board)
        self.pattern = pattern
        self.timeout = timeout if timeout else 15

    def execute(self):
        self.board.console.read_all()
        matched_output = self.board.console.wait_for_match(match=self.pattern,
                                                           timeout=self.timeout)
        if not matched_output:
            raise TaskFailed(
                f'{str(self)}: Timeout reached while waiting for pattern "{self.pattern}"')


@DeviceActionRegistry.register()
class SetAction(DeviceActionBase):
    def __init__(self, board: Board, device_console: str = None):
        super().__init__(board)

        self.device_console = device_console

        if self.device_console and not self.board.get_console(self.device_console):
            raise ValueError(f'Cannot set console to "{self.device_console}": '
                             'no such console was set for this board')

    def execute(self):
        if self.device_console:
            log.log(f'Setting device console to {self.device_console}')
            self.board.console = self.board.get_console(self.device_console)
