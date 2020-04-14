"""A simple ncurses chat user interface."""

import argparse
import curses
import math

import client as client_lib
import constants


_LEFT_PANE_PERCENT  = .7
_INPUT_HEIGHT_PERCENT = .2


class Window:
    def __init__(self, scr):
        self._scr = scr
        self._height, self._width = scr.getmaxyx()
        self._data = []
        self._needs_redraw = True

    @property
    def data(self):
        return self._data.copy()

    @data.setter
    def data(self, data):
        self._data = data
        self._needs_redraw = True

    def draw(self):
        if self._needs_redraw:
            self.redraw()
            self._scr.noutrefresh()
            self._needs_redraw = False

    def redraw(self):
        """Must be implemented by the subclass."""
        raise NotImplementedError()


class ChatsWindow(Window):

    def redraw(self):
        self._scr.erase()
        self._scr.border(' ', 0, 0, 0, curses.ACS_HLINE, 0, curses.ACS_HLINE, 0)
        self._scr.addstr(0, 1, 'Chats')
        right_align = len(str(len(self._data)))
        for i, chat in enumerate(self._data):
            chat_name = chat['chat_name']
            text = f'{i + 1:>{right_align}}. {chat_name}'
            self._scr.addstr(i + 1, 0, text)


class MessagesWindow(Window):

    def redraw(self):
        self._scr.erase()
        self._scr.border(0, 0, 0, 0, 
                         0, curses.ACS_TTEE, curses.ACS_LTEE, curses.ACS_RTEE)

        # TODO(eugenhotaj): Use the actual chat name here.
        self._scr.addstr(0, 2, 'Chat')
        for i, message in enumerate(self._data[-10:]):
            user_id, text = message['user_id'], message['message_text']
            text = f'{user_id}: {text}'
            self._scr.addstr(i + 1, 1, text)


class InputWindow(Window):

    def __init__(self, scr, user_name):
        super().__init__(scr)
        self._scr = scr
        self._prompt = list(f'{user_name} > ')

    def send_input(self, char):
        result = None
        if 31 < char < 126:
            self._data.append(chr(char))
        elif char == curses.KEY_BACKSPACE:
            if self._data: 
                del self._data[-1]
        elif char == curses.KEY_ENTER:
            result = ''.join(self._data)
            self._data = []
        self._needs_redraw = True
        return result

    def redraw(self):
        self._scr.erase()
        self._scr.border(0, 0, ' ', 0, 
                         curses.ACS_VLINE, curses.ACS_VLINE, 0, curses.ACS_BTEE)

        data = self._prompt + self._data
        chars_per_line = self._width - 2
        lines = math.ceil(len(data) / chars_per_line)
        for line in range(lines):
            start = line * chars_per_line
            end = start + chars_per_line
            text = ''.join(data[start:end])
            self._scr.addstr(line, 1, text)
        my, mx = lines - 1, (len(data) % chars_per_line) + 1
        my += 1 if mx == 1 else 0
        self._scr.move(my, mx)


def main(stdscr, user_id, data_address, broadcast_address):
    height, width = stdscr.getmaxyx()
    left_pane_width = int(_LEFT_PANE_PERCENT * width)
    right_pane_width = width - left_pane_width
    input_height = int(_INPUT_HEIGHT_PERCENT * height)
    messages_height = height - input_height

    # Component which renders the current conversation messages.
    n_lines, n_cols = messages_height, left_pane_width
    begin_y, begin_x = 0, 0
    win = stdscr.subwin(n_lines, n_cols, begin_y, begin_x)
    messages_win = MessagesWindow(win)

    def on_new_message(message):
        messages_win.data = messages_win.data + [message]

    client = client_lib.Client(user_id, data_address, broadcast_address, on_new_message)
    user_name = client.get_users([user_id])[0]['user_name']

    # Component which handles the input box.
    n_lines, n_cols = input_height, left_pane_width
    begin_y, begin_x = messages_height, 0
    win = stdscr.subwin(n_lines, n_cols, begin_y, begin_x)
    input_win = InputWindow(win, user_name)

    # Component which renders chats.
    n_lines, n_cols = height, right_pane_width
    begin_y, begin_x = 0, left_pane_width 
    win = stdscr.subwin(n_lines, n_cols, begin_y, begin_x)
    chats_win = ChatsWindow(win)

    chats = client.get_chats(user_id)
    chat_id = chats[0]['chat_id']
    chats_win.data = chats
    messages = client.get_messages(chat_id)
    messages_win.data = messages
 
    stdscr.timeout(17)
    while True:
        # Draw the screen.
        input_win.draw()
        messages_win.draw()
        chats_win.draw()
        curses.doupdate()

        # Get input and standardize key presses.
        char = stdscr.getch()
        if char in (10, 13):
            char = curses.KEY_ENTER
        elif char == 127:
            char = curses.KEY_BACKSPACE
        
        # Update state.
        message_text = input_win.send_input(char)
        if message_text is not None:
            message = client.insert_message(chat_id, user_id, message_text)
            messages_win.data = messages_win.data + [message]

 
if __name__ == '__main__':
    # Parse flags.
    parser = argparse.ArgumentParser()
    parser.add_argument('--user_id', type=int, required=True, 
                        help='Id for the connected user')
    FLAGS = parser.parse_args()
    user_id = FLAGS.user_id
    data_address = (constants.LOCALHOST, constants.DATA_PORT)
    broadcast_address = (constants.LOCALHOST, constants.BROADCAST_PORT)
    curses.wrapper(main, user_id, data_address, broadcast_address)
