

import logging
import threading
import typing

from PIL import Image
from mss import mss
from pynput import keyboard, mouse
from pynput.keyboard import KeyCode


class Screener(object):
    def __init__(self, listener: typing.Callable[[Image], typing.NoReturn], pixel_sensibility=10):
        self.mouse_pos = None
        self.press_start = None
        self.pixel_sensibility = pixel_sensibility
        self.last_region = None
        self.is_pressing = False
        self.listener = listener

    def run(self):
        with keyboard.Listener(on_press=self._on_press, on_release=self._on_release) as key_listener:
            with mouse.Listener(on_move=self._on_move) as mouse_listener:
                mouse_listener.join()
            key_listener.join()

    def start(self):
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        return thread

    @staticmethod
    def _get_full_display_size(screener: mss) -> typing.Dict[str, int]:
        monitors = screener
        left = monitors[0]["left"]
        top = monitors[0]["top"]
        width = monitors[0]["width"]
        height = monitors[0]["height"]
        for i in range(1, len(monitors)):
            left = min(left, monitors[i]["left"])
            top = min(top, monitors[i]["top"])
            width = max(width, monitors[i]["width"])
            height = max(height, monitors[i]["height"])
        return {"left": left, "top": top, "width": width, "height": height}

    def _get_screen_region(self, screener: mss) -> typing.Dict[str, int]:
        if self.mouse_pos is None:
            logging.debug("mouse_pos is None ?!")
            return

        if self.press_start is None \
                or abs(self.press_start[0] - self.mouse_pos[0]) < self.pixel_sensibility \
                or abs(self.press_start[1] - self.mouse_pos[1]) < self.pixel_sensibility:
            if self.last_region is not None:
                logging.debug(f"region is last_region : {self.last_region}")
                return self.last_region
            logging.debug(f"region is full monitor : {self.last_region}")
            return Screener._get_full_display_size(screener.monitors)
        return {\
            "left": min(self.mouse_pos[0], self.press_start[0]),\
            "top": min(self.mouse_pos[1], self.press_start[1]),\
            "width": abs(self.mouse_pos[0] - self.press_start[0]),\
            "height": abs(self.mouse_pos[1] - self.press_start[1])\
            }

    def _do_screen(self):
        with mss() as screener:
            region = self._get_screen_region(screener)
            self.last_region = region
            sct_img = screener.grab(region)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            logging.debug("Image captured")
            if self.listener is not None:
                self.listener(img)

    def _on_press(self, key: KeyCode):
        if not self.is_pressing:
            if key == keyboard.Key.ctrl_r:
                self.is_pressing = True
                self.press_start = self.mouse_pos
                logging.debug(f"press CTRL at {self.press_start}")
            else:
                self.is_pressing = False
                self.press_start = None
                logging.debug(f"Another key was typed, aborting : {key}")

    def _on_release(self, key: KeyCode):
        if self.is_pressing and key == keyboard.Key.ctrl_r:
            self.is_pressing = False
            logging.debug(f"release CTRL at {self.mouse_pos}")
            self._do_screen()

    def _on_move(self, x, y):
        self.mouse_pos = (x, y)