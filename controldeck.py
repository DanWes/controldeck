#!/usr/bin/env python
"""
HTML style powered by Quasar

NOTE: currently buttons only updated on page reload
"""

import sys
from os import getcwd, path, sep, makedirs
import shutil
import shlex
from subprocess import Popen, PIPE, STDOUT
from configparser import ConfigParser
import re
import json
import time
import datetime
import argparse
from addict import Dict  # also used in justpy

APP_NAME = "ControlDeck"
COLOR_PRIME = "blue-grey-8"        # "blue-grey-7" "blue-grey-8" 'light-blue-9'
COLOR_PRIME_TEXT = "blue-grey-7"
COLOR_SELECT = "light-blue-9"
DEBUG = False

CONFIG_DIR = path.join(path.expanduser("~"), '.config', APP_NAME.lower())
CONFIG_FILE_NAME = APP_NAME.lower() + '.conf'
CONFIG_FILE = path.join(CONFIG_DIR, CONFIG_FILE_NAME)
CACHE_DIR = path.join(path.expanduser('~'), '.cache', APP_NAME.lower())
STATIC_DIR = path.join(CACHE_DIR, 'static')

# justpy config overwrite
# NEEDS to be done BEFORE loading justpy but AFTER jpcore.justpy_config.JpConfig
# jpcore.justpy_config.JpConfig loads defaults into jpcore.jpconfig
# justpy creates app mounts
from jpcore.justpy_config import JpConfig
import jpcore.jpconfig
jpcore.jpconfig.STATIC_DIRECTORY = STATIC_DIR

from justpy import (
  app,
  Div,
  I,
  P,
  QuasarPage,
  QBadge,
  QBar,
  QBtn,
  QBtnGroup,
  QBtnToggle,
  QCard,
  QCardSection,
  QDialog,
  QDiv,
  QEditor,
  QHeader,
  QIcon,
  QInput,
  QItem,
  QItemLabel,
  QItemSection,
  QLayout,
  QNotify,
  QPage,
  QPageContainer,
  QSeparator,
  QSlider,
  QSpace,
  QTab,
  QTabs,
  QTabPanel,
  QTabPanels,
  QToolbar,
  QTooltip,
  SetRoute,
  ToggleDarkModeBtn,
  WebPage,
  parse_html,
  run_task,
  justpy
)

def tohtml(text):
  return text.replace("\n", "<br>")

def process(command_line, shell=False, output=True, stdout=PIPE, stderr=STDOUT):
  try:
    # with shell=True args can be a string
    # detached process https://stackoverflow.com/a/65900355/992129 start_new_session
    # https://docs.python.org/3/library/subprocess.html#popen-constructor
    # reading the output blocks also the process -> for buttons use output=False
    # maybe https://stackoverflow.com/questions/375427/a-non-blocking-read-on-a-subprocess-pipe-in-python
    # print(command_line)
    if shell:
      # shell mode for 'easy' program strings with pipes
      # e.g. DISPLAY=:0 wmctrl -xl | grep emacs.Emacs && DISPLAY=:0 wmctrl -xa emacs.Emacs || DISPLAY=:0 emacs &
      args = command_line
    else:
      args = shlex.split(command_line)
    # print(args)
    result = Popen(args, stdout=stdout, stderr=stderr, shell=shell, start_new_session=True)
    if output:
      res = result.stdout.read().decode("utf-8").rstrip()
      result.kill()  # does not help to unblock
      # print(res)
      return res
  except Exception as e:
    print(f"{e} failed!")

def config_load(conf=''):
  config = ConfigParser(strict=False)
  # fist check if file is given
  if conf:
    config_file = conf
  else:
    # check if config file is located at the script's location
    config_file = path.join(path.dirname(path.realpath(__file__)), CONFIG_FILE_NAME)  # realpath; resolve symlink
    if not path.exists(config_file):
      # if not, use the file inside .config
      makedirs(CONFIG_DIR, exist_ok=True)
      config_file = CONFIG_FILE
  try:
    config.read(path.expanduser(config_file))
  except Exception as e:
    print(f"{e}")
  #print(config.sections())
  return config

# TODO: colors definable in config
class Label(QDiv):
  """
  Args:
    **kwargs:
      - wtype: if 'empty' then: empty slot, for horizontal arrangement, text is
        ignored, no bg color etc.
  """
  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.style = "width: 90px;"
    self.style += "min-height: 70px;"
    if self.wtype != 'empty':
      self.classes = f"q-pa-sm text-blue-grey-5 text-bold text-center bg-blue-grey-10"
      # bg-light-blue-10
      #self.style += "font-size: 14px;"
      self.style += "line-height: 1em;"
      #self.style += "border-radius: 7px;"
      self.classes += " q-btn--push"  # border-radius: 7px;
      self.text = self.text.upper()
    #print()
    #print(self)

# TODO: distinguish between non-command and comand inactive stage?
class Button(QBtn):
  """
  Args:
    **kwargs:
      - text: button text in normal state (unpressed)
      - text_alt: button text in active state (pressed)
      - wtype: 'button' (any string atm) for a button
      - command: command to execute on click
      - command_alt: command to execute on click in active state
      - color_bg: background color
      - color_fg: foreground color
      - state_pattern: string defining the normal state (unpressed) [NEDDED?]
      - state_pattern_alt: string defining the alternative state
        (active, pressed)
      - state_command: command to execute to compare with state_pattern*
      - icon: icon in normal state (unpressed)
      - icon_alt: icon in active state
  
  Usage:
    Button(text, text_alt, wtype, command, command_alt,
           color_bg=, color_fg=, state_pattern, state_pattern_alt,
           state_command,
           icon, icon_alt, image, image_alt,
           a)
  """
  def __init__(self, **kwargs):
    self.stack = True
    # self.outline = True         # is set via style, see below
    # self.color = "blue-grey-8"  # is overwritten via text_color
    self.text_color = COLOR_PRIME_TEXT
    self.size = 'md'              # button / font size
    self.push = True
    # self.padding = 'none'       # not working, also not inside init
    self.dense = True

    # default **kwargs
    self.wtype = None             # button or empty
    self.image = ''               # used for files like svg and png
                                  # e.g. /usr/share/icons/breeze-dark/actions/24/media-playback-stop.svg
    self.command = ''             # command to run on click
    self.state = ''               # output of the state check command
    self.state_command = ''       # command to check the unclicked state
    super().__init__(**kwargs)

    self.style = "width: 90px;"
    self.style += "min-height: 77px;"   # image + 2 text lines
    self.style += "border: 1px solid var(--c-blue-grey-8);"  # #455a64 blue-grey-8
    self.style += "line-height: 1em;"

    # if DEBUG:
    #   print(f'[DEBUG] button: {self.text}; image: {self.image}; exists: {path.exists(self.image)}')
    if self.image and path.exists(self.image):
      # copy image files into the static folder
      basename = path.basename(self.image)
        # e.g. media-playback-stop.svg
      staticfile = path.join(STATIC_DIR, basename)
        # e.g. <user-home>/.cache/controldeck/static/media-playback-stop.svg
      if not path.exists(staticfile):
        shutil.copy2(self.image, staticfile)
        if DEBUG:
          print(f'[DEBUG] copy {self.image} to {staticfile}')
      self.icon = f"img:/static/{basename}"
        # e.g. img:/static/media-playback-stop.svg
      # <q-icon name="img:data:image/svg+xml;charset=utf8,<svg xmlns='http://www.w3.org/2000/svg' height='140' width='500'><ellipse cx='200' cy='80' rx='100' ry='50' style='fill:yellow;stroke:purple;stroke-width:2' /></svg>" />
      # <q-btn icon="img:data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==" ... />
      # if DEBUG:
      #   print(f'[DEBUG] button: {self.text}; icon: {staticfile}; exists: {path.exists(self.image)}')
      #   print(f'[DEBUG] button: {self.text}; icon: {self.icon}')

    if self.command != '':
      self.update_state()
      tt = f"command: {self.command.strip()}"
      if self.state_command:
        tt += f"\nstate: {self.state}"
      QTooltip(a=self, text=tt, delay=500) # setting style white-space:pre does not work, see wp.css below
      def click(self, msg):
        if self.command != '':
          self.update_state()
          if DEBUG:
            print(f"[btn] command: {self.command}")
          process(self.command, shell=True, output=False)  # output=True freezes controldeck until process finished (until e.g. an emacs button is closed)
      self.on('click', click)

  def is_state_alt(self):
    return self.state == self.state_pattern_alt

  def update_state(self):
    if self.state_command != '':
      self.state = process(self.state_command, shell=True)
      if DEBUG:
        print("[btn] update btn state")
        print(f"[btn] text: {self.text}")
        print(f"[btn] state (before click): {self.state}")
        print(f"[btn] state_command: {self.state_command}")
        print(f"[btn] state_pattern: {self.state_pattern}")
        print(f"[btn] state_pattern_alt: {self.state_pattern_alt}")
        print(f"[btn] is_state_alt: {self.is_state_alt()}")
      if self.is_state_alt():
        # self.style += "border: 1px solid green;"
        # self.style += "border-bottom: 1px solid green;"
        self.style += "border: 1px solid var(--c-light-blue-9);"
        # self.style += "border-bottom: 1px solid var(--c-light-blue);"


class Slider(Div):
  def __init__(self, **kwargs):
    # instance vars
    self.slider = None        # for handle methods to access slider
    self.toggled = False

    # default **kwargs
    self.wtype = 'slider'     # slider (atm the only option)
    self.name = ''            # id name
    self.description = ''     # badge name

    super().__init__(**kwargs)
    self.style = "width:286px;"  # three buttons and the two spaces

    self.cmdl_toggle = ''     # cmd for the button left
    self.cmdl_value = ''      # cmd for the slider value

    # local vars
    badge_name = self.description if self.description else self.name
    value = 0

    badge = QBadge(
      text=badge_name,
      outline=True,
      color=COLOR_PRIME_TEXT,
      style="max-width:286px;",  # 3*90 + 2*8
      classes="ellipsis",
      a=self,
    )
    tt = QTooltip(
      a=badge, text=badge_name, delay=500, anchor='center left',
      offset=[0, 14], transition_show='jump-right', transition_hide='jump-left')
    tt.self='center left'
    item = QItem(
      a=self,
      dense=True,  # dense: less spacing: vertical little higher
    )
    item_section = QItemSection(
      side=True,     # side=True unstreched btn
      a=item,
    )

    item_section2 = QItemSection(a=item)
    def handle_slider(widget_self, msg):
      # process(cmdl_value.format(name=self.name,value=msg.value), shell=True, output=False)
      pass
    self.slider = QSlider(
      value=value,
      min=0,
      max=100,
      step=5,
      label=True,
      a=item_section2,
      input=handle_slider,
      color=COLOR_SELECT,
      style="opacity: 0.6 !important;" if self.is_toggled() else "opacity: unset !important;",
    )

  # TODO: toggle?
  def is_toggled(self):
    self.toggled = not self.toggled
    return self.toggled

class Volume(Div):
  # class variables
  data = {}                   # pulseaudio info for all sinks
  icon_muted = 'volume_mute'  # default icon for muted state, 'volume_off' better for disabled or not found?
  icon_unmuted = 'volume_up'  # default icon for unmuted state
  last_update = 0             # used for updates. init set to zero so the 1st diff is large to go into update at startup

  def __init__(self, **kwargs):
    # instance vars
    self.slider = None        # for handle methods to access slider

    # default **kwargs
    self.wtype = 'sink'       # sink (loudspeaker) or sink-input (app output)
    self.name = ''            # pulseaudio sink name
    self.description = ''     # badge name

    super().__init__(**kwargs)
    self.style = "width:286px;"  # three buttons and the two spaces
    self.update_state()       # get self.pa_state

    if self.pa_state:
      if self.wtype == 'sink':
        cmdl_toggle = 'pactl set-sink-mute {name} toggle'
        cmdl_value = 'pactl set-sink-volume {name} {value}%'
      elif self.wtype == 'sink-input':
        cmdl_toggle = 'pactl set-sink-input-mute {name} toggle'
        cmdl_value = 'pactl set-sink-input-volume {name} {value}%'
        app_name = self.pa_state['properties']['application.process.binary'] if 'application.process.binary' in self.pa_state['properties'] else ''
        if app_name == '':
          app_name = self.pa_state['properties']['application.name'] if 'application.name' in self.pa_state['properties'] else ''
        if app_name == '':
          app_name = self.pa_state['properties']['node.name'] if 'node.name' in self.pa_state['properties'] else ''
        self.description = \
          app_name +\
          ': ' +\
          self.pa_state['properties']['media.name']
      # local vars
      badge_name = self.description if self.description else self.name
      volume_level = 0
      if self.pa_state:  # might be empty {} if it is not found
        # pulseaudio 2^16 (65536) volume levels
        if 'front-left' in self.pa_state['volume']:
          volume_level = float(self.pa_state['volume']['front-left']['value_percent'][:-1])  # remove the % sign
        elif 'mono' in self.pa_state['volume']:
          volume_level = float(self.pa_state['volume']['mono']['value_percent'][:-1])  # remove the % sign
        # TODO: ? indicator if stream is stereo or mono ?

      badge = QBadge(
        text=badge_name,
        outline=True,
        color=COLOR_PRIME_TEXT,
        style="max-width:286px;",  # 3*90 + 2*8
        classes="ellipsis",
        a=self,
      )
      tt = QTooltip(
        a=badge, text=badge_name, delay=500, anchor='center left',
        offset=[0, 14], transition_show='jump-right', transition_hide='jump-left')
      tt.self='center left'
      item = QItem(
        a=self,
        dense=True,  # dense: less spacing: vertical little higher
      )
      item_section = QItemSection(
        side=True,     # side=True unstreched btn,
        #avatar=True,  # more spacing than side
        a=item,
      )
      # QIcon(name="volume_up", a=item_section)
      def handle_btn(widget_self, msg):
        # not checking the current state
        process(cmdl_toggle.format(name=self.name), shell=True, output=False)
        if widget_self.icon == self.icon_unmuted:  # switch to mute
          widget_self.icon = self.icon_muted
          self.slider.style = "opacity: 0.6 !important;"
        elif widget_self.icon == self.icon_muted:  # switch to unmute
          widget_self.icon = self.icon_unmuted
          self.slider.style = "opacity: unset !important;"
        # toggle disable state
        # this wont allow to change the volume in a mute state
        # self.slider.disable = not self.slider.disable
      QBtn(
        icon=self.icon_muted if self.is_muted() else self.icon_unmuted,
        dense=True,
        flat=True,
        a=item_section,
        color=COLOR_PRIME_TEXT,
        click=handle_btn,
      )
      item_section2 = QItemSection(a=item)
      def handle_slider(widget_self, msg):
        process(cmdl_value.format(name=self.name,value=msg.value), shell=True, output=False)
      self.slider = QSlider(
        value=volume_level,
        min=0,
        max=100,
        step=5,
        label=True,
        a=item_section2,
        input=handle_slider,
        color=COLOR_SELECT,
        # track_color=COLOR_PRIME,  # not working, see .q-slider__track-container
        # markers=True,
        # marker_labels=True,  # not working?
        # track_size="10px",   # not working, see cs .q-slider__track-container
        # style = "height: 4px;"
        style="opacity: 0.6 !important;" if self.is_muted() else "opacity: unset !important;",
      )

  @classmethod
  def update_states(cls) -> None:
    """
    get pulseaudio state of all sinks and sink-inputs and save it to
    class variable data

    creates and updates
    Volume.data['sinks']
    Volume.data['sink-inputs']
    both might be empty lists but available
    """
    t = time.time()
    dt = t - cls.last_update
    if dt > 1.0: # update only if at least a second passed since last update
      cls.last_update = t

      # wsl not running pulse daemon: Connection failure: Connection refused
      sinks = process('pactl -f json list sinks', shell=True)
      if 'failure' in sinks:
        print("'pactl -f json list sinks' returns: '", sinks, "'")
        # fill (initialize) key 'sinks' and 'sink-inputs' to empty list so not enter KeyError
        cls.data['sinks'] = []
        cls.data['sink-inputs'] = []
      else:
        cls.data['sinks'] = json.loads(sinks)

        sink_inputs = process('pactl -f json list sink-inputs', shell=True, stderr=None)  # stderr might have e.g.: Invalid non-ASCII character: 0xffffffc3
        if 'failure' in sinks:
          print("'pactl -f json list sink-inputs' returns", sink_inputs)
          cls.data['sink-inputs'] = []
        else:
          cls.data['sink-inputs'] = json.loads(sink_inputs)

  def update_state(self) -> None:
    "fills self.pa_state, therefore access info via self.pa_state"
    self.update_states()
    tmp = []
    # filter for the given pa name, empty list if not found
    if self.wtype == 'sink':
      # match pa name with self.name
      tmp = list(filter(lambda item: item['name'] == self.name,
                        Volume.data['sinks']))
    elif self.wtype == 'sink-input':
      # match pa index with self.name
      try:  # for int casting
        tmp = list(filter(lambda item: item['index'] == int(self.name),
                          Volume.data['sink-inputs']))
      except:
        pass
    self.pa_state = tmp[0] if tmp else {}

  def is_muted(self):
    return self.pa_state['mute']

class VolumeGroup():
  def __init__(self, **kwargs):
    a = kwargs.pop('a', None)  # add Volume widgets to the specified component
    Volume.update_states()
    for i in Volume.data['sink-inputs']:
      Volume(a=a, name=i['index'], wtype='sink-input')

async def reload(self, msg):
  await msg.page.reload()

async def reload_all_instances(self, msg):
  "Reload all browser tabs that the page is rendered on"
  for page in WebPage.instances.values():
    if page.page_type == 'main':
      await page.reload()

async def kill_gui(self, msg):
  if 'pid' in msg.page.request.query_params:
    pid = msg.page.request.query_params.get('pid')
    await process(f"kill {pid}")
  else:
    await process("pkill controldeck-gui")

def ishexcolor(code):
  return bool(re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', code))

def widget_load(config) -> dict:
  """scan for widgets to add (adding below) in the config
  {
    tab-name: {
      section-id: [
        {widget-args}
      ]
    }
  }
  """
  widget_dict = {}
  for i in config.sections():
    iname = None
    #iname = re.search(r"^([0-9]*:?)([0-9]*\.?)(button|empty)", i, flags=re.IGNORECASE)
    iname = re.search(
      r"^([0-9a-z]*:)?([0-9]*\.)?(empty|label|button|slider|sink-inputs|sink|source)",  # sink-inputs BEFORE sink!
      i, flags=re.IGNORECASE)
    if iname is not None:
      tab_name = iname.group(1)[:-1] if iname.group(1) is not None else ''  # remove collon, id is '' if nothing is given
      sec_id = iname.group(2)[:-1] if iname.group(2) is not None else ''  # remove dot, id is '' if nothing is given
      wid_type = iname.group(3)
      wid_name = i[iname.end(0)+1:]  # rest; after last group, can have all chars including . and :
      # print('group   ', iname.group(0))
      # print('tab_id  ', tab_name)
      # print('sec_id  ', sec_id)
      # print('wid_type', wid_type)
      # print('wid_name', wid_name)
      # print('')
      if wid_type == 'empty':
        # TODO: empty using label class, like an alias?
        args = [{'widget-class': 'Empty',
                 'type': wid_type}]
      if wid_type == 'label':
        args = [{'widget-class': Label,
                 'type': wid_type,
                 'text': wid_name}]
      elif wid_type == 'button':
        # button or empty
        args = [{'widget-class': Button,
                 'type': wid_type,
                 'text': wid_name,
                 'text-alt': config.get(i, 'text-alt', fallback=''),
                 'color-bg': config.get(i, 'color-bg', fallback=''),
                 'color-fg': config.get(i, 'color-fg', fallback=''),
                 'command': config.get(i, 'command', fallback=''),
                 'command-alt': config.get(i, 'command-alt', fallback=''),
                 'state': config.get(i, 'state', fallback=''),
                 'state-alt': config.get(i, 'state-alt', fallback=''),
                 'state-command': config.get(i, 'state-command', fallback=''),
                 'icon': config.get(i, 'icon', fallback=''),
                 'icon-alt': config.get(i, 'icon-alt', fallback=''),
                 'image': config.get(i, 'image', fallback=''),
                 'image-alt': config.get(i, 'image-alt', fallback='')}]
      elif wid_type == 'slider':
        # sliders
        args = [{'widget-class': Slider,
                 'type': wid_type,
                 'name': wid_name,
                 'description': config.get(i, 'description', fallback=''),
                 }]
      elif wid_type == 'sink':
        # volume sliders
        args = [{'widget-class': Volume,
                 'type': wid_type,
                 'name': wid_name,
                 'description': config.get(i, 'description', fallback=''),
                 }]
      elif wid_type == 'sink-inputs':
        # multiple volume sliders
        args = [{'widget-class': VolumeGroup,
                 'type': wid_type,
                 }]
      if tab_name not in widget_dict:
        widget_dict.update({tab_name: {}})
      # try:
      #   widget_dict[sec_id] += args
      # except KeyError:
      #   widget_dict[sec_id] = args
      try:
        widget_dict[tab_name][sec_id] += args
      except KeyError:
        widget_dict[tab_name][sec_id] = args
  return widget_dict

@SetRoute('/')
async def application(request):
  """
  Components:
  [QLayout]
  +-[QHeader]
    +-[QBar]
      +-[QBtnToggle] - tabs
      +-[QSpace]
      +-[QBtn] - edit
      +-[ToggleDarkModeBtn]
      +-[QBtn] - fullscreen
      +-[QBtn] - reload
      +-([QBtn]) - close
  +-[QPageContainer]
    +-[QPage]
      +-[QTabPanel]
      +-[QTabPanel]
      +-[QTabPanel]
      +-[QTabPanel]
      +-...
  """
  wp = QuasarPage(
    title=APP_NAME,
    dark=True,
    classes="blue-grey-10",
  )

  # can be accessed via msg.page.request
  wp.request = request
  tab_choice = request.query_params.get('tab', '[all]')  # if tab is not specified default to [all]

  wp.page_type = 'main'
  wp.head_html = """<meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="mobile-web-app-capable" content="yes">"""
  wp.css = """
    .q-icon {
      height: unset;  /* overwrite 1em so unused icons in buttons do not use space */
    }
    .q-btn img.q-icon {  /* for images icons not font icons */
      padding-bottom: 0.1em;  /* some space to the text below */
      font-size: 2.5em !important;  /* increase image size (1.715em) */
    }
    .q-btn i.q-icon {  /* for font icons not image icons */
      padding-bottom: 0.1em;  /* some space to the text below */
    }
    .q-btn-group > .q-btn-item:not(:last-child) {
      border-right: unset !important;
    }
    .q-btn-group {
      border-radius: 7px;
    }

    /* bc/ track_size is not working */
    .q-slider__track-container {
      height: 4px;
      margin-top: -2px;
    }
    /* bc/ track_color is not working */
    .q-slider__track-container {
      background: #455a64 !important;  /* blue-grey-8 */
    }

    .q-tooltip {
      white-space: pre;
    }

    /* COLORS */
    :root {
      --c-blue-grey-8: #455a64;  /* blue-grey-8 */
      --c-light-blue-9: #0277bd;  /* light-blue-9 */
    }
    .border-c-blue-grey-8 {
      border: 1px solid var(--c-blue-grey-8) !important;
    }
  """

  # quasar version installed v1.9.14
  # v1 bc/ v2 uses vue v3 components but justpy only has vue v2 components
  # https://github.com/justpy-org/justpy/issues/460
  # wp.head_html += '<link href="/static/quasar.prod.css" rel="stylesheet" type="text/css">'
  # script_html = """
  # <script src="/static/quasar.umd.prod.js"></script>
  # """
  # will be added at the top of body
  # wp.body_html = script_html

  # scan for widgets to add (adding below) in the config
  config = config_load()
  widget_dict = widget_load(config)
  tab_names = ['[all]'] + list(widget_dict.keys())  # an all tab + all defined tab in the config

  layout = QLayout(view="lHh lpr lFf",
                   #container=True,
                   a=wp, name='layout')
  header = QHeader(elevated=True, a=layout)
  #toolbar = QToolbar(a=header)  # height 50
  toolbar = QBar(
    a=header,
    classes='bg-'+COLOR_PRIME,
  )       # height 32, dense 24  'bg-light-blue-10'

  # toolbar_tabs = QTabs(
  #   a=toolbar, outside_arrows=True, mobile_arrows=True,
  #   style='width:200px',
  # )
  # QTab(a=toolbar_tabs, label="test1")
  # QTab(a=toolbar_tabs, label="test2")
  # QTab(a=toolbar_tabs, label="test3")
  # QTab(a=toolbar_tabs, label="test4")
  # QTab(a=toolbar_tabs, label="test5")
  # QTab(a=toolbar_tabs, label="test6")
  async def tab_button_change(self, msg):
    #print(msg)
    #print(msg['target'])
    #print(self.value)
    # tab_panel is defined below
    if self.value == '[all]':
      for tab_name in tab_panel.keys():
        if tab_panel[tab_name].has_class('hidden'):
          tab_panel[tab_name].remove_class('hidden')
    else:
      for tab_name in tab_panel.keys():
        if not tab_panel[tab_name].has_class('hidden'):
          tab_panel[tab_name].set_class('hidden')
      if self.value in tab_panel:
        tab_panel[self.value].remove_class('hidden')
    # change the address field in the browser using pushState (to be able to go 'back') (other would be replaceState)
    await msg.page.run_javascript(f"window.history.pushState('', '', '/?tab={self.value}')")
  tab_btns = QBtnToggle(  # 'deep-purple-9'
    toggle_color=COLOR_SELECT, dense=False, flat=False, push=False,
    glossy=False, a=toolbar, input=tab_button_change, value=tab_choice,
    classes='q-ma-md', unelevated=True)
  tab_btns.remove_class('q-ma-md')
  tab_btns.style = 'height:100%;'  # buttons full height
  tab_btns.style += 'width:calc(100vw - 24px - 100.5333px);'  # full width minus padding and 4 btns at the right end
  tab_btns.style += 'overflow-x:auto;'  # scroll content
  for tab in tab_names:
    label = tab.capitalize()
    if tab == '[all]':
      tab_btns.options.append({
        'label': '',
        'value': tab,
        #'icon': 'fiber_smart_record',
        #'icon': 'device_hub',
        'icon': 'brightness_auto',
        #'icon': 'looks',
      })
    elif tab == '':
      tab_btns.options.append({
        'label': '',
        'value': tab,
        'icon': 'radio_button_unchecked',
      })
    else:
      tab_btns.options.append({
        'label': label,
        'value': tab,
      })

  QSpace(a=toolbar)

  def toggle_edit_config(self, msg):
    self.dialog.value = True
    if path.exists(CONFIG_FILE):
      self.dialog_label.text = CONFIG_FILE
      with open(CONFIG_FILE, encoding='utf-8') as file:
        self.dialog_input.value = file.read()
  def edit_dialog_after(self, msg):
    self.dialog_input.remove_class('changed')
  edit_dialog = QDialog(
    maximized=True,
    transition_show='slide-down',
    transition_hide='slide-up',
    a=toolbar,
    name="edit-dialog",
    after=edit_dialog_after,
  )
  edit_dialog_card = QCard(
    a=edit_dialog,
  )
  edit_dialog_bar = QBar(a=edit_dialog_card, classes='bg-'+COLOR_PRIME)
  edit_dialog_label = QItemLabel(a=edit_dialog_bar)  # text filled by handle toggle_edit_config
  QSpace(a=edit_dialog_bar)
  QSeparator(vertical=True,spaced=True,a=edit_dialog_bar)
  def edit_dialog_save(self, msg):
    if path.exists(CONFIG_FILE):
      with open(CONFIG_FILE, mode='w', encoding='utf-8') as file:
        file.write(self.dialog_input.value)
    self.dialog_input.remove_class('changed')
  edit_dialog_btn_save = QBtn(
    a=edit_dialog_bar,
    dense=True,
    flat=True,
    icon='save',
    click=edit_dialog_save)
  QTooltip(a=edit_dialog_btn_save, text='Save')
  QSeparator(vertical=True,spaced=True,a=edit_dialog_bar)
  edit_dialog_btn_close = QBtn(
    a=edit_dialog_bar,
    dense=True,
    flat=True,
    icon='close',
    v_close_popup=True)
  QTooltip(a=edit_dialog_btn_close, text='Close')
  edit_dialog_card_section = QCardSection(
    a=edit_dialog_card,
    #classes='q-pt-none',
  )
  edit_dialog_input = QInput(
    #filled=True,
    type='textarea',
    style='font-family:monospace,monospace;height:calc(100vh - 64px);',  # 32 bar + 16 padding-top + 16 padding-bottom, two components deeper set height 100% see wp.css below
    a=edit_dialog_card_section,
    #value='',  # filled by handle toggle_edit_config
    spellcheck=False,
    #wrap='off',  # not working
    #bg_color="blue-grey-9",  # COLOR_PRIME
    #input_class='text-'+COLOR_PRIME,
    input_class='text-blue-grey-4',
    outlined=True,
    input_style='resize:none;white-space:pre;padding:6px;',
    color='transparent',  # on focus change border color, default is prime (blue)
  )
  def edit_dialog_change(self, msg):
    #print(type(self.classes))
    # self.set_class('changed')  # hangs
    # self.set_classes('changed')  # hangs
    #if self.classes:
    #  return True  # return non None to not update the widget
    self.classes = 'changed'
    # self.error=True  # red border
    # return None to update the widget
  #edit_dialog_input.on('change', edit_dialog_change)  # hits after losing focus
  edit_dialog_input.on('input', edit_dialog_change) # hits during editing
  wp.css += """
    .q-dialog .q-field__control {
      height: 100%;
      padding: unset;
    }
    /* changed coloring */
    .q-field--dark.changed .q-field__control::before {
      border-color: #9653f799;
    }
    .q-field--dark.changed .q-field__control:hover::before {
      border-color: #9653f7 !important;
    }
  """
  edit_dialog_btn_save.dialog_input = edit_dialog_input
  edit_dialog.dialog_input = edit_dialog_input
  # edit_dialog_editor = QEditor(
  #   a=edit_dialog_card_section,
  #   definitions={
  #     'save': {
  #       'tip': 'Save your work',
  #       'icon': 'save',
  #       'label': 'Save',
  #     },
  #     'upload': {
  #       'tip': 'Upload to cloud',
  #       'icon': 'cloud_upload',
  #       'label': 'Upload',
  #     },
  #   },
  #   toolbar=[['undo', 'redo', 'print', 'fullscreen', 'viewsource'],['upload', 'save']],
  # )

  # edit_dialog_html = """
  # <q-dialog :maximized='True'>
  #   <q-card>
  #     <q-bar>
  #     </q-bar>
  #     <q-input filled type='textarea' :rows='10000' value='
  # kalsakdjl
  # alskdlhkhsa
  # lkashdl
  # alksjhdl
  # lkhsadlk
  # alsdh
  # kjashd
  # alkdjsh
  # lakjshd
  # alshjd'>
  #     </q-input>
  #   </q-card>
  # </q-dialog>
  # """
  # edit_dialog = parse_html(edit_dialog_html, a=toolbar)

  edit_config = QBtn(
    dense=True,
    flat=True,
    icon='edit',
    a=toolbar,
    click=toggle_edit_config,
    dialog=edit_dialog,
    dialog_input=edit_dialog_input,
    dialog_label=edit_dialog_label,
  )
  QTooltip(a=edit_config, text='Config')

  # async def dark_light_mode_toggle(self, msg):
  #   if self.icon == 'dark_mode':
  #     self.icon = 'light_mode'
  #   elif self.icon == 'light_mode':
  #     self.icon = 'dark_mode'
  btn_toogle_dark = ToggleDarkModeBtn(
    label='', icon='settings_brightness', dense=True, flat=True, a=toolbar,
    #click=dark_light_mode_toggle
  )
  QTooltip(a=btn_toogle_dark, text='Toggle dark/light mode')
  async def toggle_screen(self, msg):
    await msg.page.run_javascript('Quasar.AppFullscreen.toggle()')
  btn_fullscreen = QBtn(dense=True, flat=True, icon='crop_square', a=toolbar, click=toggle_screen)
  QTooltip(a=btn_fullscreen, text='Toggle fullscreen')
  btn_reload = QBtn(dense=True, flat=True, icon="redo", click=reload, a=toolbar)
  QTooltip(a=btn_reload, text='Reload')
  if "gui" in request.query_params:
    btn_close = QBtn(dense=True, flat=True, icon="close", click=kill_gui, a=toolbar)
    QTooltip(a=btn_close, text='Close')

  page_container = QPageContainer(a=layout)
  page = QPage(a=page_container, name="page-tabs")

  #tab_panels = QTabPanels(v_model='tab', animated=True, a=layout)  # panels not working
  tab_panel = {i:QTabPanel(name=i, classes="q-pa-none", a=page) for i in tab_names}
  msg = Dict()
  msg.page = wp
  await tab_button_change(tab_btns, msg)  # update visibility of tab panels regarding the request

  # add widgets; naming like _div_[tab_name][sec_id]
  for tab_name in widget_dict:
    for i in widget_dict[tab_name]:
      var = "_div_"+tab_name+i     # tab_name: chars or sting-letters, i (sec_id) '' or a string-number
      for j in widget_dict[tab_name][i]:
        if var not in vars():
          vars()[var] = Div(
            name=var,
            classes="row q-pa-sm q-gutter-sm",
            a=tab_panel[tab_name])
        # TODO: empty using label class, like an alias?
        if j['widget-class'] == 'Empty':
          Label(text='',
                wtype=j['type'],
                a=eval(var))
        if j['widget-class'] == Label:
          j['widget-class'](
            text=j['text'],
            wtype=j['type'],
            a=eval(var))
        if j['widget-class'] == Button:
          j['widget-class'](
            text=j['text'], text_alt=j['text-alt'],
            wtype=j['type'],
            command=j['command'], command_alt=j['command-alt'],
            color_bg=j['color-bg'], color_fg=j['color-fg'],
            state_pattern=j['state'], state_pattern_alt=j['state-alt'],
            state_command=j['state-command'],
            icon=j['icon'], icon_alt=j['icon-alt'],
            image=j['image'], image_alt=j['image-alt'],
            a=eval(var))
        elif j['widget-class'] == Slider:
          j['widget-class'](
            name=j['name'], description=j['description'],
            wtype=j['type'],
            a=eval(var))
        elif j['widget-class'] == Volume:
          j['widget-class'](
            name=j['name'], description=j['description'],
            wtype=j['type'],
            a=eval(var))
        elif j['widget-class'] == VolumeGroup:
          j['widget-class'](wtype=j['type'], a=eval(var))

  # TODO: change reference wp.components to ...
  if not wp.components:
    # config not found or empty, therefore insert an empty div to not get an error
    Div(text="add elements in controldeck.conf", classes="flex flex-wrap", a=wp)

  status = config.get('default', 'status', fallback='False').title() == 'True'
  #if status:
  #  wp.add(STATUS_DIV)

  # TODO: Test
  if DEBUG:
    test_row = Div(classes="row q-pa-sm q-gutter-sm", a=tab_panel['[all]'])
    # button with active status led
    test_btn = Button(
      a=test_row,
      text='foo',
    )
    Div(
      a=test_btn,
      style='position: absolute;top: 2px;right: 2px;width: 5px;background-color: #00ff00;height: 5px;border-radius: 2.5px;'
    )
    # notify, position ['top-left', 'top', 'top-right', 'left', 'center', 'right', 'bottom-left', 'bottom', 'bottom-right']
    test_btn.qnotify = QNotify(message='Test nofify', position='top', a=wp)
    def test_btn_click(self, msg):
      self.qnotify.notify = True
      self.qnotify.caption = 'test caption'
    test_btn.on('click', test_btn_click)
    def test_btn_after(self, msg):
      self.qnotify.notify = False
    test_btn.on('after', test_btn_after)

  return wp

@SetRoute('/hello')
def hello_function():
  wp = WebPage()
  wp.add(P(text='Hello there!', classes='text-5xl m-2'))
  return wp

def main(args, host, port):
  if not path.exists(STATIC_DIR):
    makedirs(STATIC_DIR, exist_ok=True)
  justpy(host=host, port=port, start_server=True)
  # this process will run as main loop

def cli():
  global DEBUG
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawTextHelpFormatter,  # preserve formatting
    prefix_chars='-',
    add_help=False,     # custom help text
  )
  parser.add_argument('-c', '--config', nargs='?', type=str, default='',
                      help="Specify a path to a custom config file (default: ~/.config/controldeck/controldeck.conf)")
  parser.add_argument('--host', type=str, default='',
                      help="Specify the host to use (overwrites the value inside the config file, fallbacks to 127.0.0.1)")
  parser.add_argument('--port', type=str, default='',
                      help="Specify the port to use (overwrites the value inside the config file, fallbacks to 8000)")
  parser.add_argument('-v', '--verbose', action="store_true", help="Verbose output")
  parser.add_argument('-D', '--debug', action='store_true', help=argparse.SUPPRESS)
  parser.add_argument('-h', '--help', action='store_true',  # action help auto exits
                      help='Show this help message and exit')
  args = parser.parse_args()

  if args.debug:
    DEBUG = True
    print('[DEBUG] args:', args)
    print('[DEBUG] __file__:', __file__)
    print('[DEBUG] cwd:', getcwd())
    print('[DEBUG] CONFIG_DIR:', CONFIG_DIR, "exists", path.exists(CONFIG_DIR))
    print('[DEBUG] CACHE_DIR:', CACHE_DIR, "exists", path.exists(CACHE_DIR))
    print('[DEBUG] STATIC_DIR:', STATIC_DIR, "exists", path.exists(STATIC_DIR))
    import starlette.routing
    mounts = [i for i in app.routes if type(i) == starlette.routing.Mount]
    mounts = [{'path': i.path, 'name': i.name, 'directory': i.app.directory} for i in mounts]
    print(f"[DEBUG] app mounts: {mounts}")

  config = config_load(args.config)
  host = args.host if args.host else config.get('default', 'host', fallback='127.0.0.1')
  port = args.port if args.port else config.get('default', 'port', fallback='8000')

  if args.debug:
    print('[DEBUG] host:', host)
    print('[DEBUG] port:', port)

  if args.help:
    parser.print_help()
    exit(0)

  main(args, host, port)

  return 0

if __name__ == '__main__':
  sys.exit(cli())
