"""Keyboard/display checks run inside the existing disposable PCE harness."""
import time


def check(send, screen):
    def key(name):
        send('key ' + name + '\nc 20000')

    def text(value):
        for char in value:
            key('Semicolon' if char == ';' else char)

    def current(expected):
        deadline = time.monotonic() + 15
        last = ''
        while time.monotonic() < deadline:
            last = screen()
            lines = [line.rstrip() for line in last.splitlines()[:24] if line.strip()]
            # A long input can wrap across rows; exclude earlier accepted lines.
            combined = ''.join(lines)
            if (combined.endswith('A>' + expected)
                    or expected and lines and lines[-1].lstrip() == expected):
                return
        raise AssertionError((expected, last))

    text(';ac')
    key('Left')
    text('b')
    current(';abc')
    key('Home')
    key('Right')
    key('Delete')
    current(';bc')
    key('End')
    text('d')
    current(';bcd')
    key('Return')
    current('')
    key('Up')
    current(';bcd')
    key('+Ctrl u -Ctrl')
    key('Up')
    current(';bcd')
    key('+Ctrl u -Ctrl')
    key('Return')
    current('')
    text(';' + 'a'*90)
    current(';' + 'a'*90)
    key('Home')
    key('Right')
    text('b')
    current(';b' + 'a'*90)
    key('End')
    key('Backspace')
    current(';b' + 'a'*89)
    key('+Ctrl u -Ctrl')
    key('Return')
    current('')
    print('PASS: live arrows, Home/End, Delete, recall, cancellation and wrapped redraw', flush=True)
