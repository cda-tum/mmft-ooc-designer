import re
import os
import argparse
import json
import math

vector_pattern = '([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)[\t ]+[(][\t ]*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)[\t ]+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)[\t ]+([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)[\t ]*[)][\t ]*'
config_name = 'config.json'
channel_map_name = 'channelMap.json'
file_name = 'volFieldValue.dat'
postprocessing_folder = 'postProcessing'

def run(path, resultfile):
  cases = []

  if os.path.isfile(os.path.join(path, config_name)):
    print('{} found. Processing as case directory.'.format(config_name))
    cases = [extract_case(path)]
  else:
    print('{} not found. Processing subdirectories.'.format(config_name))
    cases = extract_cases(path)

  results = extract_results(cases)
  with open(resultfile, 'w') as f:
    json.dump(results, f, indent=2)

def extract_results(cases):
  results = {
    'cases': [],
    'overall': []
  }
  for case in cases:
    result = {
      'n_modules':len(case['modules'])
    }
    result['module_flowrate_deviations'] = {
      'calculated_flowrates': [ m['channels']['c_main']['flowrate'] for m in case['modules']],
      'measured_flowrates': [ m['channels']['c_main']['measured_flowrate'] for m in case['modules']],
      'values': [1 - m['channels']['c_main']['measured_flowrate_relative_deviation'] for m in case['modules']],
      'absvalues': [abs(1 - m['channels']['c_main']['measured_flowrate_relative_deviation']) for m in case['modules']]
    }
    result['module_flowrate_deviations']['max'] = max(result['module_flowrate_deviations']['absvalues'])
    result['module_flowrate_deviations']['avg'] = sum(result['module_flowrate_deviations']['absvalues']) / result['n_modules']

    result['module_perfusion_deviations'] = {
      'calculated_flowrates': [ m['channels']['c_connection']['flowrate'] for m in case['modules']],
      'measured_flowrates': [ m['channels']['c_connection']['measured_flowrate'] for m in case['modules']],
      'values': [1 - m['measured_perfusion_relative_deviation'] for m in case['modules']],
      'absvalues': [abs(1 - m['measured_perfusion_relative_deviation']) for m in case['modules']]
    }
    result['module_perfusion_deviations']['max'] = max(result['module_perfusion_deviations']['absvalues'])
    result['module_perfusion_deviations']['avg'] = sum(result['module_perfusion_deviations']['absvalues']) / result['n_modules']

    results['cases'].append(result)

  results['overall'] = {
    'module_flowrate_deviations': {},
    'module_perfusion_deviations': {}
  }
  results['overall']['module_flowrate_deviations']['max'] = max([case['module_flowrate_deviations']['max'] for case in results['cases']])
  results['overall']['module_flowrate_deviations']['avg'] = sum([case['module_flowrate_deviations']['avg'] * case['n_modules'] for case in results['cases']]) / sum([case['n_modules'] for case in results['cases']])
  results['overall']['module_perfusion_deviations']['max'] = max([case['module_perfusion_deviations']['max'] for case in results['cases']])
  results['overall']['module_perfusion_deviations']['avg'] = sum([case['module_perfusion_deviations']['avg'] * case['n_modules'] for case in results['cases']]) / sum([case['n_modules'] for case in results['cases']])
  return results
    

def extract_cases(dir_path):
  dirs = [f.path for f in os.scandir(dir_path) if f.is_dir()]
  configs = []
  for dir in dirs:
    config = extract_case(dir)
    configs.append(config)
  return configs

def extract_case(case_path):
  with open(os.path.join(case_path, config_name), 'r') as f:
    config = json.load(f)
  with open(os.path.join(case_path, channel_map_name), 'r') as f:
    channel_map = json.load(f)

  for i in range(len(config['modules'])):
    module = config['modules'][i]
    for c_id, channel in module['channels'].items():
      v1 = read_channel_measure_velocity(case_path, i, c_id, channel_map)
      if v1 is None:
        continue
      v2 = get_velocity(v1[1], v1[2], v1[3], True, c_id)
      channel['measured_flowrate'] = v2 * channel['height'] * channel['width']
      channel['measured_flowrate_relative_deviation'] = channel['measured_flowrate'] / channel['flowrate']
      
    module['measured_perfusion'] = module['channels']['c_connection']['measured_flowrate'] / module['channels']['c_main']['measured_flowrate']
    module['measured_perfusion_relative_deviation'] = module['measured_perfusion'] / module['perfusion_rate']
  return config

def get_velocity(x, y, z, norm, c_id):
  if norm:
    return math.hypot(x, y, z)
  else:
    if c_id == 'c_main' or c_id == 'c_connection' or c_id == 'c_pre' or c_id == 'c_post' or c_id == 'c_supply_carry':
      return x
    elif c_id == 'c_discharge_carry':
      return -x
    elif c_id == 'c_supply' or c_id == 'c_discharge':
      return y
    else:
      raise 'channel unknown'

  
def read_channel_measure_velocity(case_path, module_index, channel, channel_map):
  id = '{}_{}'.format(channel_map['velocitiesPrefix'], channel_map['modules'][module_index]['channels'][channel])
  if os.path.isdir(os.path.join(case_path, postprocessing_folder, id)):
    return extract_last_line_vector(os.path.join(case_path, postprocessing_folder, id, '0', file_name))
  else:
    return None

def extract_last_line_vector(file_path):
  with open(file_path, 'r') as f:
    for line in f:
        pass
    last_line = line

  match = re.match(vector_pattern, last_line)
  return [float(n) for n in match.groups()]
  

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('path', type=str)
  parser.add_argument('resultfile', type=str)
  args = parser.parse_args()
  run(args.path, args.resultfile)