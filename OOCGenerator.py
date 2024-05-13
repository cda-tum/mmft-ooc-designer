# stl-generation adapted for ooc-da results

import numpy as np
from stl import mesh
import math
import json
from collections import defaultdict

import matplotlib.pyplot as plt


eps = 1e-10

def read_in_network_file(filename):
    '''
    Read in the network file.json created by the ooc-da.py code and return the nodes, pumps, channels, arcs and organ_channels.
    '''
    nodes = []
    pumps = []
    channels = []
    arcs = []
    organ_channels = []

    with open(filename) as f:
        json_data = json.load(f)
        module_y_offset = json_data['module_y_offset']
        discharge_y_offset = -json_data['discharge_offset']
        supply_y_offset = json_data['supply_offset'] # because the y axis is reversed in the definition
        z = 0.0

        channel_height = json_data['channel_height'] * 2 # TODO this is just for the print
        # channel_height = 0.0003 # TODO this is just for the print

        connection_node = None
        discharge_carry_node = None
        supply_carry_node = None

        node_id_counter = 0
        num_extra_nodes = 0
        supply_and_carry_adaption = 0

        # ADD MODULE NODES AND CHANNELS
        for m in reversed(json_data['modules']): # Their order determines their ID
            delay = num_extra_nodes #TODO rename this variable
            module_x_offset = m['module_x_offset']
            if connection_node is None or supply_carry_node is None or discharge_carry_node is None:
                # technically these nodes are doubled since they will be created for the next module again
                connection_node = [module_x_offset + m['channels']['c_main']['length'] + m['channels']['c_post']['length'], module_y_offset, z]
                discharge_carry_node = [module_x_offset + m['channels']['c_main']['length'] + m['channels']['c_post']['length'], module_y_offset - discharge_y_offset, z]
                supply_carry_node = [module_x_offset - m['channels']['c_pre']['length'], module_y_offset + supply_y_offset, z]
                nodes.extend([connection_node, discharge_carry_node, supply_carry_node])
            # else: 
            #     connection_node = next_connection_node
            #     discharge_carry_node = next_discharge_carry_node
            #     supply_carry_node = next_supply_carry_node

            main_pre_node = [module_x_offset, module_y_offset, 0.0]
            main_post_node = [module_x_offset + m['channels']['c_main']['length'], module_y_offset, z]
            connection_pre_node = [module_x_offset - m['channels']['c_pre']['length'], module_y_offset, z]
            
            next_connection_node = [module_x_offset - m['channels']['c_pre']['length'] - m['channels']['c_connection']['length'], module_y_offset, z]
            next_discharge_carry_node = [module_x_offset + m['channels']['c_main']['length'] + m['channels']['c_post']['length'] - m['channels']['c_discharge_carry']['length'], module_y_offset - discharge_y_offset, z]
            next_supply_carry_node = [module_x_offset - m['channels']['c_pre']['length'] - m['channels']['c_supply_carry']['length'], module_y_offset + supply_y_offset, z]
            
            nodes.extend([main_pre_node, main_post_node, connection_pre_node, next_connection_node, next_discharge_carry_node, next_supply_carry_node]) # TODO check if this is changed each loop i.e. the list is altered

            for channel_name, channel in m['channels'].items(): # TODO this depends on the input (in ooc there are vias and rounded vias, here its line segments and arcs)
            # channel_name, channel = m['channels'].items()

                connection_node_id = node_id_counter - delay
                discharge_carry_node_id = node_id_counter + 1 - delay
                supply_carry_node_id = node_id_counter + 2 - delay#- num_extra_nodes

                main_pre_node_id = node_id_counter + 3 #- num_extra_nodes
                main_post_node_id = node_id_counter + 4 #- num_extra_nodes
                connection_pre_node_id = node_id_counter + 5 #- num_extra_nodes

                next_connection_node_id = node_id_counter + 6 #- num_extra_nodes
                next_discharge_carry_node_id = node_id_counter + 7 #- num_extra_nodes
                next_supply_carry_node_id = node_id_counter + 8 #- num_extra_nodes

                if channel_name == 'c_main':
                    channels.append([main_pre_node_id, main_post_node_id, channel['width']]) # c_main # TODO maybe exchange this with nodeId!!
                    organ_channels.append([main_pre_node_id, main_post_node_id])
                if channel_name == 'c_pre':
                    channels.append([connection_pre_node_id, main_pre_node_id, channel['width']]) # c_pre
                if channel_name == 'c_post':
                    channels.append([main_post_node_id, connection_node_id, channel['width']]) # c_post
                if channel_name == 'c_connection':
                    channels.append([next_connection_node_id, connection_pre_node_id, channel['width']]) # c_connection

                if channel_name == 'c_supply_carry':
                    channels.append([next_supply_carry_node_id, supply_carry_node_id , channel['width']]) # c_supply_carry
                if channel_name == 'c_discharge_carry':
                    channels.append([discharge_carry_node_id, next_discharge_carry_node_id, channel['width']]) # c_discharge_carry

                if channel_name == 'c_supply': #c_supply
                    if 'rounded_vias' in channel:
                        via = channel['rounded_vias']
                        num_pieces = len(channel['rounded_vias'])
                        num_extra_nodes += num_pieces * 2
                        current_start_node = connection_pre_node_id
                        for i in range(num_pieces + 1):
                            if i == num_pieces:
                                end_node = supply_carry_node_id
                                channels.append([current_start_node, end_node, channel['width']])
                            else:
                                end_node = via[i][0] + [channel['width']]
                                end_node.append(z)
                                end_node[0] += module_x_offset - m['channels']['c_pre']['length']
                                nodes.append(end_node)
                                channels.append([current_start_node, len(nodes)-1, channel['width']])
                                start_node = end_node
                                center = via[i][1] 
                                center[0] += module_x_offset - m['channels']['c_pre']['length']
                                arc_end_node = via[i][2] 
                                arc_end_node.append(z)
                                arc_end_node[0] += module_x_offset - m['channels']['c_pre']['length']
                                nodes.append(arc_end_node)
                                arc_direction = via[i][3]
                                arcs.append([len(nodes)-2, center, len(nodes)-1, channel['width'], arc_direction])
                            current_start_node = len(nodes)-1 #end_node  # Update start node for next segment
                    else:
                        channels.append([supply_carry_node_id, connection_pre_node_id, channel['width']])
                if channel_name == 'c_discharge': #c_discharge
                    if 'rounded_vias' in channel:
                        via = channel['rounded_vias']
                        num_pieces = len(channel['rounded_vias'])
                        num_extra_nodes = num_pieces * 2 # because discharge is listed before supply
                        current_start_node = connection_node_id

                        for i in range(num_pieces + 1):
                            if i == num_pieces:
                                end_node = discharge_carry_node_id # adapted to take the added nodes into account
                                channels.append([current_start_node, end_node, channel['width']])
                            else:
                                end_node = via[i][0] + [channel['width']]
                                end_node.append(z)
                                end_node[0] += module_x_offset + m['channels']['c_main']['length'] + m['channels']['c_post']['length']
                                nodes.append(end_node)
                                channels.append([current_start_node, len(nodes)-1, channel['width']])
                                start_node = end_node
                                center = via[i][1]
                                center[0] += module_x_offset + m['channels']['c_main']['length'] + m['channels']['c_post']['length']
                                arc_end_node = via[i][2]
                                arc_end_node.append(z)
                                arc_end_node[0] += module_x_offset + m['channels']['c_main']['length'] + m['channels']['c_post']['length']
                                nodes.append(arc_end_node)
                                arc_direction = via[i][3]
                                arcs.append([len(nodes)-2, center, len(nodes)-1, channel['width'], arc_direction])
                            current_start_node = len(nodes)-1 #end_node  # Update start node for next segment
                    else:
                        channels.append([connection_node_id, discharge_carry_node_id, channel['width']])

            node_id_counter = len(nodes) - 3
        
        # ADD THE REST OF THE CHANNELS AND NODES OF THE GEOMETRY OOC DEFINITION, INCLUDING THE PUMPS
        pump_inflow_node = next_supply_carry_node.copy()
        pump_inflow_node[0] -= json_data['pump_stubs_length']

        pump_outflow_node = next_discharge_carry_node.copy()
        pump_outflow_node[0] -= json_data['pump_stubs_length']

        refeed_pump_inflow_node = next_connection_node.copy()
        refeed_pump_inflow_node[1] += json_data['refeed_stubs_length']

        refeed_pump_outflow_node = next_discharge_carry_node.copy()
        refeed_pump_outflow_node[1] -= json_data['refeed_stubs_length']

        width = m['channels']['c_supply_carry']['width']
        nodes.append(pump_inflow_node)
        pumps.append(len(nodes) - 1)
        channels.append([len(nodes) - 1, next_supply_carry_node_id, width])
        width = m['channels']['c_discharge_carry']['width']
        nodes.append(pump_outflow_node)
        pumps.append(len(nodes) - 1)
        channels.append([len(nodes) - 1, next_discharge_carry_node_id, width])
        nodes.append(refeed_pump_inflow_node)
        pumps.append(len(nodes) - 1)
        width = m['channels']['c_connection']['width']
        channels.append([len(nodes) - 1, next_connection_node_id, width])
        nodes.append(refeed_pump_outflow_node)
        pumps.append(len(nodes) - 1)
        channels.append([len(nodes) - 1, next_discharge_carry_node_id, width])

    return nodes, pumps, channels, arcs, channel_height, organ_channels

def define_channels_per_node(nodes: list, channels: list): # as a dictionary?
    '''
    Define all channels that are connected to each node in the network.
    '''
    channels_per_node = defaultdict(list)

    for node in range(len(nodes)):
        for channel in channels:
            if channel[0] == node or channel[1] == node:
                channels_per_node[node].append(channel)

    return channels_per_node

def define_quads_at_nodes(nodes: list, channels_per_node: dict):
    '''
    Define quads around each node as a basis to later extrude the 1D channel definition to a 2D and then 3D geometry.
    '''
    # i.e.  ---3-----2
    #          |  x  | l
    #       ---0-----1
    #          |  w  |
    quads = {} # contains node ID and width and height of the quad surrounding that node

    for node in channels_per_node: # this doesn't yet include angled channels!
        quad_widths = []
        quad_lengths = []
        for channel in channels_per_node[node]: # TODO include height top bottom and left right to include the connection of channels with different widths
            width = channel[2]
            # loop through all channels here 
            if math.isclose(nodes[channel[0]][1], nodes[channel[1]][1], rel_tol=eps): # horizontal channel
                length = abs(nodes[channel[0]][1] - nodes[channel[1]][1])
                quad_length = width
                quad_lengths.append(width)

            elif math.isclose(nodes[channel[0]][0], nodes[channel[1]][0], rel_tol=eps): # vertical channel
                length = abs(nodes[channel[0]][0] - nodes[channel[1]][0])

                quad_width = width
                quad_widths.append(width)
            else:
                print("Error: channel is not horizontal or vertical")
                print("channel:", channel)

        quads[node] = [quad_widths, quad_lengths]
    return quads

def define_channel_faces_xy(nodes: list, channels: list, quad_list: list):
    """
    Define channel faces on the xy plane.
    """
    channel_faces_xy = []

    for channel in channels:
            quad_1 = quad_list[channel[0]]
            if len(quad_1) == 2:
                quad_1 = [quad_list[channel[0]][0],quad_list[channel[0]][0],quad_list[channel[0]][1],quad_list[channel[0]][1]]

            quad_2 = quad_list[channel[1]]
            if len(quad_2) == 2:
                quad_2 = [quad_list[channel[0]][0],quad_list[channel[0]][0],quad_list[channel[0]][1],quad_list[channel[0]][1]]

            if math.isclose(nodes[channel[0]][1], nodes[channel[1]][1], rel_tol=eps): # horizontal channel
                if nodes[channel[0]][0] < nodes[channel[1]][0]: # channel goes from left to right
                    channel_faces_xy.append([quad_1[1], quad_2[0], quad_2[3], quad_1[2]])
                elif nodes[channel[0]][0] > nodes[channel[1]][0]: # channel goes from right to left
                    channel_faces_xy.append([quad_2[1], quad_1[0], quad_1[3], quad_2[2]])
            elif math.isclose(nodes[channel[0]][0], nodes[channel[1]][0], rel_tol=eps): # vertical channel
                if nodes[channel[0]][1] > nodes[channel[1]][1]: # channel goes from top to bottom
                    channel_faces_xy.append([quad_2[3], quad_2[2], quad_1[1], quad_1[0]])
                elif nodes[channel[0]][1] < nodes[channel[1]][1]: # channel goes from bottom to top
                    channel_faces_xy.append([quad_1[3], quad_1[2], quad_2[1], quad_2[0]])

    return channel_faces_xy


def define_vertices_and_quad_list(nodes: list, quads: list, height: float):
    """
    Get the quad definition at each node, at each corner point of the quad a vertice (coordinate) is defined, additionally a quad list defines the vertices at each quad.
    """
    quad_faces_xy = []
    vertices = []
    quad_list = []
    # z = nodes[node][2] # TODO maybe shift back to this ?? 
    z = 0.0

    for j in range(2):    
        for i, node in enumerate(quads):
            if len(quads[node][0]) > 0 and len(quads[node][1]) > 0: # if the quad has a width and length
                if len(quads[node][0]) > 1:
                    width1 = quads[node][0][0]
                    width2 = quads[node][0][1]
                elif len(quads[node][0]) == 1:
                    width1 = width2 = quads[node][0][0]
                if len(quads[node][1]) > 1:
                    length1 = quads[node][1][0]
                    length2 = quads[node][1][1]
                elif len(quads[node][1]) == 1:
                    length1 = length2 = quads[node][1][0]
                vertices.append([nodes[node][0] - width1/2, nodes[node][1] - length2/2, z + height])
                vertices.append([nodes[node][0] + width1/2, nodes[node][1] - length1/2, z + height])
                vertices.append([nodes[node][0] + width2/2, nodes[node][1] + length1/2, z + height])
                vertices.append([nodes[node][0] - width2/2, nodes[node][1] + length2/2, z + height])
                quad_faces_xy.append([vertices[len(vertices) - 4], vertices[len(vertices) - 3], vertices[len(vertices) - 2], vertices[len(vertices) - 1]])
                quad_list.append([len(vertices) - 4, len(vertices) - 3, len(vertices) - 2, len(vertices) - 1])
            elif len(quads[node][0]) == 0: # quad has no width!
                if len(quads[node][1]) > 1:
                    length1 = quads[node][1][0]
                    length2 = quads[node][1][1]
                elif len(quads[node][1]) == 1:
                    length1 = length2 = quads[node][1][0]
                vertices.append([nodes[node][0], nodes[node][1] - length2/2, z + height])
                vertices.append([nodes[node][0], nodes[node][1] + length1/2, z + height])
                quad_list.append([len(vertices) - 2, len(vertices) - 2, len(vertices) - 1, len(vertices) - 1])
            elif len(quads[node][1]) == 0: # quad has no length!
                if len(quads[node][0]) > 1:
                    width1 = quads[node][0][0]
                    width2 = quads[node][0][1]
                elif len(quads[node][0]) == 1:
                    width1 = width2 = quads[node][0][0]
                vertices.append([nodes[node][0] - width1/2, nodes[node][1], z + height])
                vertices.append([nodes[node][0] + width2/2, nodes[node][1], z + height])
                quad_list.append([len(vertices) - 2, len(vertices) - 1, len(vertices) - 1, len(vertices) - 2])
        height = -height # This ensures that the 3D channel extrusion is equal in - z and + z direction, with the 1D definition as a center of the channel 
    vertices = np.array(vertices)

    return vertices, quad_list

def define_quad_faces_xy(quad_list: list) -> list:
    """
    Define faces of the quads on the xy plane.
    """
    quad_faces = []
    for quad in quad_list:
        if len(quad) == 4:
            quad_faces.append([quad[0], quad[1], quad[2], quad[3]])
    return quad_faces


def define_faces_side(faces_xy_bottom: list, faces_xy_top: list) -> list:
    """
    Define the geometry faces of the channel sides based on the bottom and top faces.
    """
    faces_side = []

    if len(faces_xy_bottom) != len(faces_xy_top):
        print("Error! Number of faces on bottom and top are not equal")
        
    for i, face in enumerate(faces_xy_bottom):
        vertice_0 = faces_xy_bottom[i][0]
        vertice_1 = faces_xy_bottom[i][1]
        vertice_2 = faces_xy_bottom[i][2]
        vertice_3 = faces_xy_bottom[i][3]

        vertice_0_top = faces_xy_top[i][0]
        vertice_1_top = faces_xy_top[i][1]
        vertice_2_top = faces_xy_top[i][2]
        vertice_3_top = faces_xy_top[i][3]

        faces_side.extend([[vertice_0, vertice_1, vertice_1_top, vertice_0_top]])
        faces_side.extend([[vertice_1, vertice_2, vertice_2_top, vertice_1_top]])
        faces_side.extend([[vertice_2, vertice_3, vertice_3_top, vertice_2_top]])
        faces_side.extend([[vertice_3, vertice_0, vertice_0_top, vertice_3_top]])

    return faces_side

def discretize_arc(start, center, end, direction, num_segments: int, radius: float, height: float) -> list:
    """
    Discretize an arc into a series of points along the xy plane.
    """
    num_segments = num_segments

    # Define the arc angles
    vec_start = np.array(start) - np.array(center)
    vec_end = np.array(end)- np.array(center)

    if radius == 0:
        # radius = abs(start[1] - center[1] + start[0] - center[0] + start[2] - center[2])
        radius = abs(start[1] - center[1] + start[0] - center[0])
    else:
        radius = radius

    start_angle = np.arctan2(vec_start[1], vec_start[0]) + direction
    end_angle = np.arctan2(vec_end[1], vec_end[0])

    if height != 0:
        center[2] = -height/2 # required for the 3D extrusion to be equal in +z and -z direction only for the channel arcs! 

    arc_points = []
    for i in range(num_segments + 1):
        theta = start_angle + (end_angle - start_angle) * i / num_segments
        x = center[0] + radius * np.cos(theta)
        y = center[1] + radius * np.sin(theta)
        arc_points.append((x, y, center[2]))

    return arc_points

def discretize_arc_xz(start, center, end, direction, num_segments): # TODO combine discretize arc functions
    """
    Discretize an arc into a series of points along the xz plane.
    """
    # center, radius, direction = find_circle_center(start, midpoint, end)
    num_segments = num_segments

    if direction[0] == 0: 
        pump_type = False # In-/Outlet pump
        dir = -1
        
        if direction[1] == -1:
            dir = 1
        direction = 0
    else:
        pump_type = True # Refeed pump

        direction = 2 * np.pi

    # Define the arc angles
    vec_start = np.array(start) - np.array(center)
    vec_end = np.array(end)- np.array(center)

    radius = abs(start[0] - center[0] + start[2] - center[2])

    start_angle = np.arctan2(vec_start[2], vec_start[0]) + direction
    end_angle = np.arctan2(vec_end[2], vec_end[0])

    arc_points = []
    for i in range(num_segments + 1):
        theta = start_angle + (end_angle - start_angle) * i / num_segments
        if pump_type: 
            x = center[0] + radius * np.cos(theta)
            z = center[2] + radius * np.sin(theta)
            arc_points.append((x, center[1], z))
        else:
            y = center[1] - radius * np.cos(theta) * dir
            z = center[2] + radius * np.sin(theta)
            arc_points.append((center[0], y, z))
        
    return arc_points

def create_arc_triangles_side(arc_points, height): # TODO define direction as well ie z, y or x
    """
    Create triangles for the channel sides defined by arc points and height. (extrusion of a 1D arc in z-direction)
    """
    triangles = []
 
    for i in range(len(arc_points) - 1):
        p1, p2 = np.array(arc_points[i]), np.array(arc_points[i + 1])
        segment_vec = p2 - p1
        segment_length = np.linalg.norm(segment_vec)

        # Skip zero-length segments
        if segment_length == 0:
            continue

        p1_top = p1.copy()
        p1_top[2] += height
        p2_top = p2.copy()
        p2_top[2] += height

        triangles.append([tuple(p1), tuple(p2), tuple(p1_top)])
        triangles.append([tuple(p1_top), tuple(p2_top), tuple(p2)])

    return triangles

def create_arc_triangles_side_xz(arc_points, height, direction):
    """
    Create triangles for the pump connection sides defined by arc points and width. (extrusion of a 1D arc in z-direction) 
    """
    triangles = []

    for i in range(len(arc_points) - 1):
        p1, p2 = np.array(arc_points[i]), np.array(arc_points[i + 1])
        segment_vec = p2 - p1
        segment_length = np.linalg.norm(segment_vec)

        # Skip zero-length segments
        if segment_length == 0:
            continue

        if direction[1] != 0:
            p1_top = p1.copy()
            p1_top[0] += height
            p2_top = p2.copy()
            p2_top[0] += height
        else: 
            p1_top = p1.copy()
            p1_top[1] += height
            p2_top = p2.copy()
            p2_top[1] += height

        triangles.append([tuple(p1), tuple(p2), tuple(p1_top)])
        triangles.append([tuple(p1_top), tuple(p2_top), tuple(p2)])

    return triangles

def create_arc_triangles_xy(arc_points, arc_points2, height):
    '''
    Based on the input arc points, create the triangles for the xy plane.
    '''
    triangles = []
    
    for i in range(len(arc_points) - 1):
        p1A, p2A = np.array(arc_points[i]), np.array(arc_points[i + 1])
        p1B, p2B = np.array(arc_points2[i]), np.array(arc_points2[i + 1])

        segment_vec = p2A - p1A
        segment_length = np.linalg.norm(segment_vec)

        # Skip zero-length segments
        if segment_length == 0:
            continue

        triangles.append([tuple(p1A), tuple(p2A), tuple(p1B)])
        triangles.append([tuple(p1B), tuple(p2B), tuple(p2A)])

        # Analogous for the top/bottom triangles +z
        p1A_top = p1A.copy()
        p1A_top[2] += height
        p2A_top = p2A.copy()
        p2A_top[2] += height
        p1B_top = p1B.copy()
        p1B_top[2] += height
        p2B_top = p2B.copy()
        p2B_top[2] += height

        triangles.append([tuple(p1A_top), tuple(p2A_top), tuple(p1B_top)])
        triangles.append([tuple(p1B_top), tuple(p2B_top), tuple(p2A_top)])

    return triangles

def create_arc_triangles_xz(arc_points, arc_points2, width, direction):
    triangles = []
    
    for i in range(len(arc_points) - 1):
        p1A, p2A = np.array(arc_points[i]), np.array(arc_points[i + 1])
        p1B, p2B = np.array(arc_points2[i]), np.array(arc_points2[i + 1])

        segment_vec = p2A - p1A
        segment_length = np.linalg.norm(segment_vec)

        # Skip zero-length segments
        if segment_length == 0:
            continue

        triangles.append([tuple(p1A), tuple(p2A), tuple(p1B)])
        triangles.append([tuple(p1B), tuple(p2B), tuple(p2A)])

        xyz = 0
        d = 1

        if direction[0] == -1:
            xyz = 1
        elif direction[1] == 1: # TODO make this cleaner
            xyz = 0
        elif direction[1] == -1:
            xyz = 0
            # d = -1

        # Analogous for the top/bottom triangles +z
        p1A_top = p1A.copy()
        p1A_top[xyz] += width * (d)
        p2A_top = p2A.copy()
        p2A_top[xyz] += width * (d)
        p1B_top = p1B.copy()
        p1B_top[xyz] += width * (d)
        p2B_top = p2B.copy()
        p2B_top[xyz] += width * (d)

        triangles.append([tuple(p1A_top), tuple(p2A_top), tuple(p1B_top)])
        triangles.append([tuple(p1B_top), tuple(p2B_top), tuple(p2A_top)])

    return triangles

def create_arc_triangles_xy_2(arc_points, arc_points2, height, pump_type):
    triangles = []
    
    for i in range(len(arc_points) - 1):
        p1A, p2A = np.array(arc_points[i]), np.array(arc_points[i + 1])
        p1B, p2B = np.array(arc_points2[i]), np.array(arc_points2[i + 1])

        segment_vec = p2A - p1A
        segment_length = np.linalg.norm(segment_vec)

        # Skip zero-length segments
        if segment_length == 0:
            continue

        # Define surrounding box to be able to triangulate the top layer of the chip correctly
        p1A_top = p1A.copy()
        p1A_top[2] += height
        p2A_top = p2A.copy()
        p2A_top[2] += height

        # create a connection from the arc points to the side (in either +x or -x direction)
        nr_end_point = len(arc_points)-1
        delta_x = np.array(arc_points[0])[0] - np.array(arc_points[nr_end_point])[0]
        delta_y = np.array(arc_points[0])[1] - np.array(arc_points[nr_end_point])[1]

        p_corner = np.array(arc_points[0])
        if pump_type:
            p_corner[0] -= delta_x
        else:
            p_corner[1] -= delta_y
        p_corner[2] += height

        triangles.append([tuple(p1A_top), tuple(p2A_top), tuple(p_corner)]) # this works for the pump inlet and outlet

        # p1B_top = p1B.copy()
        # p1B_top[2] += height
        # p2B_top = p2B.copy()
        # p2B_top[2] += height

        # triangles.append([tuple(p1A_top), tuple(p2A_top), tuple(p1B_top)])
        # triangles.append([tuple(p1B_top), tuple(p2B_top), tuple(p2A_top)])

    corner_point = tuple(p_corner)

    return triangles, corner_point

def define_arcs(nodes, quad_list, vertices, arcs, numSegments, channel_height):
    """
    Define the arcs as triangles by using the discretize_arc, create_arc_triangles_side and create_arc_triangles_xy functions.
    """
    arc_triangles = []
    height = channel_height

    for arc in arcs:
        arc[1] = arc[1] + [nodes[arc[0]][2]]

        quad_1 = quad_list[arc[0]]
        quad_2 = quad_list[arc[2]]

        if nodes[arc[0]][0] < nodes[arc[2]][0]: # arc goes in + x direction # TODO combine this into a smaller loop
            if nodes[arc[0]][1] < nodes[arc[2]][1]: # arc goes in + y direction
                if arc[1][1] == nodes[arc[0]][1]: # arc center is in +x direction
                    start1 = quad_1[3]
                    start2 = quad_1[2]
                    end1 = quad_2[3]
                    end2 = quad_2[0]
                elif arc[1][0] == nodes[arc[0]][0]: # arc center is in +y direction
                    start1 = quad_1[1]
                    start2 = quad_1[2]
                    end1 = quad_2[1]
                    end2 = quad_2[0]
                else:
                    print("Error: arc1", arc) 
            elif nodes[arc[0]][1] > nodes[arc[2]][1]: # arc goes in - y direction
                if arc[1][1] == nodes[arc[0]][1]:
                    start1 = quad_1[0]
                    start2 = quad_1[1]
                    end1 = quad_2[0]
                    end2 = quad_2[3]
                elif arc[1][0] == nodes[arc[0]][0]: # arc center is in -y direction
                    start1 = quad_1[2]
                    start2 = quad_1[1]
                    end1 = quad_2[2]
                    end2 = quad_2[3]
                else:
                    print("Error: arc1", arc) 
            else:
                print("Error: arc2", arc) 
        elif nodes[arc[0]][0] > nodes[arc[2]][0]: # arc goes in -x direction
            if nodes[arc[0]][1] < nodes[arc[2]][1]: # arc goes in + y direction
                if arc[1][1] == nodes[arc[0]][1]: # arc center is in -x direction
                    start1 = quad_1[3]
                    start2 = quad_1[2]
                    end1 = quad_2[1]
                    end2 = quad_2[2]
                elif arc[1][0] == nodes[arc[0]][0]: # arc center is in +y direction
                    start1 = quad_1[0]
                    start2 = quad_1[3]
                    end1 = quad_2[0]
                    end2 = quad_2[1]
                else:
                    print("Error: arc1", arc) 
            elif nodes[arc[0]][1] > nodes[arc[2]][1]: # arc goes in - y direction
                if arc[1][1] == nodes[arc[0]][1]: # arc center is in -x direction
                    start1 = quad_1[1]
                    start2 = quad_1[0]
                    end1 = quad_2[1]
                    end2 = quad_2[2]
                elif arc[1][0] == nodes[arc[0]][0]: # arc center is in -y direction
                    start1 = quad_1[3]
                    start2 = quad_1[0]
                    end1 = quad_2[3]
                    end2 = quad_2[2]
                else:
                    print("Error: arc1", arc)    
            else:
                print("Error: arc2", arc) 
        else:
            print("Error: arc3", arc)

        start1 = vertices[start1].copy()
        start1[2] -= height/2
        start2 = vertices[start2].copy()
        start2[2] -= height/2
        end1 = vertices[end1].copy()
        end1[2] -= height/2
        end2 = vertices[end2].copy()
        end2[2] -= height/2

        if arc[4] == [-90] and start1[1] < end1[1] and start1[0] > end1[0]: 
            direction = np.pi * 2
        elif arc[4] == [90] and start1[1] > end1[1] and start1[0] < end1[0]:
            direction = -np.pi * 2
        else:
            direction = 0

        arc_points_1 = discretize_arc(start1, arc[1], end1, direction, numSegments, 0, height) # the height here is only required if the 3D extrusion is equal in +z and -z direction, rather than starting at the bottom
        arc_points_2 = discretize_arc(start2, arc[1], end2, direction, numSegments, 0, height) # the height here is only required if the 3D extrusion is equal in +z and -z direction, rather than starting at the bottom
        arc_triangles_xy = create_arc_triangles_xy(arc_points_2, arc_points_1, height)
        arc_triangles_side_1 = create_arc_triangles_side(arc_points_1, height)
        arc_triangles_side_2 = create_arc_triangles_side(arc_points_2, height)
        arc_triangles_side = arc_triangles_side_1 + arc_triangles_side_2
        arc_triangles.extend(arc_triangles_xy)
        arc_triangles.extend(arc_triangles_side)

    return arc_triangles

def distance_3d(p1, p2):
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2 + (p2[2] - p1[2])**2)

def define_pump_arcs(height, start, end, direction, numSegments, direction2, pump_radius, channel_height):
    triangles = []
    center_points = []

    step = channel_height
    radius = 0.5 * distance_3d(start, end) * direction2

    center = 0.5 * (start + end)

    arcDirection = 0
    if direction[0] == 0:
        pump_type = False # Refeed pump
        center_new = center.copy()
        center_new[1] += step * direction[1] * 0.5
        p1 = [center_new[0], center_new[1] + radius, center_new[2]]

        start_new = start.copy()

        start_new[1] += step * direction[1] * 0.5
        start_new[0] += radius - (0.5 * distance_3d(start, end)) * direction2

        if math.isclose(p1[0], start_new[0] + abs(radius), rel_tol=eps) and math.isclose(p1[1], start_new[1] - abs(radius), rel_tol=eps):
            arcDirection = -2 * np.pi

    elif direction[0] != 0:
        pump_type = True #Inlet/Outlet Pump
        center_new = center.copy()
        center_new[0] -= step * 0.5

        p1 = [center_new[0] - radius, center_new[1], center_new[2]]

        start_new = start.copy()
        start_new[0] -= step * 0.5
 
        if math.isclose(p1[0], start_new[0] - abs(radius), rel_tol=eps) and math.isclose(p1[1], start_new[1] + abs(radius), rel_tol=eps): 
            arcDirection = 2 * np.pi

    
    arc_points = discretize_arc(start_new, center_new, p1, arcDirection, numSegments, pump_radius, 0)
    arc_triangles_side = create_arc_triangles_side(arc_points, height)


    for i in range(numSegments+1):
        center_points.append([center_new[0], center_new[1], center_new[2]])

    arc_triangles_xy, corner_point = create_arc_triangles_xy_2(arc_points, center_points, height, pump_type)

    triangles.extend(arc_triangles_side)
    triangles.extend(arc_triangles_xy)

    return triangles, corner_point, arc_points

def add_pump_connections(pump_vertices, vertices, direction, numSegments, chip_height_top, pump_radius, channel_height):
    '''
    Creates the pump connections form the pump faces to the chip.
    Includes a cylinder for each pump connection to be able to connect the tubes for the pumps.
    This cylinder is connected to the chip by an intermediate section.
    '''
    
    triangles = []
    top_corner_points = [] # to define the top face of the chip

    rounded_pump_connection_radius = channel_height #+ 0.3 * chip_height_top 
    rounded_pump_connection_arc_points = []
    channel_corner_points = [] # define the corner points of the intermediate rounded channel connection
    connection_triangles = []
    all_arc_points = []

    connection_height = chip_height_top * 0.3 # TODO 0.3 is an arbitrarily chosen number
    height = chip_height_top - connection_height - channel_height/2 # TODO now refeers to the same value, adapt in the following
    height2 = chip_height_top - connection_height - channel_height/2

    # CONNECTION ARCS 1 (CONNECTION OF THE PUMP FACE TO XY PLANE)
    # start is the pump vertice, end is the pumpvertice + radius (+ height) in x and z-direction
    rounded_pump_connection_center = [pump_vertices[0][0], pump_vertices[0][1], pump_vertices[0][2] + rounded_pump_connection_radius]

    for i in range(4): # Nr of Pump vertices in pump
        if direction[0] == -1:
            if i < 2:
                end = [pump_vertices[i][0] - rounded_pump_connection_radius, pump_vertices[i][1], pump_vertices[0][2] + rounded_pump_connection_radius]
            else:
                end = [pump_vertices[i][0] - rounded_pump_connection_radius + channel_height, pump_vertices[i][1], pump_vertices[0][2] + rounded_pump_connection_radius]
        elif direction[1] == -1:
            if i < 2:
                end = [pump_vertices[i][0], pump_vertices[i][1] - rounded_pump_connection_radius, pump_vertices[0][2] + rounded_pump_connection_radius]
            else:
                end = [pump_vertices[i][0], pump_vertices[i][1] - rounded_pump_connection_radius + channel_height, pump_vertices[0][2] + rounded_pump_connection_radius]
        elif direction[1] == 1:
            if i < 2:
                end = [pump_vertices[i][0], pump_vertices[i][1] + rounded_pump_connection_radius, pump_vertices[0][2] + rounded_pump_connection_radius]
            else:
                end = [pump_vertices[i][0], pump_vertices[i][1] + rounded_pump_connection_radius - channel_height, pump_vertices[0][2] + rounded_pump_connection_radius]

        arc_points = discretize_arc_xz(pump_vertices[i], rounded_pump_connection_center, end, direction, numSegments)
        rounded_pump_connection_arc_points.append(arc_points)
        channel_corner_points.append(end)

    width = abs((pump_vertices[0][1] - pump_vertices[3][1]) + (pump_vertices[0][0] - pump_vertices[3][0]))

    arc_triangles_side = create_arc_triangles_side_xz(rounded_pump_connection_arc_points[0], width, direction)
    triangles.extend(arc_triangles_side)
    
    arc_triangles_side = create_arc_triangles_side_xz(rounded_pump_connection_arc_points[2], width, direction)
    triangles.extend(arc_triangles_side)
    
    arc_triangles_xz = create_arc_triangles_xz(rounded_pump_connection_arc_points[0], rounded_pump_connection_arc_points[2], width, direction)
    triangles.extend(arc_triangles_xz)

    # NEW PUMP VERTICES IN XY PLANE
    new_pump_vertices = pump_vertices.copy()

    for i in range(4):
        new_pump_vertices[i][2] = channel_height + connection_height
    
    if direction[0] != 0 or direction[1] == 1:
        direction2 = 1
    else:
        direction2 = -1 
    # First Arc
    triangle, corner_point, arc_points = define_pump_arcs(height, new_pump_vertices[0], new_pump_vertices[1], direction, numSegments, direction2, pump_radius, channel_height)
    triangles.extend(triangle)
    top_corner_points.append(corner_point)
    all_arc_points.append(arc_points)
    # Second Arc
    triangle, corner_point, arc_points = define_pump_arcs(height, new_pump_vertices[1], new_pump_vertices[0], direction, numSegments, direction2, pump_radius, channel_height)
    triangles.extend(triangle)
    top_corner_points.append(corner_point)
    all_arc_points.append(arc_points)
    
    # new_direction = direction.copy()
    # new_direction[0] = - direction[0]
    # new_direction[1] = - direction[1]

    direction2 = direction2 * (-1)

    # Third Arc
    triangle, corner_point, arc_points = define_pump_arcs(height2, new_pump_vertices[2], new_pump_vertices[3], direction, numSegments, direction2, pump_radius, channel_height)
    triangles.extend(triangle)
    top_corner_points.append(corner_point)
    all_arc_points.append(arc_points)
    # Fourth Arc
    triangle, corner_point, arc_points = define_pump_arcs(height2, new_pump_vertices[3], new_pump_vertices[2], direction, numSegments, direction2, pump_radius, channel_height)
    triangles.extend(triangle)
    top_corner_points.append(corner_point)
    all_arc_points.append(arc_points)

    for corner in range(len(channel_corner_points)):
        for i in range(len(all_arc_points[corner])-1):
            connection_triangles.append([all_arc_points[corner][i], all_arc_points[corner][i+1], channel_corner_points[corner]])

    # Define the connecting triangles between the acr point connecting triangles
    connection_triangles.append([all_arc_points[3][0], channel_corner_points[1], channel_corner_points[3]]) 
    connection_triangles.append([all_arc_points[3][-1], channel_corner_points[2], channel_corner_points[3]])
    connection_triangles.append([all_arc_points[0][-1], channel_corner_points[0], channel_corner_points[1]])
    connection_triangles.append([all_arc_points[2][0], channel_corner_points[0], channel_corner_points[2]])

    triangles.extend(connection_triangles)
    
    return triangles, top_corner_points

def triangulation(faces, vertices, xy_orientation):
    triangles = []
    for face in faces:
        vertice_0 = vertices[face[0]]
        vertice_1 = vertices[face[1]]
        vertice_2 = vertices[face[2]]
        vertice_3 = vertices[face[3]]

        if xy_orientation:
            triangles.append([vertice_0, vertice_1, vertice_2])
            triangles.append([vertice_0, vertice_3, vertice_2])
        else:
            triangles.append([vertice_0, vertice_1, vertice_3])
            triangles.append([vertice_0, vertice_2, vertice_3])
        
    return triangles

def identify_organ_block_vertices(organ_channels: list, quad_list: list, vertices: list, channel_height: float, chip_top: float):
    '''
    Identify the main channel which defines the channel segment directly below an organ tank and return the bottom vertices of this tank.
    '''
    # Identify the main channel, i.e., the block that defines the channel segment directly below an organ tank
    organ_block_vertices = []
    
    for node_pair in organ_channels:
        organ_block_vertice_0 = vertices[quad_list[node_pair[0]][1]].copy()
        organ_block_vertice_0[2] += 0.5 * channel_height * 2
        organ_block_vertice_1 = vertices[quad_list[node_pair[0]][2]].copy()
        organ_block_vertice_1[2] += 0.5 * channel_height * 2    
        organ_block_vertice_2 = vertices[quad_list[node_pair[1]][1]].copy()
        organ_block_vertice_2[2] += 0.5 * channel_height * 2
        organ_block_vertice_3 = vertices[quad_list[node_pair[1]][2]].copy()
        organ_block_vertice_3[2] += 0.5 * channel_height * 2

        organ_block_vertices.extend([organ_block_vertice_0, organ_block_vertice_1, organ_block_vertice_2, organ_block_vertice_3])
    
    return organ_block_vertices

def add_organ_tank_triangles(organ_block_vertices: list, height: float):
    '''
    Define the triangles for the organ tank geometry. This includes the corner points for the cut outs in the top face of the final chip.
    '''
    corner_points = [] # To be able to define the top face of the chip
    organ_tank_triangles = []

    # First define a block above the current main channel (for a first trial this might by sufficient)
    for i in range(0, len(organ_block_vertices), 4): # adapt the format so I can easily triangulate these afterwards
        corner_point0 = organ_block_vertices[i].copy()
        corner_point0[2] += height
        corner_points.append(corner_point0)
        corner_point1 = organ_block_vertices[i+1].copy()
        corner_point1[2] += height 
        corner_points.append(corner_point1)
        corner_point2 = organ_block_vertices[i+2].copy()
        corner_point2[2] += height
        corner_points.append(corner_point2)
        corner_point3 = organ_block_vertices[i+3].copy()
        corner_point3[2] += height
        corner_points.append(corner_point3)


        organ_tank_triangles.extend([ # these are the triangles of the side faces
            [tuple(organ_block_vertices[i]), tuple(organ_block_vertices[i+1]), tuple(corner_point1)], 
            [tuple(organ_block_vertices[i]), tuple(corner_point0), tuple(corner_point1)], 
            [tuple(organ_block_vertices[i+1]), tuple(organ_block_vertices[i+3]), tuple(corner_point3)],
            [tuple(organ_block_vertices[i+1]), tuple(corner_point1), tuple(corner_point3)], 
            [tuple(organ_block_vertices[i+2]), tuple(organ_block_vertices[i+3]), tuple(corner_point3)],
            [tuple(organ_block_vertices[i+2]), tuple(corner_point2), tuple(corner_point3)],
            [tuple(organ_block_vertices[i+2]), tuple(organ_block_vertices[i]), tuple(corner_point0)],
            [tuple(organ_block_vertices[i+2]), tuple(corner_point2), tuple(corner_point0)]
           ])
        
    # Define a circular connection/ tank to input the organ module based on Ronaldson-Bouchard?

    return organ_tank_triangles, corner_points

def remove_shared_faces(all_faces: list):
    '''
    Remove shared faces from the list of faces. This is necessary to achieve a continious channel in the geometry definition.
    '''
    # Create a dictionary to count faces. Use sorted tuple for comparison but store original list.
    face_count = {}
    for face in all_faces:
        sorted_face = tuple(sorted(face))
        if sorted_face in face_count:
            face_count[sorted_face][1] += 1  # Increase count
        else:
            face_count[sorted_face] = [face, 1]  # Store original face and set count to 1

    # Select faces which occur exactly once, preserving their original order.
    unique_faces = [original_face for original_face, count in face_count.values() if count == 1]

    return unique_faces

def add_chip(vertices, bottom, top, sides):
    '''
    Add a block surrounding the chip as an additional geometry. This defines the outside of the final chip geometry.
    '''
    # define the max and min values in x, y and z direction
    max_x = np.max(vertices[:,0])
    min_x = np.min(vertices[:,0])
    max_y = np.max(vertices[:,1])
    min_y = np.min(vertices[:,1])
    max_z = np.max(vertices[:,2])
    min_z = np.min(vertices[:,2])

    # create the chip block
    chip_block = ([min_x - sides, min_y - sides, min_z - bottom], 
                          [min_x - sides, max_y + sides, min_z - bottom],
                          [max_x + sides, max_y + sides, min_z - bottom],
                          [max_x + sides, min_y - sides, min_z - bottom],
                          [min_x - sides, min_y - sides, max_z + top],
                          [min_x - sides, max_y + sides, max_z + top],
                          [max_x + sides, max_y + sides, max_z + top],
                          [max_x + sides, min_y - sides, max_z + top])
    
    # define the top corners of the chip
    chip_top_corners = ([min_x - sides, min_y - sides, max_z + top], # bottom left (in xy plane)
                        [max_x + sides, min_y - sides, max_z + top], # bottom right (in xy plane)
                        [max_x + sides, max_y + sides, max_z + top], # top right (in xy plane)
                        [min_x - sides, max_y + sides, max_z + top]) # top left (in xy plane)
    
    return chip_block, chip_top_corners


def chip_to_triangles(chip_block):
    '''
    Triangulate the chip block to create triangles for the final mesh.
    '''
    block = chip_block
    triangles = [
        [block[0], block[1], block[2]], [block[0], block[2], block[3]],  # Bottom face
        # [block[4], block[5], block[6]], [block[4], block[6], block[7]],  # Top face removed to create the pump connections
        [block[0], block[1], block[5]], [block[0], block[5], block[4]],  # Front face
        [block[2], block[3], block[7]], [block[2], block[7], block[6]],  # Back face
        [block[0], block[3], block[7]], [block[0], block[7], block[4]],  # Left face
        [block[1], block[2], block[6]], [block[1], block[6], block[5]],  # Right face
    ]
    return triangles

def add_chip_top_layer_triangles(chip_top_corners, corner_points, corner_points_organ_tanks):
    triangles = []

    # Chip Top Layer
    p_top_left = chip_top_corners[0]
    p_top_right = chip_top_corners[1]
    p_bottom_right = chip_top_corners[2]
    p_bottom_left = chip_top_corners[3]

    # Pump Inlet and Outlet
    inlet_corner_points = corner_points[:4]
    outlet_corner_points = corner_points[4:8]

    # Refeed Inlet and Outlet
    refeed_inlet_corner_points = corner_points[8:12]
    refeed_outlet_corner_points = corner_points[12:]

    # Organ Tank corner points
    nr_of_organ_tanks = len(corner_points_organ_tanks) // 4
    # Most Right Organ Tank (in x-direction)
    organ_tank_corner_points = corner_points_organ_tanks[:4]

    # Corners to inlet and outlet 
    triangles.extend([[p_top_left, inlet_corner_points[0], inlet_corner_points[1]],
                     [p_top_left, inlet_corner_points[0], inlet_corner_points[2]],
                     [p_bottom_left, outlet_corner_points[0], outlet_corner_points[1]],
                     [p_bottom_left, outlet_corner_points[1], outlet_corner_points[3]]])
    
    # Inlet and Outlet to refeed inlet and outlet
    triangles.extend([[inlet_corner_points[3], refeed_inlet_corner_points[0], refeed_inlet_corner_points[2]],
                     [inlet_corner_points[3], refeed_inlet_corner_points[2], refeed_inlet_corner_points[3]],
                     [inlet_corner_points[3], inlet_corner_points[2], refeed_inlet_corner_points[3]],
                     # Outlets
                     [outlet_corner_points[2], refeed_outlet_corner_points[0], refeed_outlet_corner_points[2]],
                     [outlet_corner_points[2], refeed_outlet_corner_points[2], refeed_outlet_corner_points[3]],
                     [outlet_corner_points[3], outlet_corner_points[2], refeed_outlet_corner_points[3]]])
    
    # Connection to the right hand side, adapted for organ tanks
    triangles.extend([[p_bottom_left, p_bottom_right, outlet_corner_points[3]],
                     [outlet_corner_points[3], refeed_outlet_corner_points[3], p_bottom_right],
                    #  [refeed_outlet_corner_points[3], refeed_outlet_corner_points[1], p_bottom_right],
                     [refeed_outlet_corner_points[3], refeed_outlet_corner_points[1], p_bottom_right],
                     # repeat for the top side
                     [p_top_left, p_top_right, inlet_corner_points[2]],
                    #  [inlet_corner_points[3], refeed_inlet_corner_points[2], p_top_right],
                     [refeed_inlet_corner_points[3], refeed_inlet_corner_points[1], p_bottom_right]])
    
    # Connection of the respective inlets and outlets as well as the distance spaces, adapted for organ tanks
    triangles.extend([[p_bottom_left, outlet_corner_points[0], inlet_corner_points[1]], 
                     [p_bottom_left, p_top_left, inlet_corner_points[1]],
                     # Pump outlet to pump inlet
                     [outlet_corner_points[0], inlet_corner_points[1], inlet_corner_points[3]],
                     [outlet_corner_points[0], outlet_corner_points[2], inlet_corner_points[3]],
                     # Surface between pump and refeed connections
                     [outlet_corner_points[2], refeed_outlet_corner_points[0], inlet_corner_points[3]],
                     [inlet_corner_points[3], refeed_outlet_corner_points[0], refeed_inlet_corner_points[0]],
                     # Refeed inlet to refeed outlet
                     [refeed_outlet_corner_points[0], refeed_inlet_corner_points[0], refeed_inlet_corner_points[1]],
                     [refeed_outlet_corner_points[0], refeed_outlet_corner_points[1], refeed_inlet_corner_points[1]],
                    #  [refeed_outlet_corner_points[1], p_bottom_right, p_top_right],
                     [refeed_outlet_corner_points[1], refeed_inlet_corner_points[1], p_bottom_right]])    
    
    # Organ Tank cut outs
    triangles.extend([[p_bottom_right, p_top_right, organ_tank_corner_points[3]], # ?? war davor 2
                     [p_top_right, organ_tank_corner_points[3], organ_tank_corner_points[2]],
                     [p_top_right, organ_tank_corner_points[2], organ_tank_corner_points[0]],
                     [p_bottom_right, organ_tank_corner_points[3], organ_tank_corner_points[1]]
                      ]) 
    
    for i in range(nr_of_organ_tanks - 1):
        organ_tank_corner_points_previous = organ_tank_corner_points
        organ_tank_corner_points = corner_points_organ_tanks[(i+1)*4:(i+2)*4]

        triangles.extend([[organ_tank_corner_points_previous[0], organ_tank_corner_points_previous[1], organ_tank_corner_points[3]],
                         [organ_tank_corner_points_previous[0], organ_tank_corner_points[2], organ_tank_corner_points[3]],
                         [p_bottom_right,  organ_tank_corner_points_previous[1], organ_tank_corner_points[3]],
                         [p_top_right,  organ_tank_corner_points_previous[0], organ_tank_corner_points[2]],
                         [p_top_right, organ_tank_corner_points[2], organ_tank_corner_points[0]],
                         [p_bottom_right, organ_tank_corner_points[3], organ_tank_corner_points[1]]])

    # Connect organ tanks to pump inlets
    triangles.extend([[organ_tank_corner_points[1], organ_tank_corner_points[0], inlet_corner_points[2]], #2
                      [organ_tank_corner_points[1], inlet_corner_points[2], refeed_inlet_corner_points[3]], #3
                      [organ_tank_corner_points[1], refeed_inlet_corner_points[3], p_bottom_right], #4
                      [organ_tank_corner_points[0], inlet_corner_points[2], p_top_right]])
    
    return triangles


def create_stl_file(nodes, pumps, channels, arcs, height, bottom, top, sides, pump_radius, organ_channels, file_name, channel_negative): #incl. bool to define positive or negative channel definition
    '''
    Create an STL file based on the input nodes, channels, arcs and height using the mesh module from the stl library.
    '''
    # PRIOR DEFINITIONS
    num_segments = 10
    unit_conversion_to_mm = True

    if unit_conversion_to_mm:
        # Convert meters to millimeters and mirror in y-direction
        for i, node in enumerate(nodes):
            nodes[i] = [node[0] * 1e3, node[1] * 1e3, node[2] * 1e3]
        for i, channel in enumerate(channels):
            channels[i] = [channel[0], channel[1], channel[2] * 1e3]
        for i, arc in enumerate(arcs):
            arcs[i] = [arc[0], [arc[1][0] * 1e3, arc[1][1] * 1e3], arc[2], arc[3] * 1e3, arc[4]]
        
    

    channels_per_node = define_channels_per_node(nodes, channels)
    quads = define_quads_at_nodes(nodes, channels_per_node)

    channel_height = height * 1e3

    z_height = - 0.5 * channel_height

    vertices, quad_list = define_vertices_and_quad_list(nodes, quads, z_height)
    channels_per_node = define_channels_per_node(nodes, channels)

    # QUAD FACE DEFINITION
    quad_faces = define_quad_faces_xy(quad_list) # top and bottom faces
    len_quad_faces = len(quad_faces)
    quad_faces_bottom = quad_faces[:len_quad_faces//2]
    quad_faces_top = quad_faces[len_quad_faces//2:]
    quad_faces_side = define_faces_side(quad_faces_bottom, quad_faces_top)

    # CHANNEL FACE DEFINITION
    channel_faces_bottom = define_channel_faces_xy(nodes, channels, quad_list) # defines the channel faces on the bottom
    channel_faces_top = define_channel_faces_xy(nodes, channels, quad_faces_top) # TODO this can no longer be done this way!!
    channel_faces_side = define_faces_side(channel_faces_bottom, channel_faces_top)

    all_faces = quad_faces_bottom + quad_faces_top + channel_faces_bottom + channel_faces_top + quad_faces_side + channel_faces_side

    # REMOVE DUPLICATE FACES
    if channel_negative:
        all_faces += define_channel_faces_xy(nodes, organ_channels, quad_faces_top)
    non_overlapping_faces = remove_shared_faces(all_faces)

    # TRIANGULATE
    channel_triangles = triangulation(non_overlapping_faces, vertices, xy_orientation=True)
    if len(arcs) != 0:
        arc_triangles = define_arcs(nodes, quad_list, vertices, arcs, num_segments, channel_height)

        triangles = channel_triangles + arc_triangles
    else:
        triangles = channel_triangles

    # PUMP FACE DEFINITON 
    pump_vertices = []
    for nodeId in pumps:
        pump_vertice_0 = vertices[quad_list[nodeId][0]]
        pump_vertice_1 = vertices[quad_list[nodeId][2]]

        # add z direction to the bottom vertices
        pump_vertice_0_top = pump_vertice_0.copy()
        pump_vertice_0_top[2] += channel_height
        pump_vertice_1_top = pump_vertice_1.copy()
        pump_vertice_1_top[2] += channel_height

        pump_vertices.append([pump_vertice_0, pump_vertice_1, pump_vertice_0_top, pump_vertice_1_top])
    
    pump_vertices = np.array(pump_vertices)

    # create_svg_network_1D(nodes, channels, filename='../tests/network1D.svg')
    create_svg_network_2D(vertices, nodes, quad_list, channel_faces_bottom, arcs, filename='output2D.svg')

    # CHANNEL STRUCTURE (negative of positive for fabricaiton or simulation respectively)
    if channel_negative: # the result should be the negative of the channel embedded in a chip ready to print
        bottom = bottom # z-direction
        top = top  # z-direction
        sides = sides # xy-direction # Assuming a side connect with connections only on the yz faces
        pump_radius = pump_radius #0.03e-1 

        # CHIP DEFINITION
        chip_block, chip_top_corners = add_chip(vertices, bottom, top, sides)
        chip_triangles = chip_to_triangles(chip_block)
        organ_block_vertices = identify_organ_block_vertices(organ_channels, quad_list, vertices, channel_height, top) 
        organ_tank_triangles, corner_points_organ_tanks = add_organ_tank_triangles(organ_block_vertices, top)

        # PUMP CONNECTION DEFINITION
        pump_triangles = []
        corner_points = []
        pump_direction = [-1, 0, 0]
        pump_connection_triangles, pump_corner_points = add_pump_connections(pump_vertices[0], vertices, pump_direction, num_segments, top, pump_radius, channel_height) # Inlet
        pump_triangles.extend(pump_connection_triangles) 
        corner_points.extend(pump_corner_points)
        pump_connection_triangles, pump_corner_points = add_pump_connections(pump_vertices[1], vertices, pump_direction, num_segments, top, pump_radius, channel_height) # Outlet
        pump_triangles.extend(pump_connection_triangles) 
        corner_points.extend(pump_corner_points)
        pump_direction = [0, 1, 0]
        # pump_direction = [0, -1, 0]
        pump_connection_triangles, pump_corner_points = add_pump_connections(pump_vertices[2], vertices, pump_direction, num_segments, top, pump_radius, channel_height) # Refeed Inlet
        pump_triangles.extend(pump_connection_triangles) 
        corner_points.extend(pump_corner_points)
        pump_direction = [0, -1, 0] 
        # pump_direction = [0, 1, 0]
        pump_connection_triangles, pump_corner_points = add_pump_connections(pump_vertices[3], vertices, pump_direction, num_segments, top, pump_radius, channel_height) # Refeed Outlet
        pump_triangles.extend(pump_connection_triangles) 
        corner_points.extend(pump_corner_points)

        # Define top layer of the chip (including the pump connections and the organ tanks)
        chip_top_layer_triangles = add_chip_top_layer_triangles(chip_top_corners, corner_points, corner_points_organ_tanks)
        chip_triangles.extend(chip_top_layer_triangles)

        # APPEND THE TRIANGLES FOR THE RESPECTIVE GEOMETRIES
        triangles += chip_triangles
        triangles += pump_triangles
        triangles += organ_tank_triangles

    elif channel_negative == False: # the result should be the positive of the channel, the inlets and outlets defined as faces to be able to load the channel network into a simulation tool 
        pump_triangles = [] # these are the pumps
        for i in pump_vertices:
            pump_triangles.append([i[0], i[1], i[2]])
            pump_triangles.append([i[1], i[2], i[3]])

        triangles += pump_triangles
    
    len_triangles = len(triangles)
    triangle_counter = 0

    # Create the mesh with the total number of triangles
    mesh_data = mesh.Mesh(np.zeros(len_triangles, dtype=mesh.Mesh.dtype))

    for triangle in triangles:
        mesh_data.vectors[triangle_counter] = np.array(triangle)
        triangle_counter += 1
    
    mesh_data.save(file_name)
    print(f'STL file "{file_name}" created successfully.')

def plot_nodes(nodes: list, channels: list):
    '''
    Plots the 1D network, including the nodes and channels in the xy plane.
    '''
    # Extract X and Y coordinates from nodes
    x_coords = [node[0] for node in nodes]
    y_coords = [node[1] for node in nodes]

    plt.figure(figsize=(10, 8))  # Set figure size for better visibility
    plt.scatter(x_coords, y_coords, marker='.', label='Nodes')

    # Label each node with its index
    # for i, (x, y) in enumerate(zip(x_coords, y_coords)):
    #     plt.text(x, y, f' {i}', color='blue', fontsize=9, ha='right', va='bottom')

     # Plot channels as lines between nodes
    for start_node, end_node, width in channels:
        start_x, start_y = nodes[start_node][:2]
        end_x, end_y = nodes[end_node][:2]
        plt.plot([start_x, end_x], [start_y, end_y], 'k-', lw=max(width * 0.1, 1), label='Channels' if start_node == channels[0][0] else "")

    plt.title('Node Positions in XY Plane')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.grid(True)
    plt.axis('equal')
    plt.show()

def create_svg_network_2D(vertices, nodes, quad_list, channel_faces, arcs, filename):
    header = '''<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="50" height="25" viewBox="-10 0 60 10">\n'''
    footer = '</svg>'
    
    with open(filename, 'w') as svg_file:
        svg_file.write(header)
        
        # CHANNELS
        for channel in channel_faces:
            coords = [vertices[i] for i in channel]
            points_str = " ".join([f"{pt[0]},{pt[1]}" for pt in coords])
            # Write the polygon to the SVG
            svg_file.write(f'<polygon points="{points_str}" style="fill:none;stroke:black;stroke-width:0.1" />\n')
        
        # QUADS
        for quad in quad_list:
            quad_coords = [vertices[i] for i in quad]
            points_str = " ".join([f"{pt[0]},{pt[1]}" for pt in quad_coords])
            # Write the polygon to the SVG
            svg_file.write(f'<polygon points="{points_str}" style="fill:none;stroke:black;stroke-width:0.1" />\n')

        # Write arcs
        for arc in arcs:
            arc[1] = arc[1] + [nodes[arc[0]][2]]

            quad_1 = quad_list[arc[0]]
            quad_2 = quad_list[arc[2]]

            if nodes[arc[0]][0] < nodes[arc[2]][0]: # arc goes in + x direction 
                if nodes[arc[0]][1] < nodes[arc[2]][1]: # arc goes in + y direction
                    if arc[1][1] == nodes[arc[0]][1]: # arc center is in +x direction
                        start1 = quad_1[3]
                        start2 = quad_1[2]
                        end1 = quad_2[3]
                        end2 = quad_2[0]
                    elif arc[1][0] == nodes[arc[0]][0]: # arc center is in +y direction
                        start1 = quad_1[1]
                        start2 = quad_1[2]
                        end1 = quad_2[1]
                        end2 = quad_2[0]
                    else:
                        print("Error: arc1", arc) 
                elif nodes[arc[0]][1] > nodes[arc[2]][1]: # arc goes in - y direction
                    if arc[1][1] == nodes[arc[0]][1]:
                        start1 = quad_1[0]
                        start2 = quad_1[1]
                        end1 = quad_2[0]
                        end2 = quad_2[3]
                    elif arc[1][0] == nodes[arc[0]][0]: # arc center is in -y direction
                        start1 = quad_1[2]
                        start2 = quad_1[1]
                        end1 = quad_2[2]
                        end2 = quad_2[3]
                    else:
                        print("Error: arc1", arc) 
                else:
                    print("Error: arc2", arc) 
            elif nodes[arc[0]][0] > nodes[arc[2]][0]: # arc goes in -x direction
                if nodes[arc[0]][1] < nodes[arc[2]][1]: # arc goes in + y direction
                    if arc[1][1] == nodes[arc[0]][1]: # arc center is in -x direction
                        start1 = quad_1[3]
                        start2 = quad_1[2]
                        end1 = quad_2[1]
                        end2 = quad_2[2]
                    elif arc[1][0] == nodes[arc[0]][0]: # arc center is in +y direction
                        start1 = quad_1[0]
                        start2 = quad_1[3]
                        end1 = quad_2[0]
                        end2 = quad_2[1]
                    else:
                        print("Error: arc1", arc) 
                elif nodes[arc[0]][1] > nodes[arc[2]][1]: # arc goes in - y direction
                    if arc[1][1] == nodes[arc[0]][1]: # arc center is in -x direction
                        start1 = quad_1[1]
                        start2 = quad_1[0]
                        end1 = quad_2[1]
                        end2 = quad_2[2]
                    elif arc[1][0] == nodes[arc[0]][0]: # arc center is in -y direction
                        start1 = quad_1[3]
                        start2 = quad_1[0]
                        end1 = quad_2[3]
                        end2 = quad_2[2]
                    else:
                        print("Error: arc1", arc)    
                else:
                    print("Error: arc2", arc) 
            else:
                print("Error: arc3", arc)

            direction = arc[4]
            if direction == [-90]:
                radius = vertices[start1][0] - vertices[end1][0]
                svg_file.write(f'<path d="M{vertices[start1][0]},{vertices[start1][1]} A{radius},{radius} 0 0,0 {vertices[end1][0]},{vertices[end1][1]}" fill="none" stroke="blue" stroke-width="0.1" />\n')
                radius = vertices[start2][0] - vertices[end2][0]
                svg_file.write(f'<path d="M{vertices[start2][0]},{vertices[start2][1]} A{radius},{radius} 0 0,0 {vertices[end2][0]},{vertices[end2][1]}" fill="none" stroke="blue" stroke-width="0.1" />\n')
            else:
                radius = vertices[start1][0] - vertices[end1][0]
                svg_file.write(f'<path d="M{vertices[start1][0]},{vertices[start1][1]} A{radius},{radius} 0 0,1 {vertices[end1][0]},{vertices[end1][1]}" fill="none" stroke="blue" stroke-width="0.1" />\n')
                radius = vertices[start2][0] - vertices[end2][0]
                svg_file.write(f'<path d="M{vertices[start2][0]},{vertices[start2][1]} A{radius},{radius} 0 0,1 {vertices[end2][0]},{vertices[end2][1]}" fill="none" stroke="blue" stroke-width="0.1" />\n')
        svg_file.write(footer)

    print(f'SVG file "{filename}" created successfully.')


if __name__ == "__main__":
    output_file = '../tests/output.stl'
    filename = '../tests/config_male_all.json'
    output_file = '../tests/stl_output.stl'
    nodes, pumps, channels, arcs, height, organ_channels = read_in_network_file(filename)

    channel_negative = True
    bottom = 0.5e-3
    top = 0.5e-3
    sides = 0.5e-3
    pump_radius = 0.03e-1

    # UNCOMMENT THE FOLLOWING LINE TO SHOW THE NODES AND CHANNELS IN THE XY PLANE
    plot_nodes(nodes, channels)
    
    # create_stl_file(nodes, pumps, channels, arcs, height, organ_channels, output_file, channel_negative)
    create_stl_file(nodes, pumps, channels, arcs, height, bottom, top, sides, pump_radius, organ_channels, output_file, channel_negative)
