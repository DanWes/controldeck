#!/usr/bin/env python
import sys
from webview import create_window, start
import controldeck

def main():
  if controldeck.process("ps -ef | grep -i controldeck.py | grep -v grep") == "":
    controldeck.main()

  create_window("ControlDeck",
                url="http://0.0.0.0:8000",
                width=800,
                height=600,
                frameless=True,
                easy_drag=True,
                background_color='#000000',
                transparent=True)
  start()

if __name__ == '__main__':
  sys.exit(main())
