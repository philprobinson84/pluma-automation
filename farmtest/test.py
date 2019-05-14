'''
class ExampleTest():
    def __init__(self, board):
        self.board = board

    # Any of the below tasks will be called at the correct time,
    # if they are implimented (All are optional)

    def __init__(self, board):
        self.board = board

    def prepare(self):
        pass

    def pre_board_on(self):
        pass

    def pre_board_mount(self):
        pass

    def pre_test_body(self):
        pass

    def test_body(self):
        pass

    def post_test_body(self):
        pass

    def post_board_off(self):
        pass

    def report(self):
        pass
'''

import sys
import traceback
import platform
import datetime
import time
from copy import copy

from farmutils import Email, send_exception_email
from farmcore.exceptions import BoardBootValidationError, ConsoleLoginFailed


class TestingException(Exception):
    pass


class TaskFailed(TestingException):
    pass


class AbortTesting(TestingException):
    pass


class AbortTestingAndReport(AbortTesting):
    pass


class TestBase():
    data = {}

    def __init__(self, board):
        self.board = board

    def __repr__(self):
        return self.__class__.__name__

class BootTestBase(TestBase):
    boot_success = None

class TestCore(TestBase):
    tasks = [
        'pre_host_mount', '_host_mount', 'prepare', '_host_unmount',
        'pre_board_on', '_board_on_and_validate',
        'pre_board_login', '_board_login',
        'pre_board_mount', '_board_mount',
        'pre_test_body', 'test_body', 'post_test_body'
        '_board_unmount',
        '_board_off', 'post_board_off',
        '_host_mount', 'report'
    ]

    def pre_host_mount(self):
        self.board.log("\n=== PRE HOST MOUNT ===", colour='blue', bold=True)

    def _host_mount(self):
        self.board.log("\n=!= HOST MOUNT =!=", bold=True)
        self.board.storage.to_host()

        devnode = None
        for _ in range(1, 5):
            if not self.board.hub.get_part():
                time.sleep(1)
            else:
                devnode = self.board.hub.get_part('devnode')
                break
        if not devnode:
            raise TaskFailed('Cannot mount: No block device partition downstream of hub')

        self.board.storage.mount_host(devnode)

    def prepare(self):
        self.board.log("\n=== PREPARE ===", colour='blue', bold=True)

    def _host_unmount(self):
        self.board.log("\n=!= HOST UNMOUNT =!=", bold=True)

        #TODO: Move this functionality to the board class
        devnode = None
        for _ in range(1, 5):
            if not self.board.hub.get_part():
                time.sleep(1)
            else:
                devnode = self.board.hub.get_part('devnode')
                break
        if devnode:
            self.board.storage.unmount_host(devnode)
        else:
            self.board.log("Cannot find block device partition. Continuing anyway")

        self.board.storage.to_board()

    def pre_board_on(self):
        self.board.log("\n=== PRE BOARD ON ===", colour='blue', bold=True)

    def _board_on_and_validate(self):
        self.board.log("\n=!= BOARD ON AND VALIDATE =!=", bold=True)
        try:
            self.board.reboot_and_validate()
        except BoardBootValidationError as e:
            raise e

    def pre_board_login(self):
        self.board.log("\n=== PRE BOARD LOGIN ===", colour='blue', bold=True)

    def _board_login(self):
        self.board.log("\n=!= BOARD LOGIN =!=", bold=True)
        try:
            self.board.login()
        except ConsoleLoginFailed as e:
            raise TaskFailed(str(e))

    def pre_board_mount(self):
        self.board.log("\n=== PRE BOARD MOUNT ===", colour='blue', bold=True)

    def _board_mount(self):
        self.board.log("\n=!= BOARD MOUNT =!=", bold=True)
        self.board.storage.to_board()
        self.board.storage.mount_board()

    def pre_test_body(self):
        self.board.log("\n=== PRE TEST BODY ===", colour='blue', bold=True)

    def test_body(self):
        self.board.log("\n=== TEST BODY ===", colour='blue', bold=True)

    def post_test_body(self):
        self.board.log("\n=== POST TEST BODY ===", colour='blue', bold=True)

    def _board_unmount(self):
        self.board.log("\n=!= BOARD UNMOUNT =!=", bold=True)
        self.board.storage.unmount_board()

    def _board_off(self):
        self.board.log("\n=!= BOARD OFF =!=", bold=True)
        self.board.power.off()

    def post_board_off(self):
        self.board.log("\n=== POST BOARD OFF ===", colour='blue', bold=True)

    def report(self):
        self.board.log("\n=== REPORT ===", colour='blue', bold=True)


class TestRunner():
    def __init__(self, board, tests=None, boot_test=None,
            skip_tasks=None, email_on_fail=True, use_testcore=True):
        self.board = board
        self.email_on_fail = email_on_fail
        self.skip_tasks = skip_tasks or []
        self.tests = []
        if boot_test and not isinstance(boot_test, BootTestBase):
            raise AttributeError('Invalid boot test. Must inherit BootTestBase')
        self.boot_test = boot_test

        self.test_fails = []
        tests = tests or []
        if not isinstance(tests, list):
            tests = [tests]

        self.tasks = TestCore.tasks
        self.use_testcore = use_testcore

        # General purpose data for use globally between tests
        self.data = {}

        if self.boot_test:
            self.add_test(self.boot_test)

        for test in tests:
            self.add_test(test)

    def __call__(self):
        return self.run()

    def __repr__(self):
        return f'[{self.__class__.__name__}]'

    @property
    def num_tests(self):
        return len(self.tests)

    def _init_test_data(self, test):
        test.data = {}
        self.data[str(test)] = {
            'tasks': {
                'ran': [],
                'failed': []
            },
            'data': test.data,
            'order': self.tests.index(test)
        }

    def run(self):
        self.test_fails = []

        # Init data
        self.data = {}

        for test in self.tests:
            self._init_test_data(test)

        if (self.use_testcore and "TestCore" not in
                (str(t) for t in self.tests)):
            self.add_test(TestCore(self.board), 0)

        self.board.log("Running tests: {}".format(
            list(map(lambda t: t.__class__.__name__, self.tests))))

        try:
            for task in self.tasks:
                self._run_task(task)
            self.board.log("\n== ALL TESTS COMPLETED ==", colour='blue', bold=True)
        except AbortTesting as e:
            self.board.log("\n== TESTING ABORTED EARLY ==", colour='red', bold=True)

        # Check if any tasks failed
        if self.test_fails:
            return False
        else:
            return True

    def add_test(self, test, index=None):
        if self._get_tests_by_name(str(test)):
            self.board.error(f'Test [{str(test)}] already added', RuntimeError)

        if index is None:
            self.board.log("Appending test: {}".format(str(test)))
            self.tests.append(test)
        else:
            self.board.log("Inserting test at position {}: {} ".format(
                index, str(test)))
            self.tests.insert(index, test)

        self._init_test_data(test)

    def rm_test(self, test):
        if test in self.tests:
            self.board.log("Removed test: {}".format(str(test)))
            self.tests.remove(test)

    def _get_tests_by_name(self, test_name):
        tests = [t for t in self.tests if str(t) == test_name]
        return None if not tests else tests

    def _run_task(self, task_name, test_name=None):
        if "mount" in task_name and not self.board.storage:
            self.board.log("Board does not have storage. Skipping task: {}".format(task_name))
            return
        if task_name in self.skip_tasks:
            self.board.log("Skipping task: {}".format(task_name),
                colour='green', bold=True)
            return

        # Run all task for all tests unless one is specified
        if test_name:
            tests_to_run = self._get_tests_by_name(test_name)
            if not tests_to_run:
                self.board.error(
                    'Cannot run specified test {} as it is not in test list. Running all'.format(
                    test_name))
                tests_to_run = self.tests
            self.board.log('Running {} for test [{}] only'.format(
                task_name, test_name))
        else:
            tests_to_run = self.tests

        for test in tests_to_run:
            if (task_name == "_board_on_and_validate" and
                self.boot_test):
                # Initialise boot test result to success
                self.boot_test.boot_success = True
            task_func = getattr(test, task_name, None)
            if task_func:
                self.data[str(test)]['tasks']['ran'].append(task_name)

                if test.__class__ != TestCore:
                    self.board.log("Running: {} - {}".format(
                        str(test), task_name), colour='green')
                try:
                    task_func()
                # If exception is one we deliberately caused, don't handle it
                except KeyboardInterrupt as e:
                    raise e
                except InterruptedError as e:
                    raise e
                except Exception as e:
                    self.data[str(test)]['tasks']['failed'].append(task_name)

                    # If request to abort testing, do so
                    if isinstance(e, AbortTesting):
                        self.board.log('Testing aborted by task {} - {}: {}'.format(
                            str(test), task_name, str(e)))
                        if (isinstance(e, AbortTestingAndReport) and
                                'report' in self.tasks):
                            self._run_task('report')
                        raise e
                    # If failed boot, and we have a specific boot test,
                    #   run it's report function
                    if (isinstance(e, BoardBootValidationError) and
                            self.boot_test):
                            self.board.log('Boot test failed, running {}.report()'.format(
                                str(self.boot_test)))

                            self.boot_test.boot_success = False
                            self._run_task('report', str(self.boot_test))
                            self._handle_failed_task(test, task_name, e)
                    # For all other exceptions, we want to know about it
                    else:
                        self._handle_failed_task(test, task_name, e)

    def _handle_failed_task(self, test, task_name, exception, abort=True):
        failed = {
            'time': time.time(),
            'test': test,
            'task': task_name,
            'exception': exception,
            'traceback': traceback.format_exc()
        }
        self.test_fails.append(failed)

        if self.email_on_fail:
            self.send_fail_email(exception, test, task_name)

        self.board.log('Task failed {}'.format(failed),
            colour='red', bold=True)

        if abort:
            raise AbortTesting(str(exception))

    # # TODO: Impliment function
    # def add_test_data(self, test:TestBase, data:dict):
    #     '''
    #     - Add data to global data struct
    #     - This method would handle creating copies of the data
    #         so that the Test did not have to
    #     - It will add a reference iteration number to the data
    #     - If there is no test data for this Test on this iteration,
    #         it will append an empty dict to the data list for that test
    #     - It will add the data to the dict for that Test on that iteration
    #     - It will save all Test data for that iteration in its own data dict,
    #         in a section per iteration, with subsections for each test
    #     '''
    #     raise NotImplementedError

    #     # Type check input
    #     assert isinstance(test, TestBase)
    #     assert isinstance(data, dict)


    # # TODO: Impliment function
    # def get_test_data(self, test:TestBase, iteration:int=None, json:bool=False):
    #     '''
    #     - Return a dict of all of the test data for that test only,
    #         with a reference to what iteration the data relates to
    #     - Optional @json parameter to signal that the data returned should be
    #         a json formatted string, not a dict
    #     - Optional @iteration parameter to signal that only data for that
    #         @test on that iteration should be returned
    #     '''
    #     raise NotImplementedError

    #     assert isinstance(test, TestBase)
    #     assert isinstance(data, dict)

    # # TODO: Impliment function
    # def write_test_data(self, file:str, test:TestBase=None, iteration:int=None)
    #     '''
    #     - Write a json formatted string to a file, with
    #         path @file, containing the global test data
    #     - If the path to that file does not exist, create it
    #     - Optional @test parameter to signal that
    #         only the data for that test should be written
    #     - Optional @iteration parameter to signal that only
    #         data for that iteration should be written
    #     '''
    #     raise NotImplementedError

    def send_fail_email(self, exception, test_failed, task_failed):
        #TODO: Move to a config file
        lab_maintainers = ['mwebster@witekio.com']

        subject = 'TestRunner Exception Occured: [{}: {}] [{}]'.format(
            str(test_failed), task_failed, self.board.name)
        body = '''
        <b>Tests:</b> {}<br>
        <b>Test Failed:</b> {}<br>
        <b>Task Failed:</b> {}
        '''.format(
            [str(t) for t in self.tests],
            str(test_failed),
            task_failed)

        send_exception_email(
            exception=exception,
            recipients=lab_maintainers,
            board=self.board,
            subject=subject,
            prepend_body=body
        )