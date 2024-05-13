# Definitions for the Jupyter Notebook
from IPython.display import display, HTML, Javascript
import ipywidgets as widgets
import json
import os
import pyvista as pv
import warnings


def display_architectures(input_directory, filename, output_path):
    data = load_json(input_directory, filename)

    global widgets_ui

    widgets_list = create_widgets(data)
    widgets_ui = widgets.VBox(widgets_list)

    save_button = widgets.Button(description="Save Changes", button_style='info')
    save_button.on_click(lambda b: save_json(data, widgets_ui, output_path))

    separator_chip = widgets.HTML(
    value="<hr><h4 style='text-align:left;'>Chip Details</h4><hr>",
    layout=widgets.Layout(margin="10px 0 10px 0")
    )
    display(HTML("<style>.widget-label { display: none; }</style>"))

    display(separator_chip, widgets_ui, save_button)

def load_json(inputdir, filename):
    with open(os.path.join(inputdir, filename), 'r') as file:
        return json.load(file)

def create_widgets(data, path_prefix=''):
    widgets_list = []

    separator_modules = widgets.HTML(
        value="<hr><h4 style='text-align:left;'>Modules</h4><hr>",
        layout=widgets.Layout(margin="10px 0 10px 0")
    )

    for key, value in data.items():
        current_path = f"{path_prefix}.{key}" if path_prefix else key
        label_for_display = current_path.split('.')[-1]  # Get the last part of the path for display

        if isinstance(value, dict):
            nested_widgets = create_widgets(value, current_path)
            nested_box = widgets.VBox([widgets.HTML(value=f"<strong>{label_for_display}</strong>")] + nested_widgets)
            widgets_list.append(nested_box)
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            list_items = [create_widgets(item, f"{current_path}[{index}]") for index, item in enumerate(value)]

            widgets_list.append(separator_modules)
            for index, item in enumerate(value):
                module_widgets = create_widgets(item, f"{current_path}[{index}]")
                remove_button = widgets.Button(description="Remove Module", button_style='danger')
                remove_button.on_click(lambda b, idx=index: remove_module(data, idx, widgets_ui))
                module_widgets.append(remove_button)
                module_box = widgets.VBox([widgets.HTML(value=f"<strong>Module #{index + 1}</strong>")] + module_widgets)
                widgets_list.append(module_box)
            add_button = widgets.Button(description="Add Module", button_style='success')
            add_button.on_click(lambda b: add_module(data, widgets_ui))
            widgets_list.append(add_button) 
            
        else:
            widget = widgets.Text(value=str(value), description=current_path)
            label_html = widgets.HTML(value=f"<label style='width:150px;'>{label_for_display}:</label>")
            hbox = widgets.HBox([label_html, widget])
            widgets_list.append(hbox)


    return widgets_list


def add_module(data, widgets_ui): 
    new_module = {
        "id": "", "type": "", "real_volume": 0, "real_mass": 0,
        "number_of_layers": 0, "cell_layer_thickness": 0,
        "perfusion_rate": 0, "comment": ""
    }
    data['modules'].append(new_module)
    update_ui(data, widgets_ui)

def remove_module(data, index, widgets_ui):
    if index < len(data['modules']):
        data['modules'].pop(index)
    update_ui(data, widgets_ui)

def update_ui(data, widgets_ui):
    new_widgets_list = create_widgets(data)
    widgets_ui.children = new_widgets_list


def save_json(data, container, output_path):
    def set_value(obj, path, value):
        elements = path.split('.')
        current = obj
        for element in elements[:-1]:
            if '[' in element and ']' in element:
                key, idx = element[:-1].split('[')
                current = current[key][int(idx)]
            else:
                current = current.get(element, {})
        key = elements[-1]
        try:
            if '.' in value or 'e' in value:
                current[key] = float(value)
            else:
                current[key] = int(value)
        except ValueError:
            current[key] = value

    def find_text_widgets(container):
        """Recursively find all Text widgets in the given container."""
        widgets_found = []
        for child in container.children:
            if isinstance(child, widgets.Text):
                widgets_found.append(child)
            elif hasattr(child, 'children'):  # This checks for any type of container widget
                widgets_found.extend(find_text_widgets(child))
        return widgets_found

    text_widgets = find_text_widgets(container)
    for widget in text_widgets:
        set_value(data, widget.description, widget.value)

    with open(output_path, 'w') as file:
        json.dump(data, file, indent=4)
    print(f"Data saved to {output_path}")


def display_output_widgets():
    # Initial Global Variable Definitions
    global outputpath, outputfolder, outputfile

    # Initialize with default values
    outputpath = 'architectures'
    outputfolder = 'design_result'
    outputfile = 'design_result.json'

    # Output directory and file configuration
    outputpath_widget = widgets.Text(value='architectures', description='outputpath:', style={'description_width': 'initial'})
    outputfolder_widget = widgets.Text(value='design_result', description='Output Folder:', style={'description_width': 'initial'})
    outputfile_widget = widgets.Text(value='design_result.json', description='Output File:', style={'description_width': 'initial'})

    def update_settings(*args):
        global outputpath, outputfolder, outputfile

        outputpath = outputpath_widget.value
        outputfolder = outputfolder_widget.value
        outputfile = outputfile_widget.value

        # print("Variables updated")  # Debugging: Confirm updates
        
        
    # Attach observers to the respective widgets
    outputpath_widget.observe(update_settings, names='value')
    outputfolder_widget.observe(update_settings, names='value')
    outputfile_widget.observe(update_settings, names='value')

    def save_changes(b):
        for widget in simple_and_nested_editor.children:
            if isinstance(widget, widgets.Text):
                config[widget.description] = widget.value

    display(outputpath_widget, outputfolder_widget, outputfile_widget)

def display_chip_size_widgets():
    # Initial Global Variable Definitions
    global bottom, top, sides, pump_radius

    bottom = 300e-6 * 2
    top = 300e-6 * 2
    sides = 300e-6 * 5
    pump_radius = 300e-6 * 2

    # Define widgets for the parameters
    bottom_widget = widgets.FloatText(value=300e-6 * 2, description='Bottom [m]:', step=1e-6, style={'description_width': 'initial'})
    top_widget = widgets.FloatText(value=300e-6 * 2, description='Top [m]:', step=1e-6, style={'description_width': 'initial'})
    sides_widget = widgets.FloatText(value=300e-6 * 5, description='Sides [m]:', step=1e-6, style={'description_width': 'initial'})
    pump_radius_widget = widgets.FloatText(value=300e-6 * 2, description='Pump Tubing Radius [m]:', step=1e-6, style={'description_width': 'initial'})

    def update_settings(*args):
        global bottom, top, sides, pump_radius

        bottom = bottom_widget.value
        top = top_widget.value
        sides = sides_widget.value
        pump_radius = pump_radius_widget.value

        print("Variables updated")  # Debugging: Confirm updates
        
        
    # Attach observers to the respective widgets
    bottom_widget.observe(update_settings, names='value')
    top_widget.observe(update_settings, names='value')
    sides_widget.observe(update_settings, names='value')
    pump_radius_widget.observe(update_settings, names='value')

    display(bottom_widget, top_widget, sides_widget, pump_radius_widget)


def display_bool_widgets():
    # Initial Global Variable Definitions
    global channel_negative, unit_conversion_to_mm

    # Initialize with default values
    channel_negative = True
    unit_conversion_to_mm = True

    # Define bool widgets
    channel_negative_widget_input = widgets.Checkbox(
        value=True,  # Default checked
        description='Channel Negative',
        disabled=False,
        style={'description_width': 'initial'}
    )
    channel_negative_widget_output = widgets.Checkbox(
        value=channel_negative,  # Bind value to global variable
        description='Channel Negative',
        disabled=True,  # Disabled for output
        style={'description_width': 'initial'}
    )

    unit_conversion_to_mm_widget_input = widgets.Checkbox(
        value=True,  # Default checked
        description='Unit Conversion to mm',
        disabled=False,
        style={'description_width': 'initial'}
    )
    unit_conversion_to_mm_widget_output = widgets.Checkbox(
        value=unit_conversion_to_mm,  # Bind value to global variable
        description='Unit Conversion to mm',
        disabled=True,  # Disabled for output
        style={'description_width': 'initial'}
    )

    def update_settings(*args):
        global channel_negative, unit_conversion_to_mm

        channel_negative = channel_negative_widget_input.value
        unit_conversion_to_mm = unit_conversion_to_mm_widget_input.value

        print("Variables updated")  # Debugging: Confirm updates

        # Update output widgets with new values
        channel_negative_widget_output.value = channel_negative
        unit_conversion_to_mm_widget_output.value = unit_conversion_to_mm

    # Attach observers to the respective input widgets
    channel_negative_widget_input.observe(update_settings, names='value')
    unit_conversion_to_mm_widget_input.observe(update_settings, names='value')

    # Display input widgets for input
    display(channel_negative_widget_input, unit_conversion_to_mm_widget_input)

    # Display output widgets (read-only) for output
    display(channel_negative_widget_output, unit_conversion_to_mm_widget_output)


def convert_to_floats(data):
    if isinstance(data, dict):
        return {k: convert_to_floats(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_floats(item) for item in data]
    elif isinstance(data, str):
        # Try to convert numerical strings to floats
        try:
            return float(data) if '.' in data or 'e' in data.lower() else int(data)
        except ValueError:
            return data
    else:
        return data
    
    
def display_2D_svg(svg_file):
    # Path to your SVG file
    svg_file_path = svg_file

    style = "<style>svg{width:100% !important;height:100% !important;</style>"
    display(HTML(style))
    display(HTML(svg_file))


def display_3D_mesh(stl_file):
    # Suppress warnings
    warnings.filterwarnings('ignore')


    # Load the STL file
    mesh = pv.read(stl_file)
    mesh.rotate_z(90)


    # Plot the mesh with internal edges visible
    plotter = pv.Plotter()
    plotter.add_mesh(mesh, show_edges=True, color='white', opacity=0.5)
    plotter.add_mesh(mesh.extract_all_edges(), color='black', line_width=0.5)

    plotter.show()