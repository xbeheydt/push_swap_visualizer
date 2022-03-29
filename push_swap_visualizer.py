#!/usr/bin/env python3

################################################################################
##                                                                            ##
##                                                        :::      ::::::::   ##
##   push_swap_visualizer.py                            :+:      :+:    :+:   ##
##                                                    +:+ +:+         +:+     ##
##   By: xbeheydt <xbeheydt@42lausanne.ch>          +#+  +:+       +#+        ##
##                                                +#+#+#+#+#+   +#+           ##
##   Created: 2022/03/09 11:05:43 by xbeheydt          #+#    #+#             ##
##   Updated: 2022/03/09 11:48:48 by xbeheydt         ###   ########.ch       ##
##                                                                            ##
################################################################################

"""
Push_swap_visualizer is GUI app helps to visualize algorithm from push_swap.

This is a fork.

The original app was writing by o-reo <eruaud@student.le-101.fr>.
    - Original project : https://github.com/o-reo/push_swap_visualizer
"""

from argparse import ArgumentParser
from io import BytesIO
from os import X_OK, access
from os import path as os_path
from random import shuffle
from subprocess import STDOUT, TimeoutExpired, check_output
from time import sleep
from tkinter import (
    BOTH,
    BOTTOM,
    END,
    FLAT,
    LEFT,
    RIGHT,
    SINGLE,
    TOP,
    X,
    Button,
    Canvas,
    Checkbutton,
    Entry,
    Frame,
    IntVar,
    Label,
    Listbox,
    Scrollbar,
    StringVar,
    Tk,
    Toplevel,
)
from typing import Any, List

import imageio as iio
import numpy as np

# Helper classes ===============================================================


class Stack(List):
    """
    Stack handler
    """

    def rot(self) -> None:
        self.append(self.pop(0))

    def rev_rot(self) -> None:
        self.insert(0, self.pop())

    def push(self, dstStack: List) -> None:
        dstStack.insert(0, self.pop(0))

    def swap(self) -> None:
        self.insert(1, self.pop(0))

    def size(self) -> int:
        return len(self)

    @staticmethod
    def ss(a: List, b: List) -> None:
        a.swap()
        b.swap()

    @staticmethod
    def rr(a: List, b: List) -> None:
        a.rot()
        b.rot()

    @staticmethod
    def rrr(a: List, b: List) -> None:
        a.rev_rot()
        b.rev_rot()

    @staticmethod
    def generator(min: int, max: int, size: int, rand: int) -> List[int]:
        li = list(range(min, max))
        if rand:
            shuffle(li)
        if size > 0:
            return li[0:size]
        return li

    @staticmethod
    def action(action: str, a, b):
        if action == "sa":
            a.swap()
        elif action == "sb":
            b.swap()
        elif action == "ss":
            Stack.ss(a, b)
        elif action == "ra":
            a.rot()
        elif action == "rb":
            b.rot()
        elif action == "rr":
            Stack.rr(a, b)
        elif action == "rra":
            a.rev_rot()
        elif action == "rrb":
            b.rev_rot()
        elif action == "rrr":
            Stack.rrr(a, b)
        elif action == "pa":
            b.push(a)
        elif action == "pb":
            a.push(b)
        return (a, b)


class Gif(List):
    def __init__(self, path: str, fps: int = 10, loop: int = 0) -> None:
        self.__path = path
        self.__kwargs = {"fps": fps, "loop": loop}
        self = []

    def canvas_append(self, cv: Canvas) -> None:
        ps = cv.postscript(colormode="color")
        self.append(iio.imread(BytesIO(ps.encode("utf-8"))))

    def save(self) -> None:
        iio.mimsave(self.__path, self, **self.__kwargs)

    def resize(self, width: int, height: int) -> None:
        for i, img in enumerate(self):
            self[i] = self.scale(img, width, height)

    @staticmethod
    def scale(img: np.array, width: int, height: int) -> np.array:
        n_rows = len(img)
        n_cols = len(img[0])
        return [
            [
                img[int(n_rows * row / height)][int(n_cols * cols / width)]
                for cols in range(width)
            ]
            for row in range(height)
        ]


# MVC app classes ==============================================================


class PSVizApp:
    def __init__(self) -> None:
        self.config = PSVizConfig()
        self.root = Tk()
        self.view = PSVizView(self, self.config)

        self.__lstCmd = ["Initial State"]
        self.__isPlay = 0
        self.__winStack = 0
        self.__winGifExport = 0

    def run(self) -> None:
        self.view.windowMain()
        self.view.path = self.config.path
        self.view.frameSpeed = self.config.speed
        self.__stack = None
        self.root.mainloop()

    def callbackPath(self, var, index, mode) -> None:
        try:
            self.config.path = self.view.path
        except ValueError:
            self.view.btnRun["state"] = "disable"
            self.view.entPath.configure(background="red")
        else:
            self.view.btnRun["state"] = "normal"
            self.view.entPath.configure(background="white")

    def clickRun(self) -> None:
        self.view.clearLstCmd()
        if self.__stack is not None:
            self.__stack = Stack(self.view.strStackLst)
        else:
            self.__stack = Stack([int(val) for val in self.config.stack])
        try:
            self.__lstCmd = [""] + [
                line.decode("utf-8")
                for line in check_output(
                    [self.config.path] + [str(val) for val in self.config.stack],
                    stderr=STDOUT,
                    timeout=self.config.timeout,
                ).splitlines()
            ]
        except TimeoutExpired:
            self.__lstCmd = ["", "Timeout"]
        self.view.lstCmd = self.__lstCmd
        if "Error" in self.__lstCmd or "Timeout" in self.__lstCmd:
            self.view.btnPrev["state"] = "disable"
            self.view.btnPlay["state"] = "disable"
            self.view.btnNext["state"] = "disable"
            self.view.entFramePos["state"] = "disable"
            self.view.framePos = 0
            self.view.frameNum = 0
        else:
            self.view.btnPrev["state"] = "normal"
            self.view.btnPlay["state"] = "normal"
            self.view.btnNext["state"] = "normal"
            self.view.entFramePos["state"] = "normal"
            self.view.framePos = 0
            self.view.frameNum = len(self.__lstCmd) - 1
            self.__runGotoCmds(0, 0)
            self.eventSelectFramePos()

    def clickNext(self) -> None:
        if self.view.framePos < self.view.frameNum:
            self.view.framePos += 1
            self.__runGotoCmds(0, self.view.framePos)

    def clickPrev(self) -> None:
        if self.view.framePos >= 0:
            self.view.framePos -= 1
            self.__runGotoCmds(0, self.view.framePos)

    def clickPlay(self) -> None:
        if self.__isPlay == 0:
            self.__isPlay = 1
            self.view.btnPlay["text"] = "||"
            self.view.btnPrev["state"] = "disable"
            self.view.btnNext["state"] = "disable"
            self.view.entFramePos["state"] = "disable"
            self.__runPlayCmds(self.view.framePos, self.view.frameNum)
            self.__isPlay = 0
            self.view.btnPrev["state"] = "normal"
            self.view.btnPlay["state"] = "normal"
            self.view.btnPlay["text"] = ">"
            self.view.btnNext["state"] = "normal"
            self.view.entFramePos["state"] = "normal"
        else:
            self.__isPlay = 0
            self.view.btnPrev["state"] = "normal"
            self.view.btnPlay["state"] = "normal"
            self.view.btnPlay["text"] = ">"
            self.view.btnNext["state"] = "normal"
            self.view.entFramePos["state"] = "normal"
            self.__runGotoCmds(0, self.view.framePos)

    def clickStack(self) -> None:
        if self.__winStack == 0:
            self.__winStack = 1
            self.view.windowStack()
            self.view.strStackLst = self.config.stack
        else:
            self.__winStack = 0
            self.view.winStack.destroy()

    def clickGifExportOpen(self) -> None:
        if self.__winGifExport == 0:
            self.__winGifExport = 1
            self.view.windowGifExport()
        else:
            self.__winGifExport = 0
            self.view.winGifExport.destroy()

    def clickGifExportRun(self) -> None:
        self.view.btnPrev["state"] = "disable"
        self.view.btnPlay["state"] = "disable"
        self.view.btnNext["state"] = "disable"
        self.view.entFramePos["state"] = "disable"
        self.config.gif_export = self.view.strGifExportPath
        self.__runPlayGif(0, self.view.frameNum)
        self.view.btnPrev["state"] = "normal"
        self.view.btnPlay["state"] = "normal"
        self.view.btnNext["state"] = "normal"
        self.view.entFramePos["state"] = "normal"

    def clickGenerate(self) -> None:
        if self.__isPlay == 0:
            self.config.min = self.view.stackMin
            self.config.max = self.view.stackMax
            self.config.size = self.view.stackSize
            self.config.stack = Stack.generator(
                self.config.min,
                self.config.max,
                self.config.size,
                self.view.chkStackShuffle,
            )
            self.view.strStackLst = self.config.stack

    def eventEnterSpeed(self, event) -> None:
        if self.view.frameSpeed < self.config.FRAME_SPEED_MIN:
            self.view.frameSpeed = self.config.FRAME_SPEED_MIN
        if self.view.frameSpeed > self.config.FRAME_SPEED_MAX:
            self.view.frameSpeed = self.config.FRAME_SPEED_MAX
        self.config.speed = self.view.frameSpeed

    def eventEnterFramePos(self, event) -> None:
        self.eventSelectFramePos()
        self.__runGotoCmds(0, self.view.framePos)

    def eventSelectFramePos(self) -> None:
        if self.view.framePos < 0:
            self.view.framePos = 0
        elif self.view.framePos > self.view.frameNum:
            self.view.framePos = self.view.frameNum
        self.view.lstCmd.select_clear(0, END)
        self.view.lstCmd.select_set(self.view.framePos)
        self.view.lstCmd.see(self.view.framePos)

    def __runPlayCmds(self, start: int, end: int) -> None:
        a = Stack(self.__stack.copy())
        b = Stack()
        if start > 0:
            for pos in range(0, start):
                a, b = Stack.action(self.__lstCmd[pos], a, b)
        for pos in range(start, end + 1):
            sleep(1 / self.config.speed)
            self.view.framePos = pos
            self.eventSelectFramePos()
            a, b = Stack.action(self.__lstCmd[pos], a, b)
            self.view.drawStack(a, b)
            if self.__isPlay == 0:
                break

    def __runGotoCmds(self, start: int, end: int) -> None:
        a = Stack(self.__stack.copy())
        b = Stack()
        for pos in range(start, end + 1):
            a, b = Stack.action(self.__lstCmd[pos], a, b)
        self.view.framePos = end
        self.eventSelectFramePos()
        self.view.drawStack(a, b)

    def __runPlayGif(self, start: int, end: int) -> None:
        a = Stack(self.__stack.copy())
        b = Stack()
        gif = Gif(path=self.config.gif_export, fps=self.view.strGifExportFps)

        for pos in range(start, end + 1):
            self.view.framePos = pos
            self.eventSelectFramePos()
            a, b = Stack.action(self.__lstCmd[pos], a, b)
            self.view.drawStack(a, b)
            gif.canvas_append(self.view.canViz)

        # FIXME : process is very long and very large memory is consummed
        # gif.resize(self.view.strGifExportSize, self.view.strGifExportSize)
        gif.save()


class PSVizConfig:

    APP_DESC = "Push Swap Visualizer"

    PUSH_SWAP_PATH = "./push_swap"

    CMD_TIMEOUT_MIN = 10
    CMD_TIMEOUT_MAX = 1024
    CMD_TIMEOUT = 12

    STACK_GEN_MIN = 0
    STACK_GEN_MAX = 100
    STACK_GEN_SIZE = 10

    FRAME_SPEED = 25
    FRAME_SPEED_MIN = 1
    FRAME_SPEED_MAX = 2048

    GIF_DEFAULT_PATH = "./psviz.gif"
    GIF_DEFAULT_FPS = 10
    GIF_DEFAULT_SIZE = 400

    def __init__(self) -> None:
        # init properties with default values
        self.__path = self.PUSH_SWAP_PATH
        self.__timeout = self.CMD_TIMEOUT
        self.__min = self.STACK_GEN_MIN
        self.__max = self.STACK_GEN_MAX
        self.__size = self.STACK_GEN_SIZE
        self.__speed = self.FRAME_SPEED
        self.__gif = os_path.abspath(self.GIF_DEFAULT_PATH)
        self.__gif_fps = self.GIF_DEFAULT_FPS
        self.__gif_size = self.GIF_DEFAULT_SIZE

        # setup and run cli argument parser
        self.parser = ArgumentParser(description=self.APP_DESC)
        self.__run_parser()

        # Errors handling
        # Non blocking
        self.stack = self.args.stack
        try:
            self.path = self.args.path
        except ValueError:
            pass
        # blocking
        try:
            self.timeout = self.args.timeout
            self.min = self.args.min
            self.max = self.args.max
            self.size = self.args.size
            self.speed = self.args.speed
        except ValueError:
            self.parser.print_help()
            exit(1)

        # Clean parser
        del self.parser
        del self.args

    def __error(self, msg: str) -> None:
        print("Argument Error : {}\n".format(msg))

    def __run_parser(self) -> None:
        # Positionnal arguments
        self.parser.add_argument(
            "stack",
            metavar="INT",
            nargs="*",
            help="your custom stack list",
            default=[],
        )

        # Optionnal flag arguments
        self.parser.add_argument(
            "--path",
            metavar="PATH",
            type=str,
            help="'push_swap' path (default: {})".format(self.__path),
            default=self.__path,
        )

        self.parser.add_argument(
            "-t",
            "--timeout",
            metavar="MS",
            type=int,
            help="timeout setting to run push_swap (default: {})".format(
                self.__timeout
            ),
            default=self.__timeout,
        )

        self.parser.add_argument(
            "-s",
            "--speed",
            metavar="FPS",
            type=int,
            help="frame speed refresh (default: {})".format(self.__speed),
            default=self.__speed,
        )

        self.parser.add_argument(
            "--min",
            metavar="INT",
            type=int,
            help="min value for stack generator (default: {})".format(self.__min),
            default=self.__min,
        )

        self.parser.add_argument(
            "--max",
            metavar="INT",
            type=int,
            help="max value for stack generator (default: {})".format(self.__max),
            default=self.__max,
        )

        self.parser.add_argument(
            "--size",
            metavar="INT",
            type=int,
            help="size value for stack generator (default: {})".format(self.__size),
            default=self.__size,
        )
        self.args = self.parser.parse_args()

    # path helpers
    @property
    def path(self) -> str:
        return self.__path

    @path.setter
    def path(self, p: str) -> None:
        self.__path = os_path.abspath(p)
        if not os_path.exists(self.__path):
            self.__error("{} not exists".format(self.__path))
            raise ValueError
        if not access(self.__path, X_OK):
            self.__error("{} is not executable".format(self.__path))
            raise ValueError

    @property
    def gif_export(self) -> str:
        return self.__gif

    @gif_export.setter
    def gif_export(self, path: str) -> None:
        self.__gif = path

    @property
    def gif_fps(self) -> int:
        return self.__gif_fps

    @gif_fps.setter
    def gif_fps(self, fps: int) -> None:
        self.__gif_fps = fps

    @property
    def gif_size(self) -> int:
        return self.__gif_size

    @gif_size.setter
    def gif_size(self, size: int) -> None:
        self.__gif_size = size

    # timeout helpers
    @property
    def timeout(self) -> int:
        return self.__timeout

    @timeout.setter
    def timeout(self, t: int) -> None:
        if t < self.CMD_TIMEOUT_MIN or t > self.CMD_TIMEOUT_MAX:
            self.__error(
                "timeout value between {} and {}".format(
                    self.CMD_TIMEOUT_MIN, self.CMD_TIMEOUT_MAX
                )
            )
            raise ValueError
        self.__timeout = t

    # min helpers
    @property
    def min(self) -> int:
        return self.__min

    @min.setter
    def min(self, m: int) -> None:
        self.__min = m
        if self.__min >= self.__max:
            print(m)
            print(self.__max)
            self.__error("min cannot be equal or upper than max")
            self.__min = self.STACK_GEN_MIN
            raise ValueError

    # max helpers
    @property
    def max(self) -> int:
        return self.__max

    @max.setter
    def max(self, m: int) -> None:
        self.__max = m
        if self.__max <= self.__min:
            self.__error("max cannot be equal or upper than min")
            self.__max = self.STACK_GEN_MAX
            raise ValueError

    # size helpers
    @property
    def size(self) -> int:
        return self.__size

    @size.setter
    def size(self, s: int) -> None:
        self.__size = s
        if self.__size < 0:
            self.__size = 0
            self.__error("size must be positive number or equal 0")
            self.__size = self.STACK_GEN_SIZE
            raise ValueError

    # speed helpers
    @property
    def speed(self) -> int:
        return self.__speed

    @speed.setter
    def speed(self, s: int) -> None:
        self.__speed = s
        if self.__speed < self.FRAME_SPEED_MIN:
            self.__error("min speed is {}".format(self.FRAME_SPEED_MIN))
            self.__speed = self.FRAME_SPEED_MIN
            raise ValueError
        if self.__speed > self.FRAME_SPEED_MAX:
            self.__error("max speed is {}".format(self.FRAME_SPEED_MAX))
            self.__speed = self.FRAME_SPEED_MAX
            raise ValueError


class PSVizView:
    """
    Class view for PSViz.
    """

    FONT_NORMAL = ("monospace", 12)
    FONT_SMALL = ("monospace", 10)

    CAN_BG_COL = "black"
    CAN_WIDTH = 800
    CAN_HEIGHT = 800

    LST_CMD_BG_COL = "black"
    LST_CMD_FG_COL = "white"

    ENT_CTRL_WIDTH = 5
    ENT_CTRL_PAD = 4

    BTN_CTRL_WIDTH = 5

    ENT_GIF_PATH_WIDTH = 50

    def __init__(self, app: PSVizApp, config: PSVizConfig) -> None:
        # Main setup app
        self.app = app
        self.config = config

        self.app.root.resizable(width=False, height=False)
        self.app.root.title(self.config.APP_DESC)
        self.app.root.eval("tk::PlaceWindow . center")

    def windowMain(self) -> None:
        # Root > Top frame
        self.__fmtTop = Frame(self.app.root)
        self.__canViz = Canvas(
            self.__fmtTop,
            width=self.CAN_WIDTH,
            height=self.CAN_HEIGHT,
            bg=self.CAN_BG_COL,
        )
        self.__fmtVizCmd = Frame(self.__fmtTop)
        self.__lstVizCmd = Listbox(
            self.__fmtVizCmd,
            bg=self.LST_CMD_BG_COL,
            fg=self.LST_CMD_FG_COL,
            font=self.FONT_NORMAL,
            selectmode=SINGLE,
            relief=FLAT,
        )

        self.__fmtTop.pack(side=TOP, fill=BOTH)
        self.__canViz.pack(side=LEFT)
        self.__fmtVizCmd.pack(side=RIGHT, fill=BOTH)
        self.__lstVizCmd.pack(fill=BOTH, expand=1)

        # Root > Bottom frame
        self.__fmtBottom = Frame(self.app.root)

        self.__fmtBottom.pack(side=BOTTOM, fill=X)

        # Root > Bottom Frame > Controle Frame
        self.__fmtCtrl = Frame(self.__fmtBottom)
        self.__lblFrame = Label(self.__fmtCtrl, text="frame:", font=self.FONT_SMALL)
        self.__strFramePos = StringVar(value="0")
        self.__entFramePos = Entry(
            self.__fmtCtrl,
            state="disable",
            width=self.ENT_CTRL_WIDTH,
            textvariable=self.__strFramePos,
            justify="center",
            relief=FLAT,
        )
        self.__entFramePos.bind("<Return>", self.app.eventEnterFramePos)
        self.__lblSep = Label(self.__fmtCtrl, text="/", font=self.FONT_SMALL)
        self.__strFrameNum = StringVar(value="0")
        self.__entFrameNum = Entry(
            self.__fmtCtrl,
            state="disable",
            width=self.ENT_CTRL_WIDTH,
            textvariable=self.__strFrameNum,
            justify="center",
            relief=FLAT,
        )
        self.__lblFrameSpeed = Label(
            self.__fmtCtrl, text=" speed:", font=self.FONT_SMALL
        )
        self.__strFrameSpeed = StringVar()
        self.__entFrameSpeed = Entry(
            self.__fmtCtrl,
            width=self.ENT_CTRL_WIDTH,
            textvariable=self.__strFrameSpeed,
            justify="center",
            relief=FLAT,
        )
        self.__entFrameSpeed.bind("<Return>", self.app.eventEnterSpeed)
        self.__btnNext = Button(
            self.__fmtCtrl,
            text=">>",
            command=self.app.clickNext,
            width=self.BTN_CTRL_WIDTH,
            state="disable",
        )
        self.__btnPlay = Button(
            self.__fmtCtrl,
            text=">",
            command=self.app.clickPlay,
            width=self.BTN_CTRL_WIDTH,
            state="disable",
        )
        self.__btnPrev = Button(
            self.__fmtCtrl,
            text="<<",
            command=self.app.clickPrev,
            width=self.BTN_CTRL_WIDTH,
            state="disable",
        )

        self.__fmtCtrl.pack(side=TOP, fill=X)
        self.__lblFrame.pack(side=LEFT)
        self.__entFramePos.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        self.__lblSep.pack(side=LEFT)
        self.__entFrameNum.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        self.__lblFrameSpeed.pack(side=LEFT)
        self.__entFrameSpeed.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        self.__btnNext.pack(side=RIGHT)
        self.__btnPlay.pack(side=RIGHT)
        self.__btnPrev.pack(side=RIGHT)

        # Root > Bottom Frame > Setting Frame
        self.__fmtSetting = Frame(self.__fmtBottom)
        self.__lblPath = Label(self.__fmtSetting, text="path :", font=self.FONT_SMALL)
        self.__strPath = StringVar()
        self.__entPath = Entry(
            self.__fmtSetting, textvariable=self.__strPath, justify="left"
        )
        self.__strPath.trace_add("write", self.app.callbackPath)
        self.__btnRun = Button(
            self.__fmtSetting,
            text="RUN",
            command=self.app.clickRun,
            width=self.BTN_CTRL_WIDTH,
        )
        self.__btnStack = Button(
            self.__fmtSetting,
            text="STACK",
            command=self.app.clickStack,
            width=self.BTN_CTRL_WIDTH,
        )
        self.__btnGitExportOpen = Button(
            self.__fmtSetting,
            text="GIF",
            command=self.app.clickGifExportOpen,
            width=self.BTN_CTRL_WIDTH,
        )

        self.__fmtSetting.pack(side=BOTTOM, fill=X)
        self.__lblPath.pack(side=LEFT)
        self.__entPath.pack(side=LEFT, ipady=self.ENT_CTRL_PAD, ipadx=292)
        self.__btnRun.pack(side=LEFT)
        self.__btnGitExportOpen.pack(side=RIGHT)
        self.__btnStack.pack(side=RIGHT)

    def windowStack(self) -> None:
        # Stack Window
        self.__winStack = Toplevel(self.app.root)
        self.__winStack.title("Stack list")
        self.__winStack.protocol("WM_DELETE_WINDOW", self.app.clickStack)

        # Stack Window > Stack Control Frame
        self.__fmtStackCtrl = Frame(self.__winStack)
        self.__lblStackMin = Label(
            self.__fmtStackCtrl, text="min :", font=self.FONT_SMALL
        )
        self.__strStackMin = StringVar(value=str(self.app.config.min))
        self.__entryStackMin = Entry(
            self.__fmtStackCtrl,
            textvariable=self.__strStackMin,
            justify="center",
            width=self.ENT_CTRL_WIDTH,
        )
        self.__lblStackMax = Label(
            self.__fmtStackCtrl, text="  max :", font=self.FONT_SMALL
        )
        self.__strStackMax = StringVar(value=str(self.app.config.max))
        self.__entStackMax = Entry(
            self.__fmtStackCtrl,
            textvariable=self.__strStackMax,
            justify="center",
            width=self.ENT_CTRL_WIDTH,
        )
        self.__lblStackSize = Label(
            self.__fmtStackCtrl, text="  size :", font=self.FONT_SMALL
        )
        self.__strStackSize = StringVar(value=str(self.app.config.size))
        self.__entStackSize = Entry(
            self.__fmtStackCtrl,
            textvariable=self.__strStackSize,
            justify="center",
            width=self.ENT_CTRL_WIDTH,
        )
        self.__lblStackShuffle = Label(
            self.__fmtStackCtrl, text="  shuffle :", font=self.FONT_SMALL
        )
        self.__intStackShuffle = IntVar(value=True)
        self.__chkStackShuffle = Checkbutton(
            self.__fmtStackCtrl, variable=self.__intStackShuffle, onvalue=1, offvalue=0
        )
        self.__btnStackGenerate = Button(
            self.__fmtStackCtrl,
            text="GENERATE",
            command=self.app.clickGenerate,
            width=self.BTN_CTRL_WIDTH * 2,
        )

        self.__fmtStackCtrl.pack(side=TOP, fill=X)
        self.__lblStackMin.pack(side=LEFT)
        self.__entryStackMin.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        self.__lblStackMax.pack(side=LEFT)
        self.__entStackMax.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        self.__lblStackSize.pack(side=LEFT)
        self.__entStackSize.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        self.__lblStackShuffle.pack(side=LEFT)
        self.__chkStackShuffle.pack(side=LEFT)
        self.__btnStackGenerate.pack(side=RIGHT, ipadx=14)

        # Stack Window > Stack List Frame
        self.__fmtStackLst = Frame(self.__winStack)
        self.__strStackLst = StringVar()
        self.__entStackLst = Entry(self.__fmtStackLst, textvariable=self.__strStackLst)
        self.__scrollStackLst = Scrollbar(self.__fmtStackLst, orient="horizontal")

        self.__fmtStackLst.pack(side=BOTTOM, fill=BOTH)
        self.__entStackLst.pack(side=TOP, fill=X, expand=1)
        self.__scrollStackLst.pack(side=BOTTOM, fill=X)

        # Config scrollbars
        self.__entStackLst.config(xscrollcommand=self.__scrollStackLst.set)
        self.__scrollStackLst.config(command=self.__entStackLst.xview)

    def windowGifExport(self) -> None:
        self.__winGifExport = Toplevel(self.app.root)
        self.__winGifExport.title("Gif Exporter")
        self.__winGifExport.protocol("WM_DELETE_WINDOW", self.app.clickGifExportOpen)

        self.__fmtGifExportCtrl = Frame(self.__winGifExport)
        self.__lblGifExportFps = Label(
            self.__fmtGifExportCtrl, text="FPS : ", font=self.FONT_SMALL
        )
        self.__strGifExportFps = StringVar(value=self.config.gif_fps)
        self.__entGifExportFps = Entry(
            self.__fmtGifExportCtrl,
            textvariable=self.__strGifExportFps,
            justify="center",
            width=self.ENT_CTRL_WIDTH,
        )

        self.__lblGifExportSize = Label(
            self.__fmtGifExportCtrl, text="size :", font=self.FONT_SMALL
        )
        self.__strGifExportSize = StringVar(value=self.config.gif_size)
        self.__entGifExportSize = Entry(
            self.__fmtGifExportCtrl,
            textvariable=self.__strGifExportSize,
            justify="center",
            width=self.ENT_CTRL_WIDTH,
        )

        self.__fmtGifExportPath = Frame(self.__winGifExport)
        self.__lblGifExportPath = Label(
            self.__fmtGifExportPath, text="path :", font=self.FONT_SMALL
        )
        self.__strGifExportPath = StringVar(value=self.config.gif_export)
        self.__entGifExportPath = Entry(
            self.__fmtGifExportPath,
            textvariable=self.__strGifExportPath,
            width=self.ENT_GIF_PATH_WIDTH,
        )
        self.__btnGifExportRun = Button(
            self.__fmtGifExportPath, text="RUN", command=self.app.clickGifExportRun
        )

        self.__fmtGifExportCtrl.pack(side=TOP, fill=X)
        self.__lblGifExportFps.pack(side=LEFT)
        self.__entGifExportFps.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)
        # self.__lblGifExportSize.pack(side=LEFT)
        # self.__entGifExportSize.pack(side=LEFT, ipady=self.ENT_CTRL_PAD)

        self.__fmtGifExportPath.pack(side=BOTTOM)
        self.__lblGifExportPath.pack(side=LEFT)
        self.__entGifExportPath.pack(side=LEFT, fill=X, ipady=self.ENT_CTRL_PAD)
        self.__btnGifExportRun.pack(side=LEFT)

    @property
    def canViz(self) -> Canvas:
        return self.__canViz

    @property
    def lstCmd(self) -> Listbox:
        return self.__lstVizCmd

    @lstCmd.setter
    def lstCmd(self, lst: List[str]) -> None:
        for i, line in enumerate(lst):
            self.__lstVizCmd.insert(i, "%5i :  %s" % (i, line))

    def clearLstCmd(self) -> None:
        self.__lstVizCmd.delete(0, self.__lstVizCmd.size())

    @property
    def framePos(self) -> int:
        if self.__strFramePos.get():
            return int(self.__strFramePos.get())
        self.__strFramePos.set("0")
        return 0

    @framePos.setter
    def framePos(self, pos: int) -> None:
        self.__strFramePos.set(str(pos))

    @property
    def entFramePos(self) -> Entry:
        return self.__entFramePos

    @property
    def frameNum(self) -> int:
        return int(self.__strFrameNum.get())

    @frameNum.setter
    def frameNum(self, num: int) -> None:
        self.__strFrameNum.set(str(num))

    @property
    def frameSpeed(self) -> int:
        if self.__strFrameSpeed.get():
            return int(self.__strFrameSpeed.get())
        self.__strFrameSpeed.set(1)
        return 1

    @frameSpeed.setter
    def frameSpeed(self, speed: int) -> None:
        self.__strFrameSpeed.set(str(speed))

    @property
    def btnPrev(self) -> Button:
        return self.__btnPrev

    @property
    def btnPlay(self) -> Button:
        return self.__btnPlay

    @property
    def btnNext(self) -> Button:
        return self.__btnNext

    @property
    def entPath(self) -> Entry:
        return self.__entPath

    @property
    def path(self) -> str:
        return self.__strPath.get()

    @path.setter
    def path(self, p: str) -> None:
        self.__strPath.set(p)

    @property
    def btnRun(self) -> Button:
        return self.__btnRun

    @property
    def btnStack(self) -> Button:
        return self.__btnStack

    @property
    def winStack(self) -> Toplevel:
        return self.__winStack

    @property
    def stackMin(self) -> int:
        return int(self.__strStackMin.get())

    @stackMin.setter
    def stackMin(self, m: int) -> None:
        self.__strStackMin.set(str(m))

    @property
    def stackMax(self) -> int:
        return int(self.__strStackMax.get())

    @stackMax.setter
    def stackMax(self, m: int) -> None:
        self.__strStackMax.set(str(m))

    @property
    def stackSize(self) -> int:
        return int(self.__strStackSize.get())

    @property
    def stackShuffle(self) -> int:
        return self.__chkStackShuffle.get()

    @property
    def btnStackGenerate(self) -> Button:
        return self.__btnStackGenerate

    @property
    def strStackLst(self) -> List[Any]:
        return [int(val) for val in self.__strStackLst.get().split(" ") if val]

    @strStackLst.setter
    def strStackLst(self, s: List[Any]) -> None:
        self.__strStackLst.set(" ".join([str(val) for val in s]))

    @property
    def chkStackShuffle(self) -> int:
        return (self.__chkStackShuffle)

    @property
    def winGifExport(self) -> Toplevel:
        return (self.__winGifExport)

    @property
    def strGifExportPath(self) -> str:
        return (self.__strGifExportPath.get())

    @strGifExportPath.setter
    def strGifExportPath(self, path: str) -> None:
        self.__strGifExportPath.set(path)

    @property
    def strGifExportFps(self) -> int:
        return (int(self.__strGifExportFps.get()))

    @strGifExportFps.setter
    def strGifExportFps(self, fps: int) -> None:
        self.__strGifExportFps.set(str(fps))

    @property
    def strGifExportSize(self) -> int:
        return (int(self.__strGifExportSize.get()))

    @strGifExportSize.setter
    def strGifExportSize(self, size: int) -> None:
        self.__strGifExportSize.set(str(size))

    # Utils methods
    def drawStack(self, a: Stack, b: Stack) -> None:
        self.__canViz.delete("all")
        vi = 0
        ww = self.CAN_WIDTH
        wh = self.CAN_HEIGHT
        hw = ww / 2
        hm = a.size() + b.size()
        mx, mn = (0, 0)
        self.__canViz.create_rectangle(
            0, 0, self.CAN_WIDTH + 2, self.CAN_HEIGHT + 2, outline="", fill="black"
        )

        if hm != 0:
            mx = max(a + b)
            mn = min(a + b)
        if a.size() > 0:
            a_val = [(num - mn) / (mx - mn) for num in a]
            for val in a_val:
                self.__canViz.create_rectangle(
                    0,
                    vi,
                    10 + val * (hw - 100),
                    vi + wh / hm,
                    fill=self.__colorIndexToHex(val),
                    outline="",
                )
                vi += wh / hm
        vi = 0
        if b.size() > 0:
            b_val = [(num - mn) / (mx - mn) for num in b]
            for val in b_val:
                self.__canViz.create_rectangle(
                    hw,
                    vi,
                    hw + 10 + val * (hw - 100),
                    vi + wh / hm,
                    fill=self.__colorIndexToHex(val),
                    outline="",
                )
                vi += wh / hm
        self.__canViz.update()

    # private methods
    @classmethod
    def __colorIndexToHex(cls, index: int) -> str:
        col = "#%02x%02x%02x" % (
            int(255 * (index - 0.3) * (index > 0.3)),
            int(255 * index - ((510 * (index - 0.6)) * (index > 0.6))),
            int((255 - 510 * index) * (index < 0.5)),
        )
        return col


# Main =========================================================================


def main() -> int:
    PSVizApp().run()


if __name__ == "__main__":
    main()
