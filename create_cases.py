import argparse
import os
import json
import itertools
from ooc_da import solve

def run(outputpath):
  inputdir = 'architectures'

  # change these values to create different case dirs
  inputfiles = ['male_simple']
  variations = {
    'spacing': [0.5e-3,1.5e-3],
    'viscosity': [9.3e-4, 1.1e-3, 3e-3],
    'shear': [1.2, 2]
  }

  

  for inputfile in inputfiles:
    outdir = os.path.join(outputpath, inputfile)
    print('Creating cases for {}.'.format(inputfile))
    if os.path.isdir(outdir):
      raise Exception('Directory {} already exists. Aborting to make sure nothing is overriden.'.format(inputfile))
    os.mkdir(outdir)
    with open(os.path.join(inputdir, '{}.json'.format(inputfile)), 'r') as f:
      config = json.load(f)
    allvariations = dict(variations)
    i = 0
    mapNames = {}
    for key, values in variations.items():
      allvariations[key].append(config[key])
      mapNames[i] = key
      i += 1

    count = 0
    for es in itertools.product(*[values for (key, values) in allvariations.items()]):
      case_dir = os.path.join(outdir, '{}_{}'.format(inputfile, count))
      os.mkdir(case_dir)
      config_copy = dict(config)
      for i in range(len(es)):
        config_copy[mapNames[i]] = es[i]
        pass

      result = solve(config_copy)
      
      file_path = os.path.join(case_dir, 'config.json')
      with open(file_path, 'w+') as f:
        json.dump(result, f, indent=2)
      count += 1
      
      


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('outputpath', type=str)
  args = parser.parse_args()
  run(args.outputpath)