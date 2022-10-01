#!/usr/bin/env python
import sys
import os
import argparse
from tkinter import Tk, messagebox
from webview import create_window, start
from controldeck import config_load, process
import threading
import time

def thread_function(name):
  # print("Thread %s: starting", name)
  for i in range(10):
    # print("Thread %s: finishing", name)
    # p = process("xdotool search --name 'ControlDeck'")
    # intersection of ControlDeck window name and empty classname
    p = process("comm -12 <(xdotool search --name 'ControlDeck' | sort) <(xdotool search --classname '^$' | sort)", shell=True)
    if p:
      # print(p)
      # process("xdotool search --name 'ControlDeck' set_window --class 'controldeck'", output=False)
      # process("xdotool search --name 'ControlDeck' set_window --classname 'controldeck' --class 'ControlDeck' windowunmap windowmap", output=False)  # will find to many wrong ids
      process(f"xdotool set_window --classname 'controldeck' --class 'ControlDeck' {p} windowunmap {p} windowmap {p}", shell=True, output=False)
    time.sleep(0.1)

def main(args, pid=-1):
  config = config_load(conf=args.config)
  host = config.get('default', 'host', fallback='0.0.0.0')
  port = config.get('default', 'port', fallback='8000')
  url = f"http://{host}:{port}/?gui&pid={str(pid)}"
  try:
    width = int(config.get('gui', 'width', fallback=800))
  except ValueError as e:
    print(f"{e}")
    width = 800
  try:
    height = int(config.get('gui', 'height', fallback=600))
  except ValueError as e:
    print(f"{e}")
    width = 600
  try:
    x = int(config.get('gui', 'x', fallback=''))
  except ValueError as e:
    print(f"{e}")
    x = None
  try:
    y = int(config.get('gui', 'y', fallback=''))
  except ValueError as e:
    print(f"{e}")
    y = None
  resizable = config.get('gui', 'resizable', fallback='True').title() == 'True'
  fullscreen = config.get('gui', 'fullscreen', fallback='False').title() == 'True'
  try:
    min_width = int(config.get('gui', 'min_width', fallback=200))
  except ValueError as e:
    print(f"{e}")
    min_width = 200
  try:
    min_height = int(config.get('gui', 'min_height', fallback=100))
  except ValueError as e:
    print(f"{e}")
    min_width = 100
  min_size = (min_width, min_height)
  frameless = config.get('gui', 'frameless', fallback='False').title() == 'True'
  minimized = config.get('gui', 'minimized', fallback='False').title() == 'True'
  on_top = config.get('gui', 'always_on_top', fallback='False').title() == 'True'

  #controldeck_process = process("ps --no-headers -C controldeck")
  controldeck_process = process("ps --no-headers -C controldeck || ps aux | grep -e 'python.*controldeck.py' | grep -v grep", shell=True, output=True)

  if args.start and controldeck_process == "":
    cmd = "controldeck"
    cmd += " --config={args.config}" if args.config else ""
    print(cmd)
    process(cmd, shell=True, output=False)

  elif controldeck_process == "":
    # cli output
    print("controldeck is not running!")

    # gui output
    # Tkinter must have a root window. If you don't create one, one will be created for you. If you don't want this root window, create it and then hide it:
    root = Tk()
    root.withdraw()
    messagebox.showinfo("ControlDeck", "controldeck is not running!")
    # Other option would be to use the root window to display the information (Label, Button)

    sys.exit(2)

  create_window("ControlDeck",
                url=url,
                html=None,
                js_api=None,
                width=width,
                height=height,
                x=x,
                y=y,
                resizable=resizable,
                fullscreen=fullscreen,
                min_size=min_size,
                hidden=False,
                frameless=frameless,
                easy_drag=True,
                minimized=minimized,
                on_top=on_top,
                confirm_close=False,
                background_color='#000000',
                transparent=True,
                text_select=False)
  x = threading.Thread(target=thread_function, args=(1,))
  x.start()
  start()

def cli():
  parser = argparse.ArgumentParser(
    description=__doc__, prefix_chars='-',
    formatter_class=argparse.RawTextHelpFormatter,
  )
  parser.add_argument('-c', '--config', nargs='?', type=str, default='',
                      help="Specify a path to a custom config file (default: ~/.config/controldeck/controldeck.conf)")
  parser.add_argument('-s', '--start', action="store_true",
                      help="Start also controldeck program")
  parser.add_argument('-v', '--verbose', action="store_true", help="Verbose output")
  parser.add_argument('-D', '--debug', action='store_true', help=argparse.SUPPRESS)
  args = parser.parse_args()

  if args.debug:
    print(args)

  main(args, pid=os.getpid())

  return 0

if __name__ == '__main__':
  sys.exit(cli())
