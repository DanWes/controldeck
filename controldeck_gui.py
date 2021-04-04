#!/usr/bin/env python
import sys
from webview import create_window, start
import controldeck

def main():
  if controldeck.process("ps -ef | grep -i controldeck.py | grep -v grep") == "":
    controldeck.main()

  config = controldeck.config_load()
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

  create_window("ControlDeck",
                url="http://0.0.0.0:8000",
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
  start()

if __name__ == '__main__':
  sys.exit(main())
