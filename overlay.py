import logging
import queue

import cv2 as cv
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import Tk


class OverlayWindow(Tk):

    def __init__(self, quit_button="<Button-1>", clear_button="<Enter>"):
        super().__init__()
        self.lift()
        self.iconbitmap("neondb/neon.ico")
        self.title("neonabyss_tooltip")
        self.check_interval = 100
        self.evtQueue = queue.Queue()
        self.column_size = 150
        self.bgcolor = "black"
        self.fgcolor = "white"
        self.small_font = "helvetica 12"
        self.large_font = "helvetica 14"
        self.configure(background='mediumorchid4')
        self.geometry("+0+0")
        self.overrideredirect(True)
        if quit_button is not None:
            self.bind(quit_button, lambda event: OverlayWindow.quit(self))
        if clear_button is not None:
            self.bind(clear_button, lambda event: OverlayWindow.__message(self, "Waiting..."))
        self.wm_attributes("-topmost", True)
        self.wm_attributes("-transparentcolor", 'mediumorchid4')
        self.frame = tk.Frame(self,
                              background='mediumorchid4'
                              )

    def __clear(self):
        for child in self.frame.winfo_children():
            child.destroy()

    def __message(self, text):
        self.__clear()
        lbl = tk.Label(self.frame,
                          text=text,
                          font=self.small_font,
                          background=self.bgcolor,
                          foreground=self.fgcolor,
                          wraplength=self.column_size,
                          justify="center")
        lbl.grid(row=1, column=1)
        self.pack()
        self.__position()
        self.lift()

    def __items(self, items):
        self.__clear()

        if len(items) < 1:
            self.__message("Nothing found !")
            return

        for i, item in enumerate(items):
            ttl_lbl = tk.Label(self.frame,
                               text=item["name"] ,
                               font=self.large_font,
                               background=self.bgcolor,
                               foreground=self.fgcolor,
                               wraplength=self.column_size,
                               justify="center")
            ttl_lbl.grid(row=0, column=i)

            tkimg = ImageTk.PhotoImage(image=Image.fromarray(cv.cvtColor(item["small-img"], cv.COLOR_RGB2BGR)))
            img_lbl = tk.Label(self.frame, image=tkimg)
            img_lbl.image = tkimg
            img_lbl.grid(row=1, column=i)

            dsc_lbl = tk.Label(self.frame,
                               text=item["desc"],
                               font=self.small_font,
                               background=self.bgcolor,
                               foreground=self.fgcolor,
                               wraplength=self.column_size,
                               justify="center")
            dsc_lbl.grid(row=2, column=i)

            if "itemSet" in item and item["itemSet"]:
                tksetimg = ImageTk.PhotoImage(image=Image.fromarray(item["itemSet"]["img"]))
                set_img_lbl = tk.Label(self.frame,
                                       image=tksetimg,
                                       text=item["itemSet"]["slug"],
                                       font=self.small_font,
                                       background=self.bgcolor,
                                       foreground=self.fgcolor,
                                       wraplength=self.column_size,
                                       justify="center")
                set_img_lbl.image = tksetimg
                set_img_lbl.grid(row=3, column=i)

            if "atk" in item:
                text = f"Type d'arme : {item['atk']}"
                if "passive" in item and len(item["passive"]) > 0:
                    passive = item['passive'].replace("^'s ", "").replace("^' ", "")
                    text = f"{text}\nPassif: {passive}\n"
                if "active" in item and len(item["active"]) > 0:
                    for active in item["active"]:
                        text = f"{text}\nActif: {active['name']}\n"

                variant_lbl = tk.Label(self.frame,
                                   text=text,
                                   font=self.small_font,
                                   background=self.bgcolor,
                                   foreground=self.fgcolor,
                                   wraplength=self.column_size,
                                   justify="center")
                variant_lbl.grid(row=4, column=i)

        self.pack()
        self.__position()
        self.lift()

    def __check_queue(self):
        try:
            fct = self.evtQueue.get(block=False)
        except queue.Empty:
            self.after(self.check_interval, self.__check_queue)
            return

        logging.info(f"GUI event triggered : {fct}")
        try:
            if fct is not None:
                fct()
        except:
            logging.exception("Event queue action failed !")
        self.after(self.check_interval, self.__check_queue)

    def __position(self):
        self.geometry('+%d+%d' % (0, 0))

    def set_message(self, message):
        self.evtQueue.put(lambda: self.__message(message))

    def set_items(self, items):
        self.evtQueue.put(lambda: self.__items(items))

    def run(self):
        self.after(self.check_interval, self.__check_queue)
        self.mainloop()

    def pack(self):
        self.frame.pack()