#!/usr/bin/env python
import sys
from os import path, sep, makedirs
from subprocess import Popen, PIPE, STDOUT
from configparser import ConfigParser
from re import search, IGNORECASE
from justpy import Div, I, WebPage, SetRoute, parse_html, justpy

APP_NAME = "ControlDeck"

def process(args, output=True):
  try:
    # with shell=True args can be a string
    # detached process https://stackoverflow.com/a/65900355/992129 start_new_session
    # https://docs.python.org/3/library/subprocess.html#popen-constructor
    result = Popen(args, stdout=PIPE, stderr=STDOUT, shell=True, start_new_session=True)
    if output:
      return result.stdout.read().decode("utf-8").rstrip()
  except Exception as e:
    print(f"{e} failed!")

def volume(name):
  result = process(f'pamixer --get-volume-human --sink "{name}"')
  if search("The sink doesn't exit", result):
    result = "--"
  elif search("pamixer: command not found", result) is not None:
    n = process(r"pactl list sinks short | awk '{print $2}'").split()
    v = process(r"pactl list sinks | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'").split()
    if name in n:
      result = v[n.index(name)] + '%'
    else:
      result = '--'
  return result

def volume_decrease(name):
  result = process(f'pamixer --get-volume-human --sink "{name}" --decrease 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-volume "{name}" -5%')
    #process(f'pactl set-sink-volume "{name}" -5db')
    result = volume(name)
  return result

def volume_increase(name):
  result = process(f'pamixer --get-volume-human --sink "{name}" --increase 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-volume "{name}" +5%')
    #process(f'pactl set-sink-volume "{name}" +5db')
    result = volume(name)
  return result

def volume_mute(name):
  result = process(f'pamixer --get-volume-human --sink "{name}" --toggle-mute')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-mute "{name}" toggle')
    result = volume(name)
  return result

def config_load():
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
  return config

def svg_element(image):
  svg = ''
  if path.isfile(path.expanduser(image)):
    try:
      with open(path.expanduser(image)) as f:
        svg = f.read()
    except Exception as e:
      print(f"{e}")
  try:  # svg with custom tags, as inkscape is using, cannot be interpreted
    _svg = parse_html(svg)
    #print(dir(tmp_svg)) # add_attribute
    #print(tmp2.attributes)
    # set width and height to viewBox to update width and height for scaling
    w = _svg.width if hasattr(_svg, 'width') else "64"
    h = _svg.height if hasattr(_svg, 'height') else "64"
    vb = _svg.viewBox if hasattr(_svg, 'viewBox') else '0 0 ' + w + ' ' + h
    _svg.viewBox = vb
    _svg.width = 64
    _svg.height = 64
  except Exception as e:
    print(f"[Error SVG]: {e}")
    _svg = None
  return _svg

class Button(Div):
  btype = None
  command = None
  color_bg = ''
  color_fg = ''
  icon = ''
  image = ''
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    #print(dir(self))
    if self.btype == 'empty':
      self.classes = "w-20 h-20 m-2 p-1 flex select-none"
      self.text = ''

    else:
      self.classes = "bg-gray-800 hover:bg-gray-700 text-gray-500 w-20 h-20 m-2 p-1 rounded-lg font-bold flex items-center text-center justify-center select-none"

      self.style = f"background-color:{self.color_bg};" if ishexcolor(self.color_bg) else ''
      self.style += f"color:{self.color_fg};" if ishexcolor(self.color_fg) else ''

      if self.command is not None:
        def click(self, msg):
          print(self.command)
          # string works only with shell
          if isinstance(self.command, (list)):
            # e.g.: [['pkill', 'ArdourGUI'], ['systemctl', '--user', 'restart', 'pipewire', 'pipewire-pulse'], ['ardour6', '-n', 'productive-pipewire']]
            if isinstance(self.command[0], (list)):
              [process(i, False) for i in self.command]
            else:
              # e.g.: ['pkill', 'ArdourGUI']
              process(self.command, False)
          else:
            # e.g.: 'pkill ArdourGUI'
            process(self.command, False)
        self.on('click', click)

      if self.image:
        self.text = ''
        tmp = svg_element(self.image)
        if tmp is not None:
          self.add(tmp)

      elif self.icon:
        self.inner_html = f"<i class='fa-2x {self.icon}'><i>"

class ButtonSound(Div):
  div = None
  name = None
  description = None
  volume = None
  decrease_icon = ''
  decrease_image = ''
  increase_icon = ''
  increase_image = ''
  mute_icon = ''
  mute_image = ''

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.classes = "grid-rows-2"
    self.div = Div(classes="flex")

    if self.decrease_image:
      tmp = svg_element(self.decrease_image)
      if tmp is not None:
        Button(click=self.decrease, a=self.div).add(tmp)
    elif self.decrease_icon:
      Button(inner_html=f"<i class='fa-2x {self.decrease_icon}'><i>",
             click=self.decrease, a=self.div)
    else:
      Button(inner_html='- 5%', click=self.decrease, a=self.div)

    if self.increase_image:
      tmp = svg_element(self.increase_image)
      if tmp is not None:
        Button(click=self.increase, a=self.div).add(tmp)
    elif self.increase_icon:
      Button(inner_html=f"<i class='fa-2x {self.increase_icon}'><i>",
             click=self.increase, a=self.div)
    else:
      Button(inner_html='+ 5%', click=self.increase, a=self.div)

    if self.mute_image:
      tmp = svg_element(self.mute_image)
      if tmp is not None:
        Button(click=self.mute, a=self.div).add(tmp)
    elif self.mute_icon:
      Button(inner_html=f"<i class='fa-2x {self.mute_icon}'><i>",
             click=self.mute, a=self.div)
    else:
      Button(inner_html='toggle mute', click=self.mute, a=self.div)

    self.add(self.div)
    self.volume = Div(text=f"{self.description}: {volume(self.name)}",
                      classes="text-gray-600 text-center -mt-2", a=self)

  async def decrease(self, msg):
    self.volume.text = f'{self.description}: {volume_decrease(self.name)}'

  async def increase(self, msg):
    self.volume.text = f'{self.description}: {volume_increase(self.name)}'

  async def mute(self, msg):
    self.volume.text = f'{self.description}: {volume_mute(self.name)}'

async def reload(self, msg):
  await msg.page.reload()

async def reload_all_instances(self, msg):
  "Reload all browser tabs that the page is rendered on"
  for page in WebPage.instances.values():
    if page.page_type == 'main':
      await page.reload()

async def kill_gui(self, msg):
  await process("pkill controldeck-gui")

def ishexcolor(code):
  return bool(search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', code))

@SetRoute('/')
def application(request):
  wp = WebPage(title=APP_NAME, body_classes="bg-gray-900")
  wp.page_type = 'main'
  wp.head_html = '<meta name="viewport" content="width=device-width, initial-scale=1">'

  menu = Div(classes="fixed bottom-0 right-0 p-1 grid grid-col-1 select-none text-gray-500", a=wp)
  I(classes="w-10 h-10 w-1 fa-2x fa-fw fas fa-redo-alt", click=reload, a=menu)
  if "gui" in request.query_params:
    I(classes="w-10 h-10 w-1 fa-2x fa-fw fas fa-window-close", click=kill_gui, a=menu)

  config = config_load()
  volume_dict = {}
  button_dict = {}
  for i in config.sections():
    iname = None
    # volume buttons
    iname = search("^([0-9]*.?)volume", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      tmp = [{'description': i[iname.end(0)+1:],
              'color-bg': config.get(i, 'color-bg', fallback=''),
              'color-fg': config.get(i, 'color-fg', fallback=''),
              'name': config.get(i, 'name', fallback=None),
              'decrease-icon': config.get('default', 'volume-decrease-icon', fallback=''),
              'decrease-image': config.get('default', 'volume-decrease-image', fallback=''),
              'increase-icon': config.get('default', 'volume-increase-icon', fallback=''),
              'increase-image': config.get('default', 'volume-increase-image', fallback=''),
              'mute-icon': config.get('default', 'volume-mute-icon', fallback=''),
              'mute-image': config.get('default', 'volume-mute-image', fallback='')}]
      try:
        volume_dict[id] += tmp
      except KeyError:
        volume_dict[id] = tmp
    # button or empty
    iname = search("^([0-9]*.?)(button|empty)", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      tmp = [{'type': iname.group(2), 'text': i[iname.end(0)+1:],
              'color-bg': config.get(i, 'color-bg', fallback=''),
              'color-fg': config.get(i, 'color-fg', fallback=''),
              'command': config.get(i, 'command', fallback=None),
              'icon': config.get(i, 'icon', fallback=''),
              'image': config.get(i, 'image', fallback='')}]
      try:
        button_dict[id] += tmp
      except KeyError:
        button_dict[id] = tmp
  var_prefix = "_div"
  for i in volume_dict:
    var = var_prefix+i
    for j in volume_dict[i]:
      if var not in vars():
        vars()[var] = Div(classes="flex flex-wrap", a=wp)
      color_bg = f"background-color:{j['color-bg']};" if ishexcolor(j['color-bg']) else ''
      color_fg = f"color:{j['color-fg']};" if ishexcolor(j['color-fg']) else ''
      ButtonSound(name=j['name'], description=j['description'],
                  color_bg=j['color-bg'], color_fg=j['color-fg'],
                  decrease_icon=j['decrease-icon'], decrease_image=j['decrease-image'],
                  increase_icon=j['increase-icon'], increase_image=j['increase-image'],
                  mute_icon=j['mute-icon'], mute_image=j['mute-image'],
                  a=eval(var))
  for i in button_dict:
    var = var_prefix+i
    for j in button_dict[i]:
      if var not in vars():
        vars()[var] = Div(classes="flex flex-wrap", a=wp)
      Button(text=j['text'], btype=j['type'], command=j['command'],
             color_bg=j['color-bg'], color_fg=j['color-fg'],
             icon=j['icon'], image=j['image'], a=eval(var))

  if not wp.components:
    # config not found or empty, therefore insert an empty div to not get an error
    Div(text="add elements in controldeck.conf", classes="flex flex-wrap", a=wp)

  return wp

def main():
  justpy(host="0.0.0.0")

if __name__ == '__main__':
  sys.exit(main())
