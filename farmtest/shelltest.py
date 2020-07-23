import os
import re

from .test import TestBase, TaskFailed
from farmcore import HostConsole


class ShellTest(TestBase):
    shell_test_index = 0

    def __init__(self, board, script, name=None, should_print=None, should_not_print=None, run_on_host=False, timeout=None):
        super().__init__(self)
        self.board = board
        self.should_print = should_print or []
        self.should_not_print = should_not_print or []
        self.run_on_host = run_on_host
        self.timeout = timeout if timeout is not None else 5

        self.scripts = script
        if not isinstance(self.scripts, list):
            self.scripts = [self.scripts]

        if name:
            self._test_name += f'[{name}]'
        else:
            ShellTest.shell_test_index += 1
            self._test_name += f'[{ShellTest.shell_test_index}]'

        if not self.run_on_host and not self.board.console:
            raise ValueError(
                f'Cannot run script test "{self._test_name}" on target: no console'
                ' was defined. Define a console in "pluma-target.yml", or use '
                ' "run_on_host" test attribute to run on the host instead.')

    def test_body(self):
        console = None
        if self.run_on_host:
            console = HostConsole('sh')
        else:
            console = self.board.console
            if not console:
                raise TaskFailed(
                    f'Failed to run script test "{self._test_name}": no console available')

            self.board.login()

        for script in self.scripts:
            self.run_command(console, script)

    def run_command(self, console, script):
        CommandRunner.run(test_name=self._test_name, log_function=self.board.log, console=console, command=script,
                          timeout=self.timeout, should_print=self.should_print, should_not_print=self.should_not_print)


class CommandRunner():
    @staticmethod
    def run(test_name, console, command, log_function=print, timeout=None, should_print=None, should_not_print=None):
        should_print = should_print or []
        should_not_print = should_not_print or []

        received = console.send_and_read(command, timeout=timeout)
        if received.startswith(command):
            received = received[len(command):]
        received = received.strip()

        prefix = f'Script test "{test_name}":'
        if not received:
            raise TaskFailed(f'{prefix} No response available')

        formatted_received = ''
        first_line = True
        for line in received.splitlines():
            if not first_line:
                formatted_received += '            '
            formatted_received += f'{line}{os.linesep}'
            first_line = False

        sent_line = f'  Sent:     $ {command}{os.linesep}'
        should_print_line = f'  Expected: {should_print}{os.linesep}'
        should_not_print_line = f'  Errors:   {should_not_print}{os.linesep}'
        received_line = f'  Received: {formatted_received}'

        if CommandRunner.output_matches_pattern(should_not_print, received):
            raise TaskFailed(
                f'{prefix} Response matched error condition:{os.linesep}' +
                sent_line + should_not_print_line + received_line)

        if len(should_print) > 0:
            response_valid = CommandRunner.output_matches_pattern(
                should_print, received)

            if not response_valid:
                raise TaskFailed(
                    f'{prefix} Response did not match expected:{os.linesep}' +
                    sent_line + should_print_line + received_line)
            elif log_function:
                log_function(
                    f'{prefix} Matching response found:{os.linesep}' +
                    sent_line + should_print_line + received_line)
        elif log_function:
            log_function(f'{prefix}{os.linesep}' + sent_line + received_line)

        retcode_command = 'echo retcode=$?'
        retcode_received, matched = console.send_and_expect(
            retcode_command, match='retcode=0')

        if retcode_received.startswith(retcode_command):
            retcode_received = retcode_received[len(retcode_command):]

        if not matched:
            error = f'{prefix} Command "{command}" returned with a non-zero exit code{os.linesep}' + \
                sent_line + received_line + \
                f'  Return code query output: {retcode_received}'
            ansi_colors_regexp = re.compile(
                r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            error = ansi_colors_regexp.sub('', error)
            raise TaskFailed(error)

        # Be sure nothing stays in the buffer
        console.wait_for_quiet()

    @staticmethod
    def output_matches_pattern(patterns, output):
        if patterns is None:
            raise ValueError('None pattern provided')

        if not isinstance(patterns, list):
            patterns = [patterns]

        for pattern in patterns:
            regexp = re.compile(pattern)
            for line in output.splitlines():
                if regexp.match(line) is not None:
                    return True

        return False
