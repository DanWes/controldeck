#!/usr/bin/env python
"""
https://nicegui.io/
"""
import sys
import os
import argparse
from configparser import ConfigParser
import re
from datetime import datetime
import subprocess
import shlex
import shutil
from nicegui import ui, app

# parameters defined
APP_NAME = "ControlDeck"
DEBUG = False

# parameters derived
CONFIG_DIR = os.path.join(os.path.expanduser("~"), '.config', APP_NAME.lower())
CONFIG_FILE_NAME = APP_NAME.lower() + '.conf'
CONFIG_FILE = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)
CACHE_DIR = os.path.join(os.path.expanduser('~'), '.cache', APP_NAME.lower())
STATIC_DIR = os.path.join(CACHE_DIR, 'static')

def config(conf=''):
  cfg = ConfigParser(strict=False)
  # fist check if file is given
  if conf:
    config_file = conf
  else:
    # check if config file is located at the script's location
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), CONFIG_FILE_NAME)  # realpath; resolve symlink
    if not os.path.exists(config_file):
      # if not, use the file inside .config
      os.makedirs(CONFIG_DIR, exist_ok=True)
      config_file = CONFIG_FILE
  try:
    cfg.read(os.path.expanduser(config_file))
  except Exception as e:
    print(f"{e}")
  #print(cfg.sections())
  return cfg

def widget(cfg) -> dict:
  """scan for widgets to add from the config
  {
    tab-name: {
      section-id: [
        {widget-args}
      ]
    }
  }

  known widgets: empty, label, button, slider, sink-inputs, sink, source
  """
  widget_dict = {}
  for i in cfg.sections():
    iname = None
    iname = re.search(
      r"^([0-9a-z]*:)?([0-9]*\.)?(empty|label|button|slider|sink-inputs|sink|source)",  # sink-inputs BEFORE sink!
      i, flags=re.IGNORECASE)
    if iname is not None:
      tab_name = iname.group(1)[:-1].lower() if iname.group(1) is not None else ''  # remove collon, id is '' if nothing is given
      sec_id = iname.group(2)[:-1] if iname.group(2) is not None else ''  # remove dot, id is '' if nothing is given
      wid_type = iname.group(3).lower()
      wid_name = i[iname.end(0)+1:]  # rest; after last group, can have all chars including . and :

      # check if tab is in dict else insert placeholder
      if tab_name not in widget_dict:
        widget_dict.update({tab_name: {}})
      # check if section is in tab else insert placeholder
      if sec_id not in widget_dict[tab_name]:
        widget_dict[tab_name].update({sec_id: []})

      widget_dict[tab_name][sec_id] += [{
        'type': wid_type,
        'text': wid_name}]
      widget_dict[tab_name][sec_id][-1].update(
        cfg.items(i))
  return widget_dict

def widget_str(wgt) -> str:
  "printable text of the structure"
  # text = f'widgets: {wgt}'
  text = ''
  text += 'widgets:\n\n'
  for tab, secs in wgt.items():
    text += f'- tab: "{tab}"\n'
    for sec, items in secs.items():
      text += f'  - sec: "{sec}"\n'
      # text += f'    - items: {items}\n'
      for item in items:
        text += f'    - `{item}`\n'
  return text

# output good for short / very fast processes, this will block until done
# callback good for long processes
def process(
    command_line, shell=False, stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT, output=True, callback=None):
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
    popen_args = (args, )
    popen_kwargs = dict(
      stdout=stdout,
      stderr=stderr,
      shell=shell,
      start_new_session=True,
    )
    if callback is not None:
      def run_in_thread(callback, popen_args, popen_kwargs):
        proc = subprocess.Popen(*popen_args, **popen_kwargs)
        proc.wait()
        callback()
      thread = threading.Thread(
        target=run_in_thread,
        args=(callback, popen_args, popen_kwargs))
      thread.start()
    else:
      # proc = subprocess.Popen(args, stdout=stdout, stderr=stderr, shell=shell, start_new_session=True)
      proc = subprocess.Popen(*popen_args, **popen_kwargs)
      if output:
        res = proc.stdout.read().decode("utf-8").rstrip()
        proc.kill()  # does not help to unblock
        # print(res)
        return res
  except Exception as e:
    print(f"process '{e}' failed!")

#
# CLI
#
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

if not os.path.exists(STATIC_DIR):
  os.makedirs(STATIC_DIR, exist_ok=True)

if args.debug:
  DEBUG = True
  print('[DEBUG] args:', args)
  print('[DEBUG] __file__:', __file__)
  print('[DEBUG] cwd:', os.getcwd())
  print('[DEBUG] CONFIG_DIR:', CONFIG_DIR, "exists", os.path.exists(CONFIG_DIR))
  print('[DEBUG] CACHE_DIR:', CACHE_DIR, "exists", os.path.exists(CACHE_DIR))
  print('[DEBUG] STATIC_DIR:', STATIC_DIR, "exists", os.path.exists(STATIC_DIR))
  #import starlette.routing
  #mounts = [i for i in app.routes if type(i) == starlette.routing.Mount]
  #mounts = [{'path': i.path, 'name': i.name, 'directory': i.app.directory} for i in mounts]
  #print(f"[DEBUG] app mounts: {mounts}")

cfg = config(args.config)
host = args.host if args.host else cfg.get('default', 'host', fallback='127.0.0.1')
port = args.port if args.port else cfg.get('default', 'port', fallback='8080')

if args.debug:
  print('[DEBUG] host:', host)
  print('[DEBUG] port:', port)

if args.help:
  parser.print_help()
  exit(0)


wgt = widget(cfg)

#
# NiceGUI
#
import yaml
app.add_static_files('/static', STATIC_DIR)
def empty(**kwargs):
  # with ui.element('div') as d:
  with ui.card().tight() as d:
    d.classes('bg-grey-9')  # TODO: remove bg color
    d.style("width: 90px;min-height: 80px;line-height: 1em;")
    # text = yaml.dump_all([kwargs])
    text = "\n".join([ll.rstrip() for ll in yaml.dump_all([kwargs]).splitlines() if ll.strip()])
    ui.tooltip(f"{text}").style('white-space: pre-wrap')
  return d
def unknown(**kwargs):
  with empty(**kwargs) as d:
    d.classes(replace='bg-red-10')
    ui.label(kwargs['text'])
  return d
def label(**kwargs):
  with empty(**kwargs) as d:
    d.classes(replace='bg-blue-grey-10')
    d.classes('q-pa-sm text-blue-grey-5 text-bold text-center q-btn--push')
    # q-btn--push = border-radius: 7px;
    ui.label(kwargs['text'])
  return d
class ToggleButton(ui.button):
  def __init__(self, *args, **kwargs) -> None:
    # super().__init__(*args, **kwargs)
    super().__init__()
    self._state = False
    self.on('click', self.toggle)
    self.command = kwargs.get('command', None)
    self.command_alt = kwargs.get('command-alt', None)
    self.state_alt = kwargs.get('state-alt', None)
    self.state_command = kwargs.get('state-command', '')
    self.state = ''
    if self.state_command:
      try:
        self.state = process(self.state_command, shell=True, output=True)
      except Exception as e:
        print(e)
    if self.state == self.state_alt:
      self._state = True
  def toggle(self) -> None:
    """Toggle the button state."""
    if self._state == False:
      # button not yet toggled
      if DEBUG:
        print(f"[btn] command: {self.command}")
      output = process(self.command, shell=True, output=False) # output=True freezes until finished
    elif self.command_alt is not None:
      if DEBUG:
        print(f"[btn] command-alt: {self.command_alt}")
      output = process(self.command_alt, shell=True, output=False) # output=True freezes until finished
    self._state = not self._state
    if self.state_alt is not None:  # state_alt not command_alt b/c state for visual feedback
      self.update()
  def update(self) -> None:
    # self.props(f'color={"green" if self._state else "red"}')
    self.style(f'border: 1px solid {"#0277bd" if self._state else "#455a64"}')
    super().update()
def button(**kwargs):
  text = kwargs['description'] if 'description' in kwargs else kwargs['text']
  icon = kwargs.get('icon', '')
  image = kwargs.get('image', '')

  if image and os.path.exists(image):
    # copy image files into the static folder
    basename = os.path.basename(image)
      # e.g. media-playback-stop.svg
    staticfile = os.path.join(STATIC_DIR, basename)
      # e.g. <user-home>/.cache/controldeck/static/media-playback-stop.svg
    if not os.path.exists(staticfile):
      shutil.copy2(image, staticfile)
      if DEBUG:
        print(f'[DEBUG.btn.{text}] copy {image} to {staticfile}')
    icon = f"img:/static/{basename}"
      # e.g. img:/static/media-playback-stop.svg
    # <q-icon name="img:data:image/svg+xml;charset=utf8,<svg xmlns='http://www.w3.org/2000/svg' height='140' width='500'><ellipse cx='200' cy='80' rx='100' ry='50' style='fill:yellow;stroke:purple;stroke-width:2' /></svg>" />
    # <q-btn icon="img:data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==" ... />
    if DEBUG:
      print(f'[DEBUG.btn.{text}] icon: {icon}')

  # with ui.button() as d:
  with ToggleButton(**kwargs) as d:
    d.props('dense')
    d.classes('bg-grey-10')
    # d.style("width: 90px;min-height: 77px;border: 1px solid var(--c-blue-grey-8);")
    d.style("width: 90px;min-height: 80px;line-height: 1em;border: 1px solid #455a64;")
    if 'color-bg' in kwargs and kwargs['color-bg']:
      d.style(f"background-color: {kwargs['color-bg']};")
    if 'color-fg' in kwargs and kwargs['color-fg']:
      d.style(f"color: {kwargs['color-fg']} !important;")
    tttext = "\n".join([ll.rstrip() for ll in yaml.dump_all([kwargs]).splitlines() if ll.strip()])
    tttext += f"\nstate: {d.state}"
    ui.tooltip(f"{tttext}").style('white-space: pre-wrap')
    with d:
      with ui.element('div').classes('w-full'):
        ui.icon(icon)
      ui.label(text)
  return d
def slider(**kwargs):
  """command can have a {value} placeholder to insert slider value
  """
  min = kwargs.get('min', '0')
  min = float(min) if min else 0
  max = kwargs.get('max', '100')
  max = float(max) if max else 100
  step = kwargs.get('step', '1')
  step = float(step) if step else 1
  icon = kwargs.get('icon', 'tune')
  command = kwargs.get('command', '')
  state_command = kwargs.get('state-command', '')
  value = min
  if state_command:
    try:
      value = float(process(state_command, shell=True))
    except Exception as e:
      print(e)
  def action(*args, **kwargs):
    # e.g. args[0] = GenericEventArguments(
    #   sender=<nicegui.elements.slider.Slider object at 0x7c3f8e865b50>,
    #   client=<nicegui.client.Client object at 0x7c3f8fcaac10>,
    #   args=0.95)
    value = args[0].args
    if DEBUG:
      print("[sld] command:", command.format(value=value))
    process(command.format(value=value), shell=True, output=False)
  with ui.element('div') as d:
    d.style("width: 302px;min-height: 80px;") # 3*90=270 + 2*16=32 = 302
    text = "\n".join([ll.rstrip() for ll in yaml.dump_all([kwargs]).splitlines() if ll.strip()])
    ui.tooltip(f"{text}").style('white-space: pre-wrap')
    with ui.row().classes('text-ml'):
      ui.icon(icon).classes('text-2xl')
      text = kwargs['description'] if 'description' in kwargs else kwargs['text']
      ui.label(text).style("padding-top:1px;")
      v = ui.label().style("padding-top:1px;")
      s = ui.slider(min=min, max=max, step=step, value=value).props('markers')
      v.bind_text_from(s, 'value')
      s.props('color=blue-9')#.props('label-always')
      s.style("padding-left:16px;padding-right:16px;")
      # s.style("width: 200px;padding-top:30px;")
      #s.on_value_change(action)
      s.on('update:model-value', lambda e: action(e),
        throttle=1.0, leading_events=False)  # update every second (only last value of every second)
  return d
def volume(**kwargs):
  # sinks (loudspeaker); icon: volume_up, volume_mute (or volume_off)
  # source (microphone), icon: mic and mic_none (or mic_off)
  # sink-input (app output)
  # TODO: disable / mute button function on icon
  icon = ''
  if kwargs['type'] == 'sink':
    icon = 'volume_up'
  elif kwargs['type'] == 'source':
    icon = 'mic'
  elif kwargs['type'] == 'sink-input':
    icon = 'volume_up'
  kwargs.update({'min': 0, 'max': 100, 'step': 5, 'icon': icon})
  with slider(**kwargs) as d:
    pass
  return d
def volume_group(**kwargs):
  ds = []
  kwargs.update({'wtype': 'sink-input'})
  # for i in Volume.data['sink-inputs']:
  for i in []:
    with volume(**kwargs) as d:
      pass
    ds.append(d)
  return ds

def reload() -> None:
  global cfg, wgt
  cfg = config(args.config)
  wgt = widget(cfg)
  ui.navigate.reload()

@ui.page('/')
def index(tab:str=''):
  """uses wgt"""

  # tabs bar
  with ui.header().classes(replace='row items-center no-wrap') as header:
    ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
    with ui.tabs(on_change=lambda evt: ui.run_javascript(f"window.history.pushState('', '', '/?tab={evt.value}')")) as tabs:
      ui.tab(name='[all]', label='', icon='brightness_auto').tooltip('[all]')
      # for tabi in sorted(wgt.keys()):
      for tabi in wgt.keys():
        opts = {'name': tabi, 'label': tabi}
        if tabi == '':
          opts.update({'name': '[]', 'label':'', 'icon': 'radio_button_unchecked'})
        ui.tab(**opts).tooltip(opts['name'])
    # tabs.style('overflow-x:auto;')
  header.style('overflow-x:auto;')
  header.classes('bg-blue-grey-10')

  # footer
  with ui.footer(value=False) as footer:
    ui.label('Footer')
  footer.classes('bg-blue-grey-10')

  # left side drawer
  with ui.left_drawer().classes('bg-blue-grey-10') as left_drawer:
    ui.label('Side menu')
    left_drawer_label = ui.label()
    ui.timer(1.0, lambda: left_drawer_label.set_text(f'{datetime.now():%X}'))
    left_drawer_button = ui.button('reload', on_click=lambda: reload())
    
  # content for tabs
  with ui.tab_panels(tabs, value=tab).classes('w-full'):
    for tabi, secs in wgt.items():
      if tabi == '':
        tabi = '[]'
      # ui.markdown(tabi)
      with ui.tab_panel(tabi):
        for seci, items in secs.items():
          with ui.row():
            for item in items:
              if item['type'] == 'empty':
                empty(**item)
              if item['type'] == 'label':
                label(**item)
              elif item['type'] == 'button':
                button(**item)
              elif item['type'] == 'slider':
                slider(**item)
              elif item['type'] in ['sink', 'source']:
                volume(**item)
              elif item['type'] in ['sink-inputs']:
                volume_group(**item)
              else:
                unknown(**item)

  # button to toggle footer
  with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
    ui.button(on_click=footer.toggle, icon='contact_support').props('fab').classes('bg-blue-grey-10')

@ui.page('/test')
def test():
  """test"""
  ui.markdown(widget_str(wgt)).classes('w-full')#.style('overflow-x:auto;')

ui.add_head_html("""<meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="mobile-web-app-capable" content="yes">""")
ui.run(host=host, port=int(port), title=APP_NAME, dark=True)
