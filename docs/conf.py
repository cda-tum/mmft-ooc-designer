# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('../.'))


# -- Project information -----------------------------------------------------

project = 'mmft-ooc-designer'
copyright = '2024, Chair for Design Automation, Technical University of Munich'
author = 'Chair for Design Automation, Technical University of Munich'

# The full version, including alpha/beta/rc tags
release = '1.0.0'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',   # Import the autodoc extension
    'sphinx.ext.napoleon',  # Support for Google and NumPy style docstrings
    'sphinx.ext.todo',      # Support TODOs
    'sphinx.ext.viewcode',  # Add links to highlighted source code
    'sphinx.ext.intersphinx',  # Link to other projects' documentation
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

pygments_style = "colorful"

add_module_names = False




# -- Options for HTML output -------------------------------------------------

html_theme = 'alabaster'
html_static_path = ["_static"]
html_theme_options = {
    "light_logo": "mmft_light.png",
    "dark_logo": "mmft_light.png",
    "source_repository": "https://github.com/cda-tum/mmft-ooc-designer/",
    "source_branch": "main",
    "source_directory": "docs/",
    "navigation_with_keys": True,
}