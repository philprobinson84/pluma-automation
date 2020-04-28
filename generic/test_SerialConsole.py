import os
import time

from generic_fixtures import serial_console_proxy
from utils import nonblocking


def test_SerialConsole_send_sends_data(serial_console_proxy):
    serial_console_proxy.console.send('Foo')

    written = serial_console_proxy.proxy.read()

    assert written


def test_SerialConsole_send_sends_correct_data(serial_console_proxy):
    msg = 'Foo'
    serial_console_proxy.console.send(msg)

    written = serial_console_proxy.proxy.read(
        encoding=serial_console_proxy.console.encoding)

    assert written == '{}{}'.format(msg, serial_console_proxy.console.linesep)


def test_SerialConsole_send_doesnt_send_newline_when_send_newline_arg_false(serial_console_proxy):
    msg = 'Foo'
    serial_console_proxy.console.send(msg, send_newline=False)

    written = serial_console_proxy.proxy.read(
        encoding=serial_console_proxy.console.encoding)

    assert written == msg


def test_SerialConsole_send_returns_tuple(serial_console_proxy):
    returned = serial_console_proxy.console.send()

    assert isinstance(returned, tuple)


def test_SerialConsole_send_returns_tuple_length_2(serial_console_proxy):
    returned = serial_console_proxy.console.send()

    assert len(returned) == 2

def test_SerialConsole_send_returns_data_when_recieve_arg_true(serial_console_proxy):
    msg = 'Bar'

    async_result = nonblocking(serial_console_proxy.console.send,
        receive=True)

    # Wait short time for function to start
    time.sleep(0.1)

    serial_console_proxy.proxy.write(msg, serial_console_proxy.console.encoding)

    received, __ = async_result.get()
    assert received == msg


def test_SerialConsole_send_returns_matched_when_match_available(serial_console_proxy):
    before_match, to_match = 'Foo', 'Bar'
    msg = before_match + to_match

    async_result = nonblocking(serial_console_proxy.console.send,
        match=to_match)

    # Wait short time for function to start
    time.sleep(0.1)

    serial_console_proxy.proxy.write(msg, serial_console_proxy.console.encoding)

    __, matched = async_result.get()
    assert matched == to_match


def test_SerialConsole_send_returns_received_when_match_available(serial_console_proxy):
    before_match, to_match = 'Foo', 'Bar'
    msg = before_match + to_match

    async_result = nonblocking(serial_console_proxy.console.send,
        match=to_match)

    # Wait short time for function to start
    time.sleep(0.1)

    serial_console_proxy.proxy.write(msg, serial_console_proxy.console.encoding)

    received, __ = async_result.get()
    assert received == before_match


def test_SerialConsole_send_returns_recieved_false_when_no_match_available(serial_console_proxy):
    msg = 'FooBar'
    wont_match = 'Baz'

    async_result = nonblocking(serial_console_proxy.console.send,
        match=wont_match)

    # Wait short time for function to start
    time.sleep(0.1)

    serial_console_proxy.proxy.write(msg, serial_console_proxy.console.encoding)

    __, matched = async_result.get()
    assert matched is False


def test_SerialConsole_send_returns_recieved_when_no_match_available(serial_console_proxy):
    msg = 'FooBar'
    wont_match = 'Baz'

    async_result = nonblocking(serial_console_proxy.console.send,
        match=wont_match)

    # Wait short time for function to start
    time.sleep(0.1)

    serial_console_proxy.proxy.write(msg, serial_console_proxy.console.encoding)

    received, __ = async_result.get()
    assert received == msg


def test_SerialConsole_send_matches_regex(serial_console_proxy):
    msg = 'Hello World! 123FooBarBaz'
    regex = '[0-3]+Foo'
    expected_match='123Foo'

    async_result = nonblocking(serial_console_proxy.console.send,
        match=regex)

    # Wait short time for function to start
    time.sleep(0.1)

    serial_console_proxy.proxy.write(msg, serial_console_proxy.console.encoding)

    __, matched = async_result.get()
    assert matched == expected_match
