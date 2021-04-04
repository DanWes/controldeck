#!/usr/bin/env python
import sys
from os import path, sep, makedirs
from subprocess import Popen, PIPE, STDOUT
from configparser import ConfigParser, DuplicateSectionError
from re import search, IGNORECASE
from justpy import Div, WebPage, SetRoute, justpy

APP_NAME = "ControlDeck"

def process(args):
  try:
    # with shell=True args can be a string
    # detached process https://stackoverflow.com/a/65900355/992129 start_new_session
    # https://docs.python.org/3/library/subprocess.html#popen-constructor
    result = Popen(args, stdout=PIPE, stderr=STDOUT, shell=True, start_new_session=True)
    return result.stdout.read().decode("utf-8").rstrip()
  except Exception as e:
    print(f"{e} failed!")

def volume(name):
  result = process(f'pamixer --get-volume --sink "{name}"')
  if search("The sink doesn't exit", result):
    result = "--"
  elif search("pamixer: command not found", result) is not None:
    n = process(r"pactl list sinks short | awk '{print $2}'").split()
    v = process(r"pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'").split()
    if name in n:
      result = v[n.index(name)]
    else:
      result = '--'
  return result

def volume_decrease(name):
  result = process(f'pamixer --get-volume --sink "{name}" --decrease 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-volume "{name}" -5%')
    #process(f'pactl set-sink-volume "{name}" -5db')
    result = volume(name)
  return result

def volume_increase(name):
  result = process(f'pamixer --get-volume --sink "{name}" --increase 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-volume "{name}" +5%')
    #process(f'pactl set-sink-volume "{name}" +5db')
    result = volume(name)
  return result

class Button(Div):
  command = None
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.classes = "bg-gray-800 hover:bg-gray-700 w-20 h-20 m-2 p-1 rounded-lg font-bold flex items-center text-center justify-center select-none"
    if self.command is not None:
      def click(self, msg):
        print(self.command)
        # string works only with shell
        if isinstance(self.command, (list)):
          # e.g.: [['pkill', 'ArdourGUI'], ['systemctl', '--user', 'restart', 'pipewire', 'pipewire-pulse'], ['ardour6', '-n', 'productive-pipewire']]
          if isinstance(self.command[0], (list)):
            [process(i) for i in self.command]
          else:
            # e.g.: ['pkill', 'ArdourGUI']
            process(self.command)
        else:
          # e.g.: 'pkill ArdourGUI'
          process(self.command)
      self.on('click', click)

class ButtonSound(Div):
  div = None
  name = None
  description = None
  volume = None

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.classes = "grid-rows-2"
    self.div = Div(classes="flex")
    Button(inner_html=f'{self.description}<br> - 5%', click=self.decrease, a=self.div)
    Button(inner_html=f'{self.description}<br> + 5%', click=self.increase, a=self.div)
    self.add(self.div)
    self.volume = Div(text=f"Volume: {volume(self.name)}%", classes="text-center -mt-2", a=self)

  async def decrease(self, msg):
    self.volume.text = f'Volume: {volume_decrease(self.name)}%'

  async def increase(self, msg):
    self.volume.text = f'Volume: {volume_increase(self.name)}%'

@SetRoute('/')
def application():
  wp = WebPage(title=APP_NAME, body_classes="bg-gray-900")
  wp.head_html = '<meta name="viewport" content="width=device-width, initial-scale=1">'

  # div = Div(classes="flex flex-wrap", a=wp)
  # ButtonSound(name="Stream_sink", description="Stream sink", a=div)
  # div2 = Div(classes="flex flex-wrap", a=wp)
  # Button(text="Sleep", command='systemctl suspend', a=div2)

  config = ConfigParser(strict=False)
  config_file = "controldeck.conf"
  full_config_file_path = path.dirname(path.realpath(__file__)) + sep + config_file
  if not path.exists(config_file):
    config_folder = path.join(path.expanduser("~"), '.config', APP_NAME.lower())
    makedirs(config_folder, exist_ok=True)
    full_config_file_path = path.join(config_folder, config_file)
  try:
    config.read(full_config_file_path)
  except Exception as e:
    print(f"{e}")
  #print(config.sections())
  volume_dict = {}
  button_dict = {}
  for i in config.sections():
    iname = None
    iname = search("^([0-9]*.?)volume", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      try:
        volume_dict[id] += [{'description': i[iname.end(0)+1:],
                             'name': config.get(i, 'name', fallback=None)}]
      except KeyError:
        volume_dict[id] = [{'description': i[iname.end(0)+1:],
                            'name': config.get(i, 'name', fallback=None)}]
    iname = search("^([0-9]*.?)button", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      try:
        button_dict[id] += [{'text': i[iname.end(0)+1:],
                             'command': config.get(i, 'command', fallback=None)}]
      except KeyError:
        button_dict[id] = [{'text': i[iname.end(0)+1:],
                            'command': config.get(i, 'command', fallback=None)}]
  for i in volume_dict:
    for j in volume_dict[i]:
      if 'div'+i not in vars():
        vars()['div'+i] = Div(classes="flex flex-wrap", a=wp)
      ButtonSound(name=j['name'], description=j['description'], a=eval('div'+i))
  for i in button_dict:
    for j in button_dict[i]:
      if 'div'+i not in vars():
        vars()['div'+i] = Div(classes="flex flex-wrap", a=wp)
      Button(text=j['text'], command=j['command'], a=eval('div'+i))

  if not wp.components:
    # config not found or empty, therefore insert an empty div to not get an error
    Div(text="add elements in controldeck.conf", classes="flex flex-wrap", a=wp)

  return wp

def main():
  justpy(host="0.0.0.0")

if __name__ == '__main__':
  sys.exit(main())
