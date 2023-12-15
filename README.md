# Design Automation for Organs-on-a-chip

A design automation method for organs-on-chip developed by the [Chair for Design Automation](https://www.cda.cit.tum.de/) at the [Technical University of Munich](https://www.tum.de/) as part of the Munich MicroFluidic Toolkit (MMFT). This method includes the orchestration of several aspects like the size of organ modules, the required shear stress on membranes, the dimensiones and geometry of channels, pump pressures, etc., and by this improves the design task for organs-on-chip. More details about the implementation can be found in:

M. Emmerich, P. Ebner, and R. Wille. Design Automation for Organs-on-Chip. In Design, Automation and Test in Europe (DATE). 2024. 

For more information about our work on Microfluidics, please visit https://www.cda.cit.tum.de/research/microfluidics/.

If you have any questions, feel free to contact us via microfluidics.cda@xcit.tum.de or by creating an issue on GitHub.

## System Requirements
Tested with Python 3.9.14.

## Run
To run the script via the command line type:
```bash
    python ooc-da.py inputfile.json outputfile.json
```

### Example
```bash
    python ooc-da.py architectures/ooc_male_simple.json outputconfig.json
```