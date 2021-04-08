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

def process_shell(command):
  print(command)
  # string works only with shell
  if isinstance(command, (list)):
    # e.g.: [['pkill', 'ArdourGUI'], ['systemctl', '--user', 'restart', 'pipewire', 'pipewire-pulse'], ['ardour6', '-n', 'productive-pipewire']]
    if isinstance(command[0], (list)):
      [process(i, False) for i in command]
    else:
      # e.g.: ['pkill', 'ArdourGUI']
      process(command, False)
  else:
    # e.g.: 'pkill ArdourGUI'
    process(command, False)

def volume(name):
  result = process(f'pamixer --sink "{name}" --get-volume-human')
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
  result = process(f'pamixer --sink "{name}" --get-volume-human --decrease 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-volume "{name}" -5%')
    #process(f'pactl set-sink-volume "{name}" -5db')
    result = volume(name)
  return result

def volume_increase(name):
  result = process(f'pamixer --sink "{name}" --get-volume-human --increase 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-volume "{name}" +5%')
    #process(f'pactl set-sink-volume "{name}" +5db')
    result = volume(name)
  return result

def volume_mute(name):
  result = process(f'pamixer --sink "{name}" --get-volume-human --toggle-mute')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-sink-mute "{name}" toggle')
    result = volume(name)
  return result

def source_volume(name):
  result = process(f'pamixer --source "{name}" --get-volume-human')
  if search("The source doesn't exit", result):
    result = "--"
  elif search("pamixer: command not found", result) is not None:
    n = process(r"pactl list sources short | awk '{print $2}'").split()
    v = process(r"pactl list sources | grep '^[[:space:]]Volume:' | sed -e 's,.* \([0-9][0-9]*\)%.*,\1,'").split()
    if name in n:
      result = v[n.index(name)] + '%'
    else:
      result = '--'
  return result

def source_volume_decrease(name):
  result = process(f'pamixer --source "{name}" --get-volume-human --decrease 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-source-volume "{name}" -5%')
    #process(f'pactl set-source-volume "{name}" -5db')
    result = volume(name)
  return result

def source_volume_increase(name):
  result = process(f'pamixer --source "{name}" --get-volume-human --increase 5')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-source-volume "{name}" +5%')
    #process(f'pactl set-source-volume "{name}" +5db')
    result = volume(name)
  return result

def source_volume_mute(name):
  result = process(f'pamixer --source "{name}" --get-volume-human --toggle-mute')
  if search("pamixer: command not found", result) is not None:
    process(f'pactl set-source-mute "{name}" toggle')
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
  text = ''
  text_normal = ''
  text_alt = ''
  btype = None
  command = None
  command_alt = None
  color_bg = ''
  color_fg = ''
  icon = ''
  icon_alt = ''
  image = ''
  image_alt = ''
  image_element = None
  image_alt_element = None
  state = ''
  state_pattern = ''
  state_pattern_alt = ''
  state_command = ''
  state_command_alt = ''
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.text_normal = str(self.text)
    if self.btype == 'empty':
      self.classes = "w-20 h-20 m-2 p-1 flex select-none"
      self.text = ''

    else:
      self.classes = "bg-gray-800 hover:bg-gray-700 text-gray-500 w-20 h-20 m-2 p-1 rounded-lg font-bold flex items-center text-center justify-center select-none"

      self.style = f"background-color:{self.color_bg};" if ishexcolor(self.color_bg) else ''
      self.style += f"color:{self.color_fg};" if ishexcolor(self.color_fg) else ''

      if self.command is not None:
        def click(self, msg):
          self.state = process(self.state_command)
          if search(self.state_pattern, self.state):
            if self.command_alt is None:
              process_shell(self.command)
            else:
              process_shell(self.command_alt)
            if self.image_alt:
              self.components[0] = self.image_alt_element
            elif self.icon_alt:
              self.inner_html = f"<i class='fa-2x {self.icon_alt}'><i>"
            elif self.text_alt:
              self.text = self.text_alt
          else:
            process_shell(self.command)
            if self.image:
              self.components[0] = self.image_element
            elif self.icon:
              self.inner_html = f"<i class='fa-2x {self.icon}'><i>"
            else:
              self.text = self.text_normal
        self.on('click', click)

      self.state = process(self.state_command)
      self.image_element = svg_element(self.image)
      self.image_alt_element = svg_element(self.image_alt)
      if self.image and self.image_element is not None:
        self.text = ''
        if self.image_alt and not search(self.state_pattern, self.state):
          self.add(self.image_alt_element)
        else:
          self.add(self.image_element)

      elif self.icon:
        if self.icon_alt and not search(self.state_pattern, self.state):
          self.inner_html = f"<i class='fa-2x {self.icon_alt}'><i>"
        else:
          self.inner_html = f"<i class='fa-2x {self.icon}'><i>"

      else:
        if self.text_alt and not search(self.state_pattern, self.state):
          self.text = self.text_alt
        else:
          self.text = self.text_normal

class ButtonSound(Div):
  div = None
  btype = None
  name = None
  description = None
  volume = None
  decrease_icon = ''
  decrease_image = ''
  increase_icon = ''
  increase_image = ''
  mute_icon = ''
  mute_icon_alt = ''
  mute_image = ''
  mute_image_alt = ''
  bmute = None

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.classes = "grid-rows-2"
    self.div = Div(classes="flex")

    if self.decrease_image:
      tmp = svg_element(self.decrease_image)
      if tmp is not None:
        Button(click=self.decrease, a=self.div).add(tmp)
    elif self.decrease_icon:
      Button(icon = self.decrease_icon, click=self.decrease, a=self.div)
    else:
      Button(inner_html='- 5%', click=self.decrease, a=self.div)

    if self.increase_image:
      tmp = svg_element(self.increase_image)
      if tmp is not None:
        Button(click=self.increase, a=self.div).add(tmp)
    elif self.increase_icon:
      Button(icon=self.increase_icon,
             click=self.increase, a=self.div)
    else:
      Button(inner_html='+ 5%', click=self.increase, a=self.div)

    if self.mute_image and self.mute_image is not None:
      self.bmute = Button(click=self.mute,
                          image=self.mute_image,
                          image_alt=self.mute_image_alt,
                          a=self.div)
    else:
      self.bmute = Button(text='mute',
                          icon=self.mute_icon,
                          icon_alt=self.mute_icon_alt,
                          click=self.mute, a=self.div)
    if self.btype == 'mic':
      self.bmute.state = f'{source_volume(self.name)}'
    else:
      self.bmute.state = f'{volume(self.name)}'

    if self.bmute.state == 'muted':
      if self.bmute.image_alt_element:
        self.bmute.components[0] = self.bmute.image_alt_element
      elif self.mute_icon:
        self.bmute.inner_html = f"<i class='fa-2x {self.bmute.icon_alt}'><i>"
      else:
        self.bmute.text = 'unmute'

    self.add(self.div)
    if self.btype == 'mic':
      self.volume = Div(text=f"{self.description}: {source_volume(self.name)}",
                        classes="text-gray-600 text-center -mt-2", a=self)
    else:
      self.volume = Div(text=f"{self.description}: {volume(self.name)}",
                        classes="text-gray-600 text-center -mt-2", a=self)

  async def decrease(self, msg):
    if self.btype == 'mic':
      self.volume.text = f'{self.description}: {source_volume_decrease(self.name)}'
    else:
      self.volume.text = f'{self.description}: {volume_decrease(self.name)}'

  async def increase(self, msg):
    if self.btype == 'mic':
      self.volume.text = f'{self.description}: {source_volume_increase(self.name)}'
    else:
      self.volume.text = f'{self.description}: {volume_increase(self.name)}'

  async def mute(self, msg):
    if self.btype == 'mic':
      self.volume.text = f'{self.description}: {source_volume_mute(self.name)}'
      self.bmute.state = f'{source_volume(self.name)}'
    else:
      self.volume.text = f'{self.description}: {volume_mute(self.name)}'
      self.bmute.state = f'{volume(self.name)}'
    if self.bmute.state == 'muted':
      if self.bmute.image_alt_element:
        self.bmute.components[0] = self.bmute.image_alt_element
      elif self.mute_icon_alt:
        self.bmute.inner_html = f"<i class='fa-2x {self.bmute.icon_alt}'><i>"
      else:
        self.bmute.text = 'unmute'
    else:
      if self.bmute.image_element:
        self.bmute.components[0] = self.bmute.image_element
      elif self.mute_icon:
        if self.mute_icon:
          self.bmute.inner_html = f"<i class='fa-2x {self.bmute.icon}'><i>"
      else:
        self.bmute.text = 'mute'

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
    iname = search("^([0-9]*.?)(volume|mic)", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      if iname.group(2) == 'mic':
        tmp = [{'type': iname.group(2), 'description': i[iname.end(0)+1:],
                'color-bg': config.get(i, 'color-bg', fallback=''),
                'color-fg': config.get(i, 'color-fg', fallback=''),
                'name': config.get(i, 'name', fallback=None),
                'decrease-icon': config.get('default', 'mic-decrease-icon', fallback=''),
                'decrease-image': config.get('default', 'mic-decrease-image', fallback=''),
                'increase-icon': config.get('default', 'mic-increase-icon', fallback=''),
                'increase-image': config.get('default', 'mic-increase-image', fallback=''),
                'mute-icon': config.get('default', 'mic-mute-icon', fallback=''),
                'mute-icon-alt': config.get('default', 'mic-mute-icon-alt', fallback=''),
                'mute-image': config.get('default', 'mic-mute-image', fallback=''),
                'mute-image-alt': config.get('default', 'mic-mute-image-alt', fallback='')}]
      else:
        tmp = [{'type': iname.group(2), 'description': i[iname.end(0)+1:],
                'color-bg': config.get(i, 'color-bg', fallback=''),
                'color-fg': config.get(i, 'color-fg', fallback=''),
                'name': config.get(i, 'name', fallback=None),
                'decrease-icon': config.get('default', 'volume-decrease-icon', fallback=''),
                'decrease-image': config.get('default', 'volume-decrease-image', fallback=''),
                'increase-icon': config.get('default', 'volume-increase-icon', fallback=''),
                'increase-image': config.get('default', 'volume-increase-image', fallback=''),
                'mute-icon': config.get('default', 'volume-mute-icon', fallback=''),
                'mute-icon-alt': config.get('default', 'volume-mute-icon-alt', fallback=''),
                'mute-image': config.get('default', 'volume-mute-image', fallback=''),
                'mute-image-alt': config.get('default', 'volume-mute-image-alt', fallback='')}]
      try:
        volume_dict[id] += tmp
      except KeyError:
        volume_dict[id] = tmp
    # button or empty
    iname = search("^([0-9]*.?)(button|empty)", i, flags=IGNORECASE)
    if iname is not None:
      id = iname.group(1)[:-1]  # remove dot
      tmp = [{'type': iname.group(2), 'text': i[iname.end(0)+1:],
              'text-alt': config.get(i, 'text-alt', fallback=''),
              'color-bg': config.get(i, 'color-bg', fallback=''),
              'color-fg': config.get(i, 'color-fg', fallback=''),
              'command': config.get(i, 'command', fallback=None),
              'command-alt': config.get(i, 'command-alt', fallback=None),
              'state': config.get(i, 'state', fallback=''),
              'state-alt': config.get(i, 'state-alt', fallback=''),
              'state-command': config.get(i, 'state-command', fallback=''),
              'state-command-alt': config.get(i, 'state-command-alt', fallback=''),
              'icon': config.get(i, 'icon', fallback=''),
              'icon-alt': config.get(i, 'icon-alt', fallback=''),
              'image': config.get(i, 'image', fallback=''),
              'image-alt': config.get(i, 'image-alt', fallback='')}]
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
      ButtonSound(name=j['name'], description=j['description'], btype=j['type'],
                  color_bg=j['color-bg'], color_fg=j['color-fg'],
                  decrease_icon=j['decrease-icon'], decrease_image=j['decrease-image'],
                  increase_icon=j['increase-icon'], increase_image=j['increase-image'],
                  mute_icon=j['mute-icon'], mute_image=j['mute-image'],
                  mute_icon_alt=j['mute-icon-alt'], mute_image_alt=j['mute-image-alt'],
                  a=eval(var))
  for i in button_dict:
    var = var_prefix+i
    for j in button_dict[i]:
      if var not in vars():
        vars()[var] = Div(classes="flex flex-wrap", a=wp)
      Button(text=j['text'], text_alt=j['text-alt'], btype=j['type'],
             command=j['command'], command_alt=j['command-alt'],
             color_bg=j['color-bg'], color_fg=j['color-fg'],
             state_pattern=j['state'], state_pattern_alt=j['state-alt'],
             state_command=j['state-command'],
             state_command_alt=j['state-command-alt'],
             icon=j['icon'], icon_alt=j['icon-alt'],
             image=j['image'], image_alt=j['image-alt'], a=eval(var))

  if not wp.components:
    # config not found or empty, therefore insert an empty div to not get an error
    Div(text="add elements in controldeck.conf", classes="flex flex-wrap", a=wp)

  return wp

def main():
  justpy(host="0.0.0.0")

if __name__ == '__main__':
  sys.exit(main())
