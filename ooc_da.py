import json
import argparse
import math
import os

eps = 1e-10

'''
  "Main" function that is executed when the script is run.
'''
def run(inputfile, outputfile):
  solve_and_write(inputfile, outputfile)

def solve_and_write(inputfile, outputfile):
  input = read_input_file(inputfile)
  result = solve(input)
  write_output_file(result, outputfile)

'''
  takes as input a struct as the json files in ./architectures/*, computes for each module channel dimensions, flow rates, resistances, etc ... and some global values
'''
def solve(input):
  # calculate mini-human weights and sizes
  reference_round_tissue_volume = (4 / 3) * math.pi * (input['reference']['round_tissue_radius'] ** 3)
  reference_round_tissue_mass = reference_round_tissue_volume * (input['reference']['real_round_tissue_mass'] / input['reference']['real_round_tissue_volume'])
  reference_mini_human_mass = reference_round_tissue_mass * (input['reference']['standard_human_mass'] / input['reference']['real_round_tissue_mass'])
  
  channel_height = input['channel_height']
  viscosity = input['viscosity']
  spacing = input['spacing']
  radius = input['radius']

  result = dict(input)
  result['modules'] = list(map(lambda m: dict(m), input['modules']))

  n_modules = len(input['modules'])
  if n_modules == 0:
    raise 'No modules supplied.'

  max_module_width = -math.inf

  # compute mini organ sizes and determine module dimensions
  for i in range(n_modules):
    module = result['modules'][i]

    mini_mass = (reference_mini_human_mass / input['reference']['standard_human_mass']) * module['real_mass']
    module['mini_mass'] = mini_mass
    mini_volume = (mini_mass / module['real_mass']) * module['real_volume']
    module['mini_volume'] = mini_volume
    module['channels'] = {}

    if module['type'] == 'round_tissue':
      round_tissue_radius = ((mini_volume * (3 / 4)) / math.pi) ** (1 / 3)
      module_width = 4 * round_tissue_radius
      if module_width > max_module_width:
        max_module_width = module_width

  if max_module_width == -math.inf:
    max_module_width = input['module_width']

  result['max_module_width'] = max_module_width

  '''
    default channel sizes, this is subject to change, currently:
    * all channels same height
    * horizontal channels (c_main, c_supply_carry, c_discharge_carry, c_pre, c_post) same width (module width), c_connection is half of that; c_connection width must be less equal c_main width (due to meander spacing)
    * c_supply, c_discharge width = 1.5 * channel height
    * lengths for c_main are already computed
    * lengths for pre & post are spacing + 0.5 * incident channels width (c_supply or c_discharge) + module_before_after_extra_offset (manual offset in input; the larger this is, the easier a meander is fitting, hence the easier it is to get a "good" design, currently)
    * lengths for c_discharge is 0.5*c_discharge_carry_width + 0.5*c_main_width + spacing (i.e., the minimum possible, but not correct design)
    * (analogous) lengths for c_supply is 0.5*c_supply_carry_width + 0.5*c_main_width + spacing (i.e., the minimum possible, but not correct design)
    * lengths for c_discharge_carry/c_supply_carry add up naturally
    * exceptions apply for first and last modules as denoted
  '''

  supply_default_width = 1.5 * channel_height
  discharge_default_width = 1.5 * channel_height

  pre_default_length = 0.5 * supply_default_width + spacing + input['module_before_after_extra_offset']
  post_default_length = 0.5 * discharge_default_width + spacing + input['module_before_after_extra_offset']

  connection_default_width = 0.5 * max_module_width
  connection_default_length = 0.5 * supply_default_width + spacing + 0.5 * discharge_default_width

  supply_carry_default_width = max_module_width
  supply_default_offset = 0.5 * max_module_width + 0.5 * supply_carry_default_width + spacing

  discharge_carry_default_width = max_module_width
  discharge_default_offset = 0.5 * max_module_width + 0.5 * discharge_carry_default_width + spacing

  result['supply_offset'] = supply_default_offset
  result['discharge_offset'] = discharge_default_offset
  result['pump'] = {
    'flowrate': 0
  }
  result['refeed'] = {
    'flowrate': 0
  }
  result['module_y_offset'] = 0

  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    mini_mass = module['mini_mass']
    mini_volume = module['mini_volume']
    c_main_width = max_module_width
    if module['type'] == 'round_tissue':
      c_main_length = max_module_width

    elif module['type'] == 'layered_tissue':
      c_main_length = mini_volume / (max_module_width * input['reference']['number_of_layers'] * input['reference']['cell_layer_thickness'])

    else:
      raise('Unknown module type')

    c_main_flowrate = (input['shear'] * c_main_width * (input['channel_height'] ** 2)) / (6 * viscosity)
    c_main_resistance = resistance(c_main_width, channel_height, c_main_length, viscosity)
    module['channels']['c_main'] = {
      'flowrate': c_main_flowrate,
      'width': c_main_width,
      'height': channel_height,
      'length': c_main_length,
      'resistance': c_main_resistance,
      'pressuregradient': c_main_flowrate * c_main_resistance
    }

    module['channels']['c_pre'] = {
      'flowrate': c_main_flowrate,
      'width': c_main_width,
      'height': channel_height,
      'length': pre_default_length,
    }
    if is_first:
      module['channels']['c_pre']['length'] += input['discharge_extra_offset']

    module['channels']['c_post'] = {
      'flowrate': c_main_flowrate,
      'width': c_main_width,
      'height': channel_height,
      'length': post_default_length,
    }

    if is_first:
      module['channels']['c_connection'] = {
        'flowrate': module['perfusion_rate'] * c_main_flowrate,
        'width': connection_default_width,
        'height': channel_height,
        'length': connection_default_length + input['refeed_extra_offset'],
      }
    else:
      module['channels']['c_connection'] = {
        'flowrate': module['perfusion_rate'] * c_main_flowrate,
        'width': connection_default_width,
        'height': channel_height,
        'length': connection_default_length,
      }

    if is_last:
      module['channels']['c_discharge'] = {
        'flowrate': c_main_flowrate,
        'width': discharge_default_width,
        'height': channel_height,
        'length': discharge_default_offset,
      }
    else:
      module['channels']['c_discharge'] = {
        'flowrate': c_main_flowrate - next_module['channels']['c_connection']['flowrate'],
        'width': discharge_default_width,
        'height': channel_height,
        'length': discharge_default_offset,
      }

    if is_last:
      module['channels']['c_discharge_carry'] = {
        'flowrate': c_main_flowrate,
        'width': discharge_carry_default_width,
        'height': channel_height,
        'length': connection_default_length + pre_default_length + c_main_length + post_default_length,
      }
    elif is_first:
      module['channels']['c_discharge_carry'] = {
        'flowrate': module['channels']['c_discharge']['flowrate'] + next_module['channels']['c_discharge_carry']['flowrate'],
        'width': discharge_carry_default_width,
        'height': channel_height,
        'length': connection_default_length + pre_default_length + c_main_length + post_default_length  + input['refeed_extra_offset'] + input['discharge_extra_offset'], 
      }
    else:
      module['channels']['c_discharge_carry'] = {
        'flowrate': module['channels']['c_discharge']['flowrate'] + next_module['channels']['c_discharge_carry']['flowrate'],
        'width': discharge_carry_default_width,
        'height': channel_height,
        'length': connection_default_length + pre_default_length + c_main_length + post_default_length,
      }

    if is_last:
      module['channels']['c_supply'] = {
        'flowrate': (1-module['perfusion_rate']) * c_main_flowrate,
        'width': supply_default_width,
        'height': channel_height,
        'length': supply_default_offset
      }
    else:
      module['channels']['c_supply'] = {
        'flowrate': (1-module['perfusion_rate']) * c_main_flowrate,
        'width': supply_default_width,
        'height': channel_height,
        'length': supply_default_offset,
      }

    result['modules'][i] = module

  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    mini_mass = module['mini_mass']
    mini_volume = module['mini_volume']
    c_main_width = max_module_width
    if module['type'] == 'round_tissue':
      c_main_length = max_module_width

    elif module['type'] == 'layered_tissue':
      c_main_length = mini_volume / (max_module_width * input['reference']['number_of_layers'] * input['reference']['cell_layer_thickness'])

    else:
      raise('Unknown module type')

    if is_last:
      module['channels']['c_supply_carry'] = {
        'flowrate': (1-module['perfusion_rate']) * c_main_flowrate,
        'width': supply_carry_default_width,
        'height': channel_height,
        'length': connection_default_length + previous_module['channels']['c_main']['length'] + previous_module['channels']['c_pre']['length'] + previous_module['channels']['c_post']['length']
      }
    elif is_first:
      module['channels']['c_supply_carry'] = {
        'flowrate': (1-module['perfusion_rate']) * c_main_flowrate + next_module['channels']['c_supply_carry']['flowrate'],
        'width': supply_carry_default_width,
        'height': channel_height,
        'length': connection_default_length + input['refeed_extra_offset']
      }
    else:
      module['channels']['c_supply_carry'] = {
        'flowrate': (1-module['perfusion_rate']) * c_main_flowrate + next_module['channels']['c_supply_carry']['flowrate'],
        'width': supply_carry_default_width,
        'height': channel_height,
        'length': connection_default_length + previous_module['channels']['c_main']['length'] + previous_module['channels']['c_pre']['length'] + previous_module['channels']['c_post']['length'],
      }

  result['pump']['flowrate'] = result['modules'][0]['channels']['c_supply_carry']['flowrate']
  result['refeed']['flowrate'] = result['modules'][0]['channels']['c_connection']['flowrate']

  # Initialize all channels by computing resistance, pressures and meanders

  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    recompute_resistances(module, viscosity)
    recompute_pressuregradients(module)

  recompute_meanders(result)

  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

  # iterate until convergence is reached, i.e., until no more pressures have changed

  max_iterations = 1000
  i = 0
  while i < max_iterations:
    changed = correct_pressuregradients(result)
    if not changed:
      print('Solution converged in {} iterations.'.format(i+1))
      break
    correct_offsets(result)
    recompute_meanders(result)
    i += 1

  if i == max_iterations:
    raise Exception('max iterations exceeded')
  
  # compute additional values for output
  compute_all_meander_vias(result)
  compute_module_offsets(result)

  return result




def correct_pressuregradients(result):
  changed_discharge = forward_discharge_correction(result)
  changed_supply = forward_supply_correction(result)
  return changed_discharge or changed_supply


def forward_supply_correction(result):
  changed = False
  n_modules = len(result['modules'])
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    if not is_first:
      # in paper, this is the "right" arrow part of the pressure cycle
      supplyCyclePressure = -module['channels']['c_connection']['pressuregradient'] - previous_module['channels']['c_pre']['pressuregradient'] - previous_module['channels']['c_main']['pressuregradient'] - previous_module['channels']['c_post']['pressuregradient'] + module['channels']['c_supply']['pressuregradient'] + module['channels']['c_supply_carry']['pressuregradient']
      # in paper, this is the "left" arrow, i.e., just the single channel pressure
      oppositeSupplyPressure = previous_module['channels']['c_supply']['pressuregradient']

      # both must add up to zero, but in general they dont, this is the difference (the "error" that needs to be corrected)
      supplyMissingPressure = supplyCyclePressure - oppositeSupplyPressure
      if supplyMissingPressure > eps:
        changed = True

        # left channel needs to have a higher pressure gradient, i.e., needs higher resistance, and therefore more length
        supplyMissingResistance = supplyMissingPressure / previous_module['channels']['c_supply']['flowrate']
        correct_resistance(previous_module['channels']['c_supply'], supplyMissingResistance, result['viscosity'])
      elif supplyMissingPressure < -eps:
        changed = True
        # left channel already has a higher pressure gradient, therefore, correct all supply channels to the right of this module
        backward_supply_correction(result, i)
      else:
        pass
  return changed



def forward_discharge_correction(result):
  # analogous to forward_supply_correction
  changed = False
  n_modules = len(result['modules'])
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    if not is_first:
      dischargeCyclePressure = module['channels']['c_connection']['pressuregradient'] + module['channels']['c_pre']['pressuregradient'] + module['channels']['c_main']['pressuregradient'] + module['channels']['c_post']['pressuregradient'] + module['channels']['c_discharge']['pressuregradient'] + module['channels']['c_discharge_carry']['pressuregradient']
      oppositeDischargePressure = previous_module['channels']['c_discharge']['pressuregradient']
      dischargeMissingPressure = dischargeCyclePressure - oppositeDischargePressure
      if dischargeMissingPressure > eps:
        changed = True
        dischargeMissingResistance = dischargeMissingPressure / previous_module['channels']['c_discharge']['flowrate']
        correct_resistance(previous_module['channels']['c_discharge'], dischargeMissingResistance, result['viscosity'])
      elif dischargeMissingPressure < -eps:
        changed = True
        backward_discharge_correction(result, i)
      else:
        pass
  return changed


def backward_supply_correction(result, start):
  # analogous to forward_supply_correction but (1) in the other direction (to the right) and (2) starts at a given module "start" and (3) corrects the right-hand-side supply channel
  n_modules = len(result['modules'])
  for i in range(start, n_modules):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    if not is_first:
      supplyCyclePressure = module['channels']['c_connection']['pressuregradient'] + previous_module['channels']['c_pre']['pressuregradient'] + previous_module['channels']['c_main']['pressuregradient'] + previous_module['channels']['c_post']['pressuregradient'] + previous_module['channels']['c_supply']['pressuregradient'] - module['channels']['c_supply_carry']['pressuregradient']
      oppositeSupplyPressure = module['channels']['c_supply']['pressuregradient']
      supplyMissingPressure = supplyCyclePressure - oppositeSupplyPressure
      if supplyMissingPressure < 0:
        raise 'case should never occur'
      supplyMissingResistance = supplyMissingPressure / module['channels']['c_supply']['flowrate']
      correct_resistance(module['channels']['c_supply'], supplyMissingResistance, result['viscosity'])

def backward_discharge_correction(result, start):
  # analogous to backward_supply_correction
  n_modules = len(result['modules'])
  for i in range(start, n_modules):
    module = result['modules'][i]
    id = module['id']
    is_first = i == 0
    is_last = i == n_modules - 1
    
    if not is_last:
      next_module = result['modules'][i+1]

    if not is_first:
      previous_module = result['modules'][i-1]

    if not is_first:
      dischargeCyclePressure = -module['channels']['c_connection']['pressuregradient'] - module['channels']['c_pre']['pressuregradient'] - module['channels']['c_main']['pressuregradient'] - module['channels']['c_post']['pressuregradient'] + previous_module['channels']['c_discharge']['pressuregradient'] - module['channels']['c_discharge_carry']['pressuregradient']
      oppositeDischargePressure = module['channels']['c_discharge']['pressuregradient']
      dischargeMissingPressure = dischargeCyclePressure - oppositeDischargePressure
      if dischargeMissingPressure < 0:
        raise 'case should never occur'
      dischargeMissingResistance = dischargeMissingPressure / module['channels']['c_discharge']['flowrate']
      correct_resistance(module['channels']['c_discharge'], dischargeMissingResistance, result['viscosity'])


def correct_resistance(channel, missing, viscosity):
  # adds "missing" amount of resistance to the channel and updates its length, resistance and pressure
  current_resistance = channel['resistance']
  current_length = channel['length']
  if missing == 0:
    return
  else:
    resistance_per_length = current_resistance / current_length
    missing_length = missing / resistance_per_length
    channel['length'] += missing_length
    recompute_resistance(channel, viscosity)
    recompute_pressuregradient(channel)

def correct_offsets(result):
  correct_supply_offset(result)
  correct_supply_lengths(result)
  correct_discharge_offset(result)
  correct_discharge_lengths(result)

def correct_supply_offset(result):
  # set supply offset such that all meanders fit, i.e. for each module, compute the minimum necessary meander, take the max of all
  result['supply_offset'] = max(list(map(lambda m: min_meander_vertical(m['channels']['c_supply']['width'], result['spacing'], m['channels']['c_main']['width'], m['channels']['c_supply_carry']['width'], m['channels']['c_supply']['meander_bend_length'], m['channels']['c_supply']['length']), result['modules'])))

def correct_discharge_offset(result):
  # analogous
  result['discharge_offset'] = max(list(map(lambda m: min_meander_vertical(m['channels']['c_discharge']['width'], result['spacing'], m['channels']['c_main']['width'], m['channels']['c_discharge_carry']['width'], m['channels']['c_discharge']['meander_bend_length'], m['channels']['c_discharge']['length']), result['modules'])))

def correct_supply_lengths(result):
  # if any channels are shorter than the supply_offset, they need to be changed such that they have the supply_offset as length (i.e. they need to be physically connected to the supply_carry)
  n_modules = len(result['modules'])
  offset = result['supply_offset']
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    if module['channels']['c_supply']['length'] < offset:
      module['channels']['c_supply']['length'] = offset
      recompute_resistance(module['channels']['c_supply'], result['viscosity'])
      recompute_pressuregradient(module['channels']['c_supply'])

def correct_discharge_lengths(result):
  # analogous
  n_modules = len(result['modules'])
  offset = result['discharge_offset']
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    if module['channels']['c_discharge']['length'] < offset:
      module['channels']['c_discharge']['length'] = offset
      recompute_resistance(module['channels']['c_discharge'], result['viscosity'])
      recompute_pressuregradient(module['channels']['c_discharge'])

def min_meander_vertical(channel_width, spacing, upper_half_channel, lower_half_channel, bend_length, required_length):
  # compute the minimal necessary height of a meander that fits the required channel length
  length_without_endspaces = required_length - upper_half_channel - lower_half_channel - spacing
  if length_without_endspaces < eps:
    return upper_half_channel + lower_half_channel + spacing
  required_bends = math.ceil(length_without_endspaces / (2 * bend_length + 2 * spacing + 2 * channel_width))
  return required_bends * (2 * spacing + 2 * channel_width) + upper_half_channel + lower_half_channel + spacing

def recompute_resistances(module, viscosity): 
  for id, channel in module['channels'].items():
    recompute_resistance(channel, viscosity)
  
def recompute_resistance(channel, viscosity):
  channel['resistance'] = resistance(channel['width'], channel['height'], channel['length'], viscosity)

def recompute_pressuregradients(module):
  for id, channel in module['channels'].items():
    recompute_pressuregradient(channel)

def recompute_pressuregradient(channel):
  channel['pressuregradient'] = channel['resistance'] * channel['flowrate']

def resistance(width, height, length, viscosity):
  return 12 * viscosity * length / ((1 - 0.63 * (height/width)) * (height**3) * width)

def recompute_meanders(result):
  recompute_supply_meanders(result)
  recompute_discharge_meanders(result)

def recompute_supply_meander_bend_length(module, i, previous_module, spacing, radius):
  # the length of a meander bend, computed by spacing, and dimensions of the surrounding channels
  if i != 0:
    module['channels']['c_supply']['meander_bend_length'] = previous_module['channels']['c_pre']['length'] + previous_module['channels']['c_main']['length'] + previous_module['channels']['c_post']['length'] + module['channels']['c_connection']['length'] - 0.5 * previous_module['channels']['c_supply']['width'] - 0.5 * module['channels']['c_supply']['width'] - spacing + (2 * math.pi - 8) * radius
  else:
    module['channels']['c_supply']['meander_bend_length'] = module['channels']['c_connection']['length'] - 0.5 * module['channels']['c_supply']['width'] + (2 * math.pi - 8) * radius

def recompute_discharge_meander_bend_length(module, i, previous_module, spacing, radius): 
  # analogous
  if i != 0:
    module['channels']['c_discharge']['meander_bend_length'] = module['channels']['c_pre']['length'] + module['channels']['c_main']['length'] + module['channels']['c_post']['length'] + module['channels']['c_connection']['length'] - 0.5 * previous_module['channels']['c_discharge']['width'] - 0.5 * module['channels']['c_discharge']['width'] - spacing + (2 * math.pi - 8) * radius
  else:
    module['channels']['c_discharge']['meander_bend_length'] = module['channels']['c_pre']['length'] + module['channels']['c_main']['length'] + module['channels']['c_post']['length'] - 0.5 * module['channels']['c_discharge']['width'] - spacing + (2 * math.pi - 8) * radius

def meander_bends(offset, upper_half_width, lower_half_width, spacing, width): # defines height (rounding has no impact)
  return math.floor((offset - 0.5 * lower_half_width - 0.5 * upper_half_width - spacing) / (2 * spacing + 2 * width))

def recompute_supply_meanders(result):
  # mainly computes number of bends
  n_modules = len(result['modules'])
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    is_first = i == 0

    previous_module = None
    if not is_first:
      previous_module = result['modules'][i-1]

    supply = module['channels']['c_supply']
    supply['meander_bends'] = meander_bends(result['supply_offset'], module['channels']['c_main']['width'], module['channels']['c_supply_carry']['width'], result['spacing'], supply['width'])
    recompute_supply_meander_bend_length(module, i, previous_module, result['spacing'], result['radius'])
    supply['max_length'] = result['supply_offset'] + 2 * supply['meander_bends'] * supply['meander_bend_length'] 

def recompute_discharge_meanders(result):
  # analogous
  n_modules = len(result['modules'])
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    is_first = i == 0
    if not is_first:
      previous_module = result['modules'][i-1]

    discharge = module['channels']['c_discharge']
    discharge['meander_bends'] = meander_bends(result['discharge_offset'], module['channels']['c_main']['width'], module['channels']['c_discharge_carry']['width'], result['spacing'], discharge['width'])
    recompute_discharge_meander_bend_length(module, i, previous_module, result['spacing'], result['radius'])
    discharge['max_length'] = result['discharge_offset'] + 2 * discharge['meander_bends'] * discharge['meander_bend_length'] 

def compute_all_meander_vias(result):
  # computes intermediate points of meanders
  n_modules = len(result['modules'])
  for i in reversed(range(n_modules)):
    module = result['modules'][i]
    compute_meander_vias(result, module, module['channels']['c_supply'], abs(result['supply_offset']), module['channels']['c_supply_carry']['width'], True)
    compute_meander_vias(result, module, module['channels']['c_discharge'], result['discharge_offset'], module['channels']['c_discharge_carry']['width'], False)
    compute_rounded_meander_vias(result, module['channels']['c_supply'], True)
    compute_rounded_meander_vias(result, module['channels']['c_discharge'], False)

def compute_meander_vias(result, module, channel, offset, upper_half_width, up):
  eps = 1e-6
  vias = []
  spacing = result['spacing']
  meander_bends = channel['meander_bends']
  required_length = channel['length']
  meander_length = (required_length) - (offset) # + (meander_bends * (2 * math.pi - 8) * result['radius'])) # how long the channel would be without rounded edges
  if meander_bends <= 0:
    channel['vias'] = []
    return
  actual_bend_length = meander_length / (meander_bends*2)
  meander_vertical = offset - 0.5 * module['channels']['c_main']['width'] - 0.5 * upper_half_width - spacing
  # distribute bends uniformly
  bend_height = meander_vertical / (meander_bends)
  x = 0
  y = 0
  y_offset = y + (-1 if up else 1) * (0.5 * module['channels']['c_main']['width'] + 0.5 * spacing)
  if meander_length < eps:
    channel['vias'] = []
    return

  # this is a workaround; the channel generator tool cannot (at this time) create intermediate channels that are shorter then the width, also of adjacents;
  # therefore, if the meander is only a little bit longer than a straight channel, distribute extra length among meander bends differently
  # this may lead to slightly off lengths if the meander has only a few bends
  if actual_bend_length <= 2*channel['width']:
    target_length = required_length - (offset) # + (meander_bends * (2 * math.pi - 8) * result['radius']))
    current = 0
    i = 0
    while current < target_length:
      print('current: {}, target: {}'.format(current, target_length))
      current += 4*channel['width']
      vias.append([x, y_offset + (-1 if up else 1) * (bend_height * i + 0.5 * spacing + 0.5 * channel['width'])])
      vias.append([x - 2*channel['width'], y_offset + (-1 if up else 1) * (bend_height * i + 0.5 * spacing + 0.5 * channel['width'])])
      vias.append([x - 2*channel['width'], y_offset + (-1 if up else 1) * (bend_height * i + 1.5 * spacing + 1.5 * channel['width'])])
      vias.append([x, y_offset + (-1 if up else 1) * (bend_height * i + 1.5 * spacing + 1.5 * channel['width'])])
      i += 1
    channel['vias'] = vias
    return
    
  for i in range(meander_bends):
    vias.append([x, y_offset + (-1 if up else 1) * (bend_height * i + 0.5 * spacing + 0.5 * channel['width'])])
    vias.append([x - actual_bend_length, y_offset + (-1 if up else 1) * (bend_height * i + 0.5 * spacing + 0.5 * channel['width'])])
    vias.append([x - actual_bend_length, y_offset + (-1 if up else 1) * (bend_height * i + 1.5 * spacing + 1.5 * channel['width'])])
    vias.append([x, y_offset + (-1 if up else 1) * (bend_height * i + 1.5 * spacing + 1.5 * channel['width'])])

  channel['vias'] = vias

def compute_rounded_meander_vias(result, channel, up):
  rounded_vias = []
  radius = result['radius']
  i = 0
  vias = channel['vias']
  if up:
    while i in range(len(vias)): # supply, [startpoint, midpoint]
      rounded_vias.append([[vias[i][0], vias[i][1] + radius],[vias[i][0] - radius, vias[i][1] + radius], [vias[i][0] - radius, vias[i][1]], [-90]])
      i+=1
      rounded_vias.append([[vias[i][0] + radius, vias[i][1]],[vias[i][0] + radius, vias[i][1] - radius], [vias[i][0], vias[i][1] - radius], [90]])
      i+=1
      rounded_vias.append([[vias[i][0], vias[i][1] + radius],[vias[i][0] + radius, vias[i][1] + radius], [vias[i][0] + radius, vias[i][1]], [90]])
      i+=1
      rounded_vias.append([[vias[i][0] - radius, vias[i][1]],[vias[i][0] - radius, vias[i][1] - radius], [vias[i][0], vias[i][1] - radius], [-90]])
      i+=1
  else:
    while i in range(len(vias)): # discharge, [startpoint, midpoint]
      rounded_vias.append([[vias[i][0], vias[i][1] - radius],[vias[i][0] - radius, vias[i][1] - radius], [vias[i][0] - radius, vias[i][1]], [90]])
      i+=1
      rounded_vias.append([[vias[i][0] + radius, vias[i][1]],[vias[i][0] + radius, vias[i][1] + radius], [vias[i][0], vias[i][1] + radius], [-90]])
      i+=1
      rounded_vias.append([[vias[i][0], vias[i][1] - radius],[vias[i][0] + radius, vias[i][1] - radius], [vias[i][0] + radius, vias[i][1]], [-90]])
      i+=1
      rounded_vias.append([[vias[i][0] - radius, vias[i][1]],[vias[i][0] - radius, vias[i][1] + radius], [vias[i][0], vias[i][1] + radius], [90]])
      i+=1
  channel['rounded_vias'] = rounded_vias

def compute_module_offsets(result):
  # some post processing
  # during computation, supply_offset is a positive value for technical reasons; now change it to negative so it can be used as a coordinate
  result['supply_offset'] = -result['supply_offset']
  result['refeed_stubs_length'] = result['discharge_offset'] * result['refeed_stubs_relative_length'] 
  result['total_channel_length'] = compute_total_channel_length(result)
  n_modules = len(result['modules'])
  for i in range(n_modules):
    module = result['modules'][i]
    is_first = i == 0
    if not is_first:
      previous_module = result['modules'][i-1]

    module['channels']['c_supply']['actual_length'] = compute_via_length(module['channels']['c_supply'], [0,0], [0,result['supply_offset']])
    module['channels']['c_discharge']['actual_length'] = compute_via_length(module['channels']['c_discharge'], [0,0], [0,result['discharge_offset']])

    if is_first:
      module['module_x_offset'] = 0
    else:
      module['module_x_offset'] = previous_module['module_x_offset'] + previous_module['channels']['c_main']['length'] + previous_module['channels']['c_post']['length'] + module['channels']['c_connection']['length'] + module['channels']['c_post']['length']

def compute_total_channel_length(result):
  # compute statistics for total channel lengths of the chip
  total = 0
  for i in range(len(result['modules'])):
    module = result['modules'][i]
    total += module['channels']['c_connection']['length']
    total += module['channels']['c_pre']['length']
    total += module['channels']['c_main']['length']
    total += module['channels']['c_post']['length']
    total += module['channels']['c_supply']['length']
    total += module['channels']['c_supply_carry']['length']
    total += module['channels']['c_discharge']['length']
    total += module['channels']['c_discharge_carry']['length']
  return total

def compute_via_length(channel, start, end): 
  # computed actual via length to validate meanders against desired lengths (if necessary)
  total = 0
  previous = start
  for i in range(len(channel['vias'])):
    total += math.hypot(channel['vias'][i][0] - previous[0], channel['vias'][i][1] - previous[1])
    previous = channel['vias'][i]
  total += math.hypot(end[0] - previous[0], end[1] - previous[1])
  return total

def read_input_file(input_file):
  with open(input_file, 'r') as f:
    input = json.load(f)
  return input

def write_output_file(result, output_file):
  if os.path.dirname(output_file):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
  with open(output_file, 'w') as f:
    json.dump(result, f, indent=2)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('inputfile', type=str)
  parser.add_argument('outputfile', type=str)
  args = parser.parse_args()
  run(args.inputfile, args.outputfile)
