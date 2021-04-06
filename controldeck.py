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

class Button(Div):
  command = None
  empty = None
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    if self.empty:
      self.classes = "w-20 h-20 m-2 p-1 flex select-none"
    else:
      self.classes = "bg-gray-800 hover:bg-gray-700 text-gray-500 w-20 h-20 m-2 p-1 rounded-lg font-bold flex items-center text-center justify-center select-none"
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

class ButtonSound(Div):
  div = None
  name = None
  description = None
  volume = None
  button_style = None

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.classes = "grid-rows-2"
    self.div = Div(classes="flex")
    Button(inner_html=f'{self.description}<br> - 5%', style=self.button_style, click=self.decrease, a=self.div)
    Button(inner_html=f'{self.description}<br> + 5%', style=self.button_style, click=self.increase, a=self.div)
    self.add(self.div)
    self.volume = Div(text=f"Volume: {volume(self.name)}%", classes="text-gray-600 text-center -mt-2", a=self)

  async def decrease(self, msg):
    self.volume.text = f'Volume: {volume_decrease(self.name)}%'

  async def increase(self, msg):
    self.volume.text = f'Volume: {volume_increase(self.name)}%'

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

  # div = Div(classes="flex flex-wrap", a=wp)
  # ButtonSound(name="Stream_sink", description="Stream sink", a=div)
  # div2 = Div(classes="flex flex-wrap", a=wp)
  # Button(text="Sleep", command='systemctl suspend', a=div2)

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
              'name': config.get(i, 'name', fallback=None)}]
      try:
        volume_dict[id] += tmp
      except KeyError:
        volume_dict[id] = tmp
    # button
    iname = search("^([0-9]*.?)button", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      tmp = [{'type': 'normal', 'text': i[iname.end(0)+1:],
              'color-bg': config.get(i, 'color-bg', fallback=''),
              'color-fg': config.get(i, 'color-fg', fallback=''),
              'command': config.get(i, 'command', fallback=None),
              'icon': config.get(i, 'icon', fallback=''),
              'icon-image': config.get(i, 'icon-image', fallback='')}]
      try:
        button_dict[id] += tmp
      except KeyError:
        button_dict[id] = tmp
    # empty
    iname = search("^([0-9]*.?)empty", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      tmp = [{'type': 'empty', 'text': i[iname.end(0)+1:]}]
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
                  button_style = color_bg + color_fg, a=eval(var))
  for i in button_dict:
    var = var_prefix+i
    for j in button_dict[i]:
      if j['type'] == 'normal':
        color_bg = f"background-color:{j['color-bg']};" if ishexcolor(j['color-bg']) else ''
        color_fg = f"color:{j['color-fg']};" if ishexcolor(j['color-fg']) else ''
      if var not in vars():
        vars()[var] = Div(classes="flex flex-wrap", a=wp)
      if j['type'] == 'empty':
        Button(empty=True, a=eval(var))
      elif 'icon-image' in j and j['icon-image'] != '':
        svg = ''
        if path.isfile(path.expanduser(j['icon-image'])):
          try:
            with open(path.expanduser(j['icon-image'])) as f:
              svg = f.read()
          except Exception as e:
            print(f"{e}")
        try:  # svg with custom tags, as inkscape is using, cannot be interpreted
          tmp = Button(style = color_bg, command=j['command'], a=eval(var))
          tmp_svg = parse_html(svg)
          #print(dir(tmp_svg)) # add_attribute
          #print(tmp2.attributes)
          # set width and height to viewBox to update width and height for scaling
          w = tmp_svg.width if hasattr(tmp_svg, 'width') else "64"
          h = tmp_svg.height if hasattr(tmp_svg, 'height') else "64"
          vb = tmp_svg.viewBox if hasattr(tmp_svg, 'viewBox') else '0 0 ' + w + ' ' + h
          tmp_svg.viewBox = vb
          tmp_svg.width = 64
          tmp_svg.height = 64
          tmp += tmp_svg
        except Exception as e:
          print(f"[Error SVG]: {e}")
      elif 'icon' in j and j['icon'] != '':
        Button(inner_html=f"<i class='fa-2x {j['icon']}'><i>",
               style = color_bg + color_fg,
               command=j['command'], a=eval(var))
      else:
        Button(text=j['text'],
               style = color_bg + color_fg,
               command=j['command'], a=eval(var))

  if not wp.components:
    # config not found or empty, therefore insert an empty div to not get an error
    Div(text="add elements in controldeck.conf", classes="flex flex-wrap", a=wp)

  return wp

def main():
  justpy(host="0.0.0.0")

if __name__ == '__main__':
  sys.exit(main())
