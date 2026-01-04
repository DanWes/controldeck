#!/usr/bin/env python
import sys
import os
import argparse
from tkinter import Tk, messagebox
import webview
from controldeck_nicegui import config, process
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
    width = config.getint('gui', 'width', fallback=800)
  except ValueError as e:
    width = 800
    print(f"Error width: {e}. fallback to: {width}")
  try:
    height = config.getint('gui', 'height', fallback=600)
  except ValueError as e:
    width = 600
    print(f"Error height: {e}. fallback to {width}")
  try:
    x = config.getint('gui', 'x', fallback='')
  except ValueError as e:
    x = None
    print(f"Error x: {e}. fallback to {x}")
  try:
    y = config.getint('gui', 'y', fallback='')
  except ValueError as e:
    y = None
    print(f"Error y: {e}. fallback to: {y}")
  resizable = config.get('gui', 'resizable', fallback='True').title() == 'True'
  fullscreen = config.get('gui', 'fullscreen', fallback='False').title() == 'True'
  try:
    min_width = config.getint('gui', 'min_width', fallback=200)
  except ValueError as e:
    min_width = 200
    print(f"Error min_width: {e}. fallback to: {min_width}")
  try:
    min_height = config.getint('gui', 'min_height', fallback=100)
  except ValueError as e:
    min_height = 100
    print(f"Error min_height: {e}. fallback to: {min_height}")
  min_size = (min_width, min_height)
  frameless = config.get('gui', 'frameless', fallback='False').title() == 'True'
  minimized = config.get('gui', 'minimized', fallback='False').title() == 'True'
  maximized = config.get('gui', 'maximized', fallback='False').title() == 'True'
  on_top = config.get('gui', 'always_on_top', fallback='False').title() == 'True'
  confirm_close = config.get('gui', 'confirm_close', fallback='False').title() == 'True'
  transparent = config.get('gui', 'transparent', fallback='True').title() == 'True'
  gui_type = config.get('gui', 'gui_type', fallback=None)
  gui_type = gui_type if gui_type != "" else None
  menu = config.get('gui', 'menu', fallback='True').title() == 'True'
  if args.debug:
    print(f"config file [default]: {config.items('default')}")
    print(f"config file [gui]: {config.items('gui')}")

  #controldeck_process = process("ps --no-headers -C controldeck")
  #controldeck_process = process("ps --no-headers -C controldeck || ps aux | grep -e 'python.*controldeck.py' | grep -v grep", shell=True, output=True)
  controldeck_process = process("ps --no-headers -C controldeck || ps aux | grep -e 'python.*controldeck_nicegui.py' | grep -v grep", shell=True, output=True)

  if args.start and controldeck_process == "":
    #cmd = "controldeck"
    cmd = "controldeck_gui"
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

  window = webview.create_window(
    title="ControlDeck",
    url=url,
    html=None,
    js_api=None,
    width=width,
    height=height,
    x=x,
    y=y,
    screen=None,
    resizable=resizable,
    fullscreen=fullscreen,
    min_size=min_size,
    hidden=False,
    frameless=frameless,
    easy_drag=True,
    focus=True,
    minimized=minimized,
    maximized=maximized,
    on_top=on_top,
    confirm_close=confirm_close,
    background_color='#000000',
    transparent=transparent,  # TODO: bug in qt; menu bar is transparent
    text_select=False,
    zoomable=False,  # zoom via js
    draggable=False,
    vibrancy=False,
    localization=None,
  )
  x = threading.Thread(target=thread_function, args=(1,))
  x.start()

  def menu_reload():
    window = webview.active_window()
    if window:
      url = window.get_current_url()
      window.load_url(url)
      print(window.get_current_url())
      print(window)
      print(dir(window))
  def menu_zoomin():
    window = webview.active_window()
    if window:
      zoom = window.evaluate_js('document.documentElement.style.zoom')
      if zoom == "":
        zoom = 1.0
      else:
        zoom = float(zoom)
      zoom += 0.1
      print(f"zoom-in: {zoom}")
      window.evaluate_js(f'document.documentElement.style.zoom = {zoom}')
      print(f"set document.documentElement.style.zoom = {zoom}")
  def menu_zoomout():
    window = webview.active_window()
    if window:
      zoom = window.evaluate_js('document.documentElement.style.zoom')
      if zoom == "":
        zoom = 1.0
      else:
        zoom = float(zoom)
      zoom -= 0.1
      print(f"zoom-out: {zoom}")
      window.evaluate_js(f'document.documentElement.style.zoom = {zoom}')
      print(f"set document.documentElement.style.zoom = {zoom}")
  def menu_zoomreset():
    window = webview.active_window()
    if window:
      zoom = 1.0
      print(f"zoom-reset: {zoom}")
      window.evaluate_js(f'document.documentElement.style.zoom = {zoom}')
      print(f"set document.documentElement.style.zoom = {zoom}")
  menu_items = []
  if menu:
    menu_items = [webview.menu.Menu(
      'Main', [
        webview.menu.MenuAction('Reload', menu_reload),
        webview.menu.MenuAction('zoom +', menu_zoomin),
        webview.menu.MenuAction('zoom -', menu_zoomout),
        webview.menu.MenuAction('zoom reset', menu_zoomreset),
      ]
    )]
  # TODO: zoom reset on reload (both from menu and within justpy)
  # TODO: add zoom in config
  # TODO: move zoom logic to justpy but then it is fix for all,
  #   maybe better a zoom argument in url address

  def win_func(window):
    print(window.get_current_url())
  webview.start(
    func=win_func,
    args=window,
    gui=gui_type,  # TODO: bug in qt; any menu action is always the last action
    debug=args.debug,
    menu=menu_items,
  )

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
