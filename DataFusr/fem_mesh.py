### =============================================================================================================== ###
###                                                                                                                 ###
###                                                   fem_mesh.py                                                   ###
###                                                                                                                 ###
### =============================================================================================================== ###
# This module ``fem_mesh`` contains the classes and methods for meshing and mesh-properties.


### ===================================================================================================================
###   Contents script
### ===================================================================================================================

#   1. Import modules

#   2. Functions to create mesh objects

#   3. Helper functions for meshing

#   4. Functions for meshing

#   5. End of script

### ===================================================================================================================
###   1. Import modules
### ===================================================================================================================

# Import general functions
import math
from typing import List, Optional

# References for functions and classes in the rhdhv_fem package
from rhdhv_fem.mesh import Mesh, MeshNode, MeshElement
from rhdhv_fem.fem_math import fem_compare_coordinates, fem_distance_coordinates, fem_divide_line, \
    fem_intersection_of_two_line_segments
from rhdhv_fem.fem_config import Config
from rhdhv_fem.fem_math import fem_point_on_line, fem_vector_2_points, fem_ordered_coordinates_list, fem_closest_point,\
    fem_angle_between_2_vectors

# Import module matplotlib, check if module is installed
# This module is used only for plotting meshes
try:
    import matplotlib
    from mpl_toolkits.mplot3d import Axes3D
    matplotlib.use('agg')  # Switch to a non-interactive backend to properly import matplotlib.pyplot
    import matplotlib.pyplot as plt
    matplot_use = True
except ImportError:
    matplotlib = None
    matplot_use = False


### ===================================================================================================================
###   2. Functions to create mesh objects
### ===================================================================================================================

def fem_duplicate_id_check(list_element):
    """
    This function generates an identification (ID) number. It will start at 1 and check sequencial IDs to find the
    first unique ID.

    Input:
        - list_element: List with object references of different classes (class should have ID attribute).

    Output:
        - Returns the first found unique ID.
    """
    counter = 1
    continue_check = False
    while not continue_check:
        if len(list_element) == 0:
            continue_check = True
        else:
            check = False
            for element in list_element:
                if element.id == counter:
                    check = True
                    break
            if not check:
                continue_check = True
            else:
                counter += 1
    return counter


def _fem_create_meshnode(
        project: 'Project', coordinates: List[float], node_id: Optional[int] = None, check_duplicate: bool = True) \
        -> MeshNode:
    """
    Function to create a mesh-node in the class 'MeshNode'. It is checked if there is not already an existing mesh-node
    on the same location (if it set in the project constants to merge mesh-nodes).

    Input:
        - project: Project object containing collections of fem objects an project variables.
        - coordinates (list of 3 floats): The coordinates are defined by a list of 3 floats, representing the x-, y-
          and z-coordinate of the coordinates (if only 2 floats are provided, a 2D space is assumed, setting the
          z-coordinate to zero.
        - node_id (int): Optional parameter to specify the ID of the mesh-node. If not provided it will generate
          the next available node-id in the collection of mesh-nodes. If ID is provided, it is checked if it is
          already present, in which case an error is raised.
        - check_duplicate (bool): Select to check duplicates. Default value True.

    Output:
        - Returns the object created in the 'Node' class.
        - If the input was not sufficient or correct a notification and None is returned instead.
    """
    # Check if node_id is provided else generate it
    if not node_id:
        _id = fem_duplicate_id_check(project.collections.mesh_nodes)
    else:
        _id = node_id

    # Create the meshnode
    meshnode = project.add(MeshNode(coordinates=coordinates, id=_id), check_duplicate=check_duplicate)

    # Inform if the mesh node has been merged
    if node_id and node_id != meshnode.id:
        project.write_log(f"WARNING: Mesh node with id {node_id} has been merged with {meshnode.id}.")

    # Return the mesh node object
    return meshnode


def _fem_create_meshelement(project: 'Project', node_list: List[MeshNode], element_id: Optional[int] = None):
    """
    Function to create an element in the class 'MeshElement'.

    Input:
        - project: Project object containing collections of fem objects an project variables.
        - point_list (list of obj): List of object references of MeshNodes, which are to be associated to the element.
        - element_id (int): Optional parameter to specify the ID of the mesh-element. If not provided it will generate
          the next available element-id in the collection of mesh-elements. If ID is provided, it is checked if it is
          already present, in which case an error is raised.

    Output:
        - Returns the object created in the 'MeshElement' class.
    """
    # Check if element_id is provided else generate it
    if not element_id:
        element_id = fem_duplicate_id_check(project.collections.mesh_elements)

    # Create and return the mesh element object
    return project.add(MeshElement(node_list=node_list, id=element_id))


def _fem_create_mesh(project: 'Project', elements: List[MeshElement]):
    """
    Function to create a mesh in the class 'Mesh' and add it to the project.

    Input:
        - project: Project object containing collections of fem objects an project variables.
        - elements (list of obj): List of instances of MeshElements class, which are part of the mesh of the shape.

    Output:
        - Returns the instance of mesh containing the elementset.
    """
    # Create and return the mesh object
    return project.add(Mesh(elements=elements))


### ===================================================================================================================
###   3. Helper functions for meshing
### ===================================================================================================================

def _fem_get_meshnode_id(project: 'Project', coordinates: List[float]):
    nodes = list()
    for mesh_node in project.collections.mesh_nodes:
        if fem_compare_coordinates(mesh_node.coordinates, coordinates, precision=project.rounding_precision):
            nodes.append(mesh_node)
    return nodes


def _fem_get_single_meshnode_id(project: 'Project', coordinates: List[float]):
    lst = project.get_meshnode_id(coordinates)
    if len(lst) > 1:
        raise UserWarning("ERROR: Multiple meshnodes on coordinate, currently not available in fem-client.")
    return lst[0].id


### ===================================================================================================================
###   4. Functions for meshing
### ===================================================================================================================

def fem_create_regular_linemesh(line_shape: 'Lines', nr_elements: Optional[int] = None):
    """
    This function creates a mesh object for a line shape. The mesh is a regular mesh based on the nr of elements]
    specified (all elements have the same size).

    Input:
        - line_shape (obj): Object reference of the Lines class, part of the Shapes class (Beam, Column, Pile etc).
        - nr_elements (int): Number of elements to create. Optional, if not provided, the elementsize specified in the
          shape is used for meshing. The elementsize is used as the maximum size of the element (ceiling the division
          of the beam).

    Output:
        - Returns mesh-object with the requested divison.
    """
    project = line_shape.project
    shape_division = line_shape.get_nodes(from_start=True)
    end_node = None
    elements = []
    for i in range(1, len(shape_division)):

        # Calculate the distance between the two shape nodes
        distance = fem_distance_coordinates(shape_division[i - 1].coordinates, shape_division[i].coordinates)

        # Check if the number of elements is requested, else get from elementsize attribute of shape
        if not nr_elements:
            nr_elements_segm = math.ceil(distance / line_shape.elementsize)
        else:
            nr_elements_segm = nr_elements

        # Calculate the increment in 3D
        c_sta = shape_division[i - 1].coordinates
        c_end = shape_division[i].coordinates
        c_inc = [(ce - cs) / nr_elements_segm for ce, cs in zip(c_end, c_sta)]

        for j in range(nr_elements_segm):
            if j == 0:
                coord = [(cs + ci * j) for cs, ci in zip(c_sta, c_inc)]
                start_node = project.create_meshnode(coord)
            else:
                start_node = end_node
            coord = [(cs + ci * (j + 1)) for cs, ci in zip(c_sta, c_inc)]
            end_node = project.create_meshnode(coord)
            elements.append(project.create_meshelement(node_list=[start_node, end_node]))

    return project.create_mesh(elements=elements)


def fem_create_regular_surfacemesh(surface: 'Surfaces', nr_elements_1: Optional[int] = None,
                                   nr_elements_2: Optional[int] = None):
    """
    This function creates a regular mesh for a given surface shape.

    .. warning:: Function only works for a contour of 4 lines. The surface may not have internal points, openings,
      regions or internal lines.

    Input:
        - surface (obj): Object reference of surface shape.
        - nr_element_1 (int): Number of elements in the first direction of the surface contour (line 1 and 3).
          Argument is optional, by default the elementsize attribute of surface is used to calculate the number of
          elements in this direction.
        - nr_element_2 (int): Number of elements in the second direction of the surface contour (line 2 and 4).
          Argument is optional, by default the elementsize attribute of surface is used to calculate the number of
          elements in this direction.

    Output:
        - Function returns the generated mesh for the surface. It does not bind it to the surface shape.
    """
    # Check the surface contour for 4 lines
    if len(surface.contour.lines) != 4:
        project = surface.project
        meshnodes = {}
        triangle_shape_nodes = {}
        filtered_ids = []
        for line in surface.contour.lines:
            triangle_shape_nodes[f'{line.node_start.id}'] = line.node_start
            triangle_shape_nodes[f'{line.node_end.id}'] = line.node_end
            if line.node_start.id not in filtered_ids:
                filtered_ids.append(line.node_start.id)
            if line.node_end.id not in filtered_ids:
                filtered_ids.append(line.node_end.id)
        counter = 0
        for i in filtered_ids:
            meshnodes[f'mesh_node_{counter}'] = \
                (project.create_meshnode(coordinates=triangle_shape_nodes[f'{i}'].coordinates))
            counter += 1
        three_sided_shape = project.create_meshelement([meshnodes['mesh_node_0'],
                                                        meshnodes['mesh_node_1'],
                                                        meshnodes['mesh_node_2']])
        return project.create_mesh(elements=[three_sided_shape])

    # Check the surface contour for openings, internal_lines or openings
    if surface.openings or surface.internal_lines or surface.internal_points or surface.regions:
        raise ValueError("ERROR: Function fem_create_regular_surfacemesh is only applicable for surface shapes without"
                         "openings, internal lines, internal points or regions.")

    # Check if the number of elements is requested, else get from elementsize attribute of shape
    if not nr_elements_1:
        nr_elements_1 = math.ceil(surface.contour.lines[0].get_length() / surface.elementsize)
    if not nr_elements_2:
        nr_elements_2 = math.ceil(surface.contour.lines[1].get_length() / surface.elementsize)
    project = surface.project

    # Divide the first line of the contour
    points_n = fem_divide_line(line=surface.contour.lines[0].get_points(), nr_elements=nr_elements_1)

    # List nodes_n is reversed if the end node is not connecting to the next line of contour
    if surface.contour.lines[0].node_start in surface.contour.lines[1].get_nodes():
        points_n.reverse()

    # Divide the second line of the contour
    points_e = fem_divide_line(line=surface.contour.lines[1].get_points(), nr_elements=nr_elements_2)
    if not fem_compare_coordinates(points_e[0], points_n[-1]):
        points_e.reverse()

    # Divide the third line of the contour
    points_s = fem_divide_line(line=surface.contour.lines[2].get_points(), nr_elements=nr_elements_1)
    if not fem_compare_coordinates(points_s[0], points_e[-1]):
        points_s.reverse()

    # Divide the fourth line of the contour
    points_w = fem_divide_line(line=surface.contour.lines[3].get_points(), nr_elements=nr_elements_2)
    if not fem_compare_coordinates(points_w[0], points_s[-1]):
        points_w.reverse()

    # The points are all arranged clockwise or anti-clockwise,
    # the order is changed to ordered in pairs
    points_s.reverse()
    points_w.reverse()

    # Initial values
    nodes = dict()
    elements = list()
    counter = 0

    # Create the meshnodes
    for iy in range(nr_elements_2 + 1):
        for ix in range(nr_elements_1 + 1):
            intersection = fem_intersection_of_two_line_segments(
                line1=[points_w[iy], points_e[iy]], line2=[points_n[ix], points_s[ix]], return_intersection=True)
            # nodei = _line_intersection(node1, node2, node3, node4)
            if intersection == 'NoIntersection' or len(intersection) == 2:
                raise ValueError(f"ERROR: Meshing of {surface.name} ran into a problem. Meshing aborted.")
            counter += 1
            # Create meshnode
            nodes[counter] = surface.project.create_meshnode(coordinates=intersection)

    # Create the meshelements
    for i in range(nr_elements_2):
        for j in range(nr_elements_1):
            elements.append(project.create_meshelement([
                nodes[i * (nr_elements_1 + 1) + j + 1],
                nodes[i * (nr_elements_1 + 1) + j + 2],
                nodes[(i+1) * (nr_elements_1 + 1) + j + 2],
                nodes[(i+1) * (nr_elements_1 + 1) + j + 1]]))

    # Create and return the mesh
    return project.create_mesh(elements=elements)


def fem_plot_2_check(elements: List[MeshElement]):
    """ Function to plot the mesh elements in 3D graph."""
    if not matplot_use:
        raise ImportError(
            "ERROR: To use the fem_plot_2_check function it is required to install matplotlib module.")

    # Initiate the data containers for scatter plot
    x, y, z = [], [], []
    
    for element in elements:
        for node in element.node_list:
            x.append(node.coordinates[0])
            y.append(node.coordinates[1])
            z.append(node.coordinates[2])

    matplotlib.use(Config.MPL_GUI)
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x, y, z) 
    plt.show()


def mesh_line_shape_with_internal_point(project: 'Project', member: 'Lines', nodes: list = []):
    """
        This function is used to split a line shape up into multiple line shapes based on the internal points that
        intersect the line shape. I.e. if there was two internal points, the line shape would be split into three.
        All loads associated with the original line shape are assigned to each of these new line shapes. All supports
        associated with original line shape are maintained. i.e. if it is a line support each new member will be a
        line support. If it is a point support the new line shape connected with the node in which the support node is
        located will be assigned.

        Input:
            - project: Project object containing collections of fem objects an project variables.
            - member (obj): RHDHV Beam/Column Object which is to be meshed
            - nodes (list of obj): List of RHDHV Nodes which are to be checked as to whether they overlap/intersect the
              beam which is to be meshed
        Output:
            - If line shape is meshed, it returns [temp_beam_dict, loads_to_delete] where temp_beam_dict is a dictionary
            of all new line shapes which have been generated and loads to delete are the load objects of the original
            line shape which are no longer needed if the original line shape is to be removed
            - Returns False if the line shape has no nodes which are internal
        """
    # create list for nodes in which are to be used to mesh the member
    internal_nodes_to_mesh = []
    ordered_internal_nodes_to_mesh = []
    # if node list defined
    if len(nodes) > 0:
        # for each node in the node list defined by the user, check if it lies on the member as an internal point
        for node in nodes:
            if fem_point_on_line(node, [member.contour.node_start, member.contour.node_end]) is True:
                internal_nodes_to_mesh.append(node)
    # check if member has internal points. If so add each internal node to the list to be meshed
    if member.internal_points is None:
        pass
    else:
        for j in member.internal_points:
            internal_nodes_to_mesh.append(j)
    if len(internal_nodes_to_mesh) == 0:
        return None
    # Determine start and end of the member so direction is maintained
    start = member.contour.node_start
    end = member.contour.node_end
    # Check to see there are nodes that intersect the member
    coordinates_of_internal_nodes = []
    # obtain list of all coordinates of internal nodes
    for node in internal_nodes_to_mesh:
        coordinates_of_internal_nodes.append(node.coordinates)
    # Remove duplicate coordinates
    new_order = []
    for coord in coordinates_of_internal_nodes:
        if coord not in new_order:
            new_order.append(coord)
    coordinates_of_internal_nodes = new_order
    # order the internal coordinates
    if len(coordinates_of_internal_nodes) > 0:
        ordered_coordinates = fem_ordered_coordinates_list(coordinates_of_internal_nodes, start.coordinates)
    else:
        ordered_coordinates = []
    # now the coordinates have been ordered, obtain the node object they relate to as node objects are not
    # iterable
    for coord in ordered_coordinates:
        for node in internal_nodes_to_mesh:
            if fem_compare_coordinates(coord, node.coordinates, Config.CHECK_PRECISION):
                ordered_internal_nodes_to_mesh.append(node)
                break
    # Append end and start node in relevant order
    ordered_internal_nodes_to_mesh.append(end)
    # place start at the front of the list
    ordered_internal_nodes_to_mesh = [start] + ordered_internal_nodes_to_mesh
    # Obtain attributes of the original member
    name = member.name
    beam_geometry = member.geometry
    z_axis = member.element_z_axis
    beam_material = member.material
    temp_line_dict = {}
    temp_beam_dict = {}
    temp_line_load_dict = {}
    # Create the new members along the line
    for j in range(len(ordered_internal_nodes_to_mesh) - 1):
        temp_line_dict[f'line{j}'] = project.create_line([ordered_internal_nodes_to_mesh[j],
                                                          ordered_internal_nodes_to_mesh[j + 1]])
        temp_beam_dict[f'beam{j}'] = project.create_beam(shape_line=temp_line_dict[f'line{j}'],
                                                         name=f'{name}_meshed_{j}',
                                                         material=beam_material,
                                                         geometry=beam_geometry)
        temp_beam_dict[f'beam{j}'].mesh_shape(1)
        temp_beam_dict[f'beam{j}'].update_local_z_axis(z_axis.vector)

    loads_to_delete = []
    # determine if any point loads are associated with the original member and replace connecting shape with new
    # member that has been created that shares the node
    for load in project.collections.point_loads:
        if load.connecting_shapes[0]['connecting_shape'] == member:
            for key in temp_beam_dict:
                if temp_beam_dict[key].contour.node_start == load.connecting_shapes[0]['shape_geometry'] or \
                        temp_beam_dict[key].contour.node_end == load.connecting_shapes[0]['shape_geometry']:
                    load.connecting_shapes[0]['connecting_shape'] = temp_beam_dict[key]
    line_load_counter = 0
    # determine if any line loads are associated with the original member and assign these loads to the new members
    for load in project.collections.line_loads:
        if load.connecting_shapes[0]['connecting_shape'] == member:
            # Get load attributes
            line_load_direction = load.direction
            line_load_value = load.value
            line_load_type = load.load_type
            line_load_case = load.loadcase
            loads_to_delete.append(load)
            # create new line loads across new members
            for value in temp_beam_dict:
                temp_line_load_dict[f'line_load_{line_load_counter}'] = project.create_lineload(
                    load_type=line_load_type,
                    value=line_load_value,
                    direction=line_load_direction,
                    loadcase=line_load_case,
                    connecting_shapes=[{"connecting_shape": temp_beam_dict[value]}])
                line_load_counter += 1
    line_support_dict = {}
    line_support_counter = 0
    # adjust point supports to make sure connected shape matches new member created
    for support in project.collections.point_supports:
        if support.connecting_shapes[0]['connecting_shape'] == member:
            for key in temp_beam_dict:
                if temp_beam_dict[key].contour.node_start == support.connecting_shapes[0]['shape_geometry'] or \
                   temp_beam_dict[key].contour.node_end == support.connecting_shapes[0]['shape_geometry']:
                    support.connecting_shapes[0]['connecting_shape'] = temp_beam_dict[key]
    # check if any line supports associated with original member and assign/create if so for all new members
    for support in project.collections.line_supports:
        if support.connecting_shapes[0]['connecting_shape'] == member:
            if member.contour == support.connecting_shapes[0]['shape_geometry']:
                degrees_of_freedom = support.degrees_of_freedom
                axes = support.axes
                spring_stiffnesses = support.spring_stiffnesses
                support_set = support.support_set
                for key in temp_beam_dict:
                    line_support_dict[f'line_support{line_support_counter}'] = project.create_linesupport(
                        connecting_shapes=[{'connecting_shape': temp_beam_dict[key]}],
                        degrees_of_freedom=degrees_of_freedom,
                        support_set=support_set,
                        axes=axes,
                        spring_stiffnesses=spring_stiffnesses)
                    line_support_counter += 1
    return [temp_beam_dict, loads_to_delete]


def mesh_surface_shape(project: 'Project', shape: 'Shape', shapes_to_remove: List['Shape'] = [],
                       loads_to_delete: ['Load'] = [], shapes_to_check_connections: List['Shape'] = [],
                       triangle_mesh_allowed: bool = False, ignore_centre_node: bool = False,
                       mesh_suitable: bool = True):
    """
    This function is used to mesh a single surface shape. This is done using the following workflow.
    1) If an internal node or not along the edge of the contour is found, the following decision can be made:
        - If there are internal nodes only:
            - If the shape is a quadrilateral
                - If triangle, mesh is allowed, the shape will be split into 4 triangles about the internal point
                - Otherwise, the shape will be split into 4, about the centre node
            - If the shape is a triangle
                - The shape will be split into three triangles about the internal node
        - If there are edge nodes and internal nodes:
            - If the shape is a quadrilateral
                - If ignore_centre_node is true, the shape will be split in one axis only. I.e. a rectangle would be
                be split vertically or horizontally based on what edge the nodes to mesh are on
                - Else, the shape will be split into four, using the edge nodes and any internal nodes (if no internal
                nodes, a node at the centroid will be created)
            - If the shape is a triangle
                - The triangle plate will be split into up to 6 triangle plates, based on the number of edges with edge
                nodes to mesh
    2) If new line shapes/ surface shapes are created. Any loads applied to the original object are translated onto the
    line shapes/ surface shapes. If the original object is a connected shape to a load/support, the connected object
    is updated to be the new generated object which is connected to the line/node.
    3) The original object which was split and all its repositories are added to the "shapes_to_remove" list and the
    "loads to delete" list.

    NOTE: - For line loads it does not consider if a function was applied to the original line load

    Input:
        - project: Project object containing collections of fem objects an project variables.
        - shape (Shape): shape in question that is to be meshed
        - shapes_to_remove (list): list of shapes to remove, default is blank
        - loads_to_delete (list): list of loads to delete, default is blank
        - shapes_to_check_connections (list): list of shapes which are adjoining which need to be checked for knock on
        impact, default is blank
        - triangle_mesh_allowed (bool): Permit the use of triangular plates. Note: This often can be far faster to
        complete solving the mesh
        - ignore_centre_node (bool): If true, this will ignore the centre node when splitting a rectangular plate up. It
        is advised that this is left as true unless being used in the mesh suitability checker.

    Output:
        The project is updated by creating any loads and supports that are now needed to support the mesh. The mesh
        across the surface is now all suitably connected.

        The following is returned:
        - Updated "shapes_to_remove" list,
        - Updated "loads_to_delete" list
        - Updated  "shapes_to_check_connections" list
        - "mesh_suitable" which is a boolean that determines if the mesh is suitable or not. if not, other shapes should
        be checked.
    """

    # obtain object properties
    material = shape.material
    geometry = shape.geometry
    # Check if any point lies on the contour
    edge_nodes_to_mesh = []
    internal_nodes_to_mesh = []
    if shape.internal_points is None:
        pass
    else:
        for j in shape.internal_points:
            internal_nodes_to_mesh.append(j)

    def determine_nodes_along_edge_of_shape_to_be_meshed(shape):
        """
        Determines the nodes along the perimeter of the shape that need to be accounted for in the mesh. This is done by
        determining the corners of the shape and then isolating the nodes that are outstanding along the edge.
        Returns: the contour nodes (contour_nodes), the corners of the shape (corners), the edge nodes to be accounted
        for in the mesh (edge_nodes_to_mesh), Number of corners to identify what type of shape it is (no_of_corners)
        """
        # Gather the contour nodes, including those that are internal points between corners
        contour_nodes = []
        for j in range(len(shape.contour.lines)):
            if j != len(shape.contour.lines) - 1:
                if shape.contour.lines[j].node_start == shape.contour.lines[j + 1].node_start or \
                        shape.contour.lines[j].node_start == shape.contour.lines[j + 1].node_end:
                    contour_nodes.append(shape.contour.lines[j].node_end)
                else:
                    contour_nodes.append(shape.contour.lines[j].node_start)
            else:
                if shape.contour.lines[j].node_start == shape.contour.lines[0].node_start or \
                        shape.contour.lines[j].node_start == shape.contour.lines[0].node_end:
                    contour_nodes.append(shape.contour.lines[j].node_end)
                else:
                    contour_nodes.append(shape.contour.lines[j].node_start)
        # Identify the number of corners to identify if its a triangle or quadrilateral
        no_of_corners = 0
        for k in range(len(contour_nodes)):
            if k == 0:
                if fem_point_on_line(contour_nodes[k],
                                     [contour_nodes[(len(contour_nodes) - 1)], contour_nodes[k + 1]]) is False:
                    no_of_corners += 1
            elif k == (len(contour_nodes) - 1):
                if fem_point_on_line(contour_nodes[k],
                                     [contour_nodes[k - 1], contour_nodes[0]]) is False:
                    no_of_corners += 1
            else:
                if fem_point_on_line(contour_nodes[k],
                                     [contour_nodes[k - 1], contour_nodes[k + 1]]) is False:
                    no_of_corners += 1
        corners = {}
        # Identify the corners, maintaining the original order of the original plate to maintain orientation
        # corner 1 is the first node
        corners['corner_1'] = contour_nodes[0]
        corner_counter = 2
        # Using the exercise above, you now know whether its a triangle or quadrilateral and therefore can find
        # the corners and number them
        if no_of_corners == 3:
            # loop through contour nodes determining when there is a corner by checking if the node is on the
            # same line as the previous node and the next one in the order
            for j in range(len(contour_nodes)):
                if j == 0:
                    continue
                elif j == len(contour_nodes) - 2:
                    if 'corner_2' not in corners:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
                        continue
                elif j == len(contour_nodes) - 1:
                    if 'corner_3' not in corners:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
                        continue
                if j != len(contour_nodes) - 1:
                    if fem_point_on_line(contour_nodes[j], [contour_nodes[j - 1], contour_nodes[j + 1]]) is False:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
        else:
            # loop through contour nodes determining when there is a corner by checking if the node is on the
            # same line as the previous node and the next one in the order
            for j in range(len(contour_nodes)):
                if j == 0:
                    continue
                elif j == len(contour_nodes) - 3:
                    if 'corner_2' not in corners:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
                        continue
                elif j == len(contour_nodes) - 2:
                    if 'corner_3' not in corners:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
                        continue
                elif j == len(contour_nodes) - 1:
                    if 'corner_4' not in corners:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
                        continue
                if j != len(contour_nodes) - 1:
                    if fem_point_on_line(contour_nodes[j], [contour_nodes[j - 1], contour_nodes[j + 1]]) is False:
                        corners[f'corner_{corner_counter}'] = contour_nodes[j]
                        corner_counter += 1
        # for each node in the contour nodes. if it is not a corner node it is therefore a node that needs to
        # be included in the mesh. This can be identified by checking the corners we just found
        for j in contour_nodes:
            if j not in corners.values():
                edge_nodes_to_mesh.append(j)
        return contour_nodes, corners, edge_nodes_to_mesh, no_of_corners

    contour_nodes, corners, edge_nodes_to_mesh, no_of_corners = determine_nodes_along_edge_of_shape_to_be_meshed(shape)

    # if there are no internal nodes to mesh and no edge nodes to mesh, return as nothing to be meshed
    if len(edge_nodes_to_mesh) == 0 and len(internal_nodes_to_mesh) == 0:
        return shapes_to_remove, loads_to_delete, shapes_to_check_connections, mesh_suitable
    # Otherwise proceed and first check if there is just internal nodes
    elif len(edge_nodes_to_mesh) == 0:
        # shape in question now is to be meshed and therefore will need to be removed from the project
        shapes_to_remove.append(shape)
        # mesh is not suitable yet so the while loop needs to continue
        mesh_suitable = False

        def mesh_shape_with_only_internal_nodes(internal_nodes_to_mesh):
            """
            Function used to mesh shapes that only have internal nodes, where there are no nodes along the perimeter
            """
            # If there are multiple internal nodes, find the closest one to the centre
            if len(internal_nodes_to_mesh) > 1:
                temp_dict_to_measure_distance = {}
                for internal_node in internal_nodes_to_mesh:
                    temp_dict_to_measure_distance[f'{internal_node.id}'] = internal_node.coordinates
                closest, index = fem_closest_point(shape.contour.get_centroid(),
                                                   list(temp_dict_to_measure_distance.values()))
                id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                    list(temp_dict_to_measure_distance.values()).index(list(closest))]
                for internal_node in internal_nodes_to_mesh:
                    if internal_node.id == int(id_of_centre_node):
                        centre_node = internal_node
                        break
            else:
                # if only one internal node, use that
                centre_node = internal_nodes_to_mesh[0]
            # If the shape is a triangle, you can then split this into three triangles about the centre node
            temp_contour_dict = {}
            if no_of_corners == 3:
                # Create contours for the 3 new areas created from the original panel
                temp_contour_dict[f'c1'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                    corners['corner_2'].coordinates,
                                                                    centre_node.coordinates])
                temp_contour_dict[f'c2'] = project.create_polyline([centre_node.coordinates,
                                                                    corners['corner_2'].coordinates,
                                                                    corners['corner_3'].coordinates])
                temp_contour_dict[f'c3'] = project.create_polyline([centre_node.coordinates,
                                                                    corners['corner_3'].coordinates,
                                                                    corners['corner_1'].coordinates])
            # If the shape is a quadrilateral and you have chosen to accept triangle mesh, split the shape into
            # four different triangles about the internal node
            elif no_of_corners == 4 and triangle_mesh_allowed is True:
                # Create contours for the 4 new areas created from the original panel
                temp_contour_dict[f'c1'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                    corners['corner_2'].coordinates,
                                                                    centre_node.coordinates])
                temp_contour_dict[f'c2'] = project.create_polyline([centre_node.coordinates,
                                                                    corners['corner_2'].coordinates,
                                                                    corners['corner_3'].coordinates])
                temp_contour_dict[f'c3'] = project.create_polyline([centre_node.coordinates,
                                                                    corners['corner_3'].coordinates,
                                                                    corners['corner_4'].coordinates])
                temp_contour_dict[f'c4'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                    centre_node.coordinates,
                                                                    corners['corner_4'].coordinates])
            # Else, if shape is a quadrilateral and chosen not to use triangles, split into four squares about
            # the internal point
            else:
                # As splitting into four squares, need intermediate nodes between each corner
                edge_node_1 = project.create_node(coordinates=[(corners['corner_1'].coordinates[0] +
                                                                corners['corner_2'].coordinates[0]) / 2,
                                                               (corners['corner_1'].coordinates[1] +
                                                                corners['corner_2'].coordinates[1]) / 2,
                                                               (corners['corner_1'].coordinates[2] +
                                                                corners['corner_2'].coordinates[2]) / 2])
                edge_node_2 = project.create_node(coordinates=[(corners['corner_2'].coordinates[0] +
                                                                corners['corner_3'].coordinates[0]) / 2,
                                                               (corners['corner_2'].coordinates[1] +
                                                                corners['corner_3'].coordinates[1]) / 2,
                                                               (corners['corner_2'].coordinates[2] +
                                                                corners['corner_3'].coordinates[2]) / 2])
                edge_node_3 = project.create_node(coordinates=[(corners['corner_3'].coordinates[0] +
                                                                corners['corner_4'].coordinates[0]) / 2,
                                                               (corners['corner_3'].coordinates[1] +
                                                                corners['corner_4'].coordinates[1]) / 2,
                                                               (corners['corner_3'].coordinates[2] +
                                                                corners['corner_4'].coordinates[2]) / 2])
                edge_node_4 = project.create_node(coordinates=[(corners['corner_4'].coordinates[0] +
                                                                corners['corner_1'].coordinates[0]) / 2,
                                                               (corners['corner_4'].coordinates[1] +
                                                                corners['corner_1'].coordinates[1]) / 2,
                                                               (corners['corner_4'].coordinates[2] +
                                                                corners['corner_1'].coordinates[2]) / 2])
                # To maintain the direction of members, determine if any members along the edges of the plate
                # must be split before creating new plates
                # get any connecting shapes to the current plate
                connecting_elements = shape.get_connecting_shapes()
                # nodes along the edge which are now new are to be created as a list
                edge_nodes = [edge_node_1, edge_node_2, edge_node_3, edge_node_4]
                for element in connecting_elements:
                    # if an element is a beam/column
                    if hasattr(element.contour, 'node_start'):
                        # determine if it needs to be meshed considering its internal points as well as the new
                        # generated edge nodes
                        returned_list = mesh_line_shape_with_internal_point(project, element, edge_nodes)
                        if returned_list is None:
                            continue
                        else:
                            temp_beam_dict = returned_list[0]
                            load_to_delete = returned_list[1]
                            shapes_to_remove.append(element)
                            loads_to_delete.extend(load_to_delete)
                            # repeat as above, obtain all elements that are in the effected area of the model to
                            # check for new found connectivity and to ensure mesh is suitable
                            shapes_to_check_connections.extend(element.get_connecting_shapes())
                            if element.internal_lines is not None:
                                for internal_line in element.internal_lines:
                                    for shape_object in project.collections.shapes:
                                        if hasattr(shape_object.contour,
                                                   'node_start') and shape_object.contour == internal_line:
                                            shapes_to_check_connections.append(shape_object)
                                        elif hasattr(shape_object.contour,
                                                     'lines') and internal_line in shape_object.contour.lines:
                                            shapes_to_check_connections.append(shape_object)
                            for value in temp_beam_dict:
                                shapes_to_check_connections.append(temp_beam_dict[value])
                # Create contours for the 4 new areas created from the original panel
                temp_contour_dict[f'c1'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                    edge_node_1.coordinates,
                                                                    centre_node.coordinates,
                                                                    edge_node_4.coordinates])
                temp_contour_dict[f'c2'] = project.create_polyline([edge_node_1.coordinates,
                                                                    corners['corner_2'].coordinates,
                                                                    edge_node_2.coordinates,
                                                                    centre_node.coordinates])
                temp_contour_dict[f'c3'] = project.create_polyline([centre_node.coordinates,
                                                                    edge_node_2.coordinates,
                                                                    corners['corner_3'].coordinates,
                                                                    edge_node_3.coordinates])
                temp_contour_dict[f'c4'] = project.create_polyline([edge_node_4.coordinates,
                                                                    centre_node.coordinates,
                                                                    edge_node_3.coordinates,
                                                                    corners['corner_4'].coordinates])
            # generate 4 new panels for the project
            temp_surface_dict = {}
            l = 0
            for key in temp_contour_dict:
                value = temp_contour_dict[key]
                temp_surface_dict[f'plate{l}'] = project.create_surface(shape_polyline=value,
                                                                        material=material,
                                                                        geometry=geometry)
                temp_surface_dict[f'plate{l}'].mesh_shape(1, 1)
                l += 1
            return temp_surface_dict

        temp_surface_dict = mesh_shape_with_only_internal_nodes(internal_nodes_to_mesh)
    # Else is for when edge nodes are needed to be taken into account if there are any present
    else:
        # shape in question now is to be meshed and therefore will need to be removed from the project
        shapes_to_remove.append(shape)
        # mesh is not suitable yet so the while loop needs to continue
        mesh_suitable = False

        def mesh_shape_with_edge_nodes(edge_nodes_to_mesh, internal_nodes_to_mesh):
            """
            Function to mesh a shape which has edge nodes present
            """
            # Define all the nodes of your meshed shape
            # If there are internal nodes - if only one, use first one of these. If more than 1, use closest to
            # centroid of shape
            if len(internal_nodes_to_mesh) > 1:
                temp_dict_to_measure_distance = {}
                for internal_node in internal_nodes_to_mesh:
                    temp_dict_to_measure_distance[f'{internal_node.id}'] = internal_node.coordinates
                closest, index = fem_closest_point(shape.contour.get_centroid(),
                                                   list(temp_dict_to_measure_distance.values()))
                id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                    list(temp_dict_to_measure_distance.values()).index(list(closest))]
                for internal_node in internal_nodes_to_mesh:
                    if internal_node.id == int(id_of_centre_node):
                        centre_node = internal_node
                        break
            elif len(internal_nodes_to_mesh) == 1:
                centre_node = internal_nodes_to_mesh[0]
            # # otherwise create new node at the centre of the project
            elif no_of_corners == 3 or ignore_centre_node is False:
                centre_node = project.create_node(coordinates=shape.contour.get_centroid())

            # If the shape is a triangle, determine the edge nodes along the shape
            def mesh_triangle_shape_with_edges_nodes():
                """
                Function meshes a triangular shape which has edge nodes and returns the new shapes from it
                """
                edge_node_1 = None
                edge_node_2 = None
                edge_node_3 = None
                edge_nodes_along_edge1 = []
                edge_nodes_along_edge2 = []
                edge_nodes_along_edge3 = []
                edges_nodes_triangle = []
                # Determine what corner the nodes in edge nodes to mesh sit between to be the intermediate node
                # Determine the node which is closest to the centre of the edge in question
                # Edge node 1 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_1'], corners['corner_2']]) is True:
                        edge_nodes_along_edge1.append(j)
                if len(edge_nodes_along_edge1) > 0:
                    temp_dict_to_measure_distance = {}
                    for edge_node in edge_nodes_along_edge1:
                        temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                    centre = [(corners['corner_1'][0] + corners['corner_2'][0]) / 2,
                              (corners['corner_1'][1] + corners['corner_2'][1]) / 2,
                              (corners['corner_1'][2] + corners['corner_2'][2]) / 2]
                    closest, index = fem_closest_point(centre,
                                                       list(temp_dict_to_measure_distance.values()))
                    id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                        list(temp_dict_to_measure_distance.values()).index(list(closest))]
                    for edge_node in edge_nodes_along_edge1:
                        if edge_node.id == int(id_of_centre_node):
                            edge_node_1 = edge_node
                            edges_nodes_triangle.append(edge_node_1)
                            break
                # Repeat and find most central edge node
                # Edge node 2 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_2'], corners['corner_3']]) is True:
                        edge_nodes_along_edge2.append(j)
                if len(edge_nodes_along_edge2) > 0:
                    temp_dict_to_measure_distance = {}
                    for edge_node in edge_nodes_along_edge2:
                        temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                    centre = [(corners['corner_2'][0] + corners['corner_3'][0]) / 2,
                              (corners['corner_2'][1] + corners['corner_3'][1]) / 2,
                              (corners['corner_2'][2] + corners['corner_3'][2]) / 2]
                    closest, index = fem_closest_point(centre,
                                                       list(temp_dict_to_measure_distance.values()))
                    id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                        list(temp_dict_to_measure_distance.values()).index(list(closest))]
                    for edge_node in edge_nodes_along_edge2:
                        if edge_node.id == int(id_of_centre_node):
                            edge_node_2 = edge_node
                            edges_nodes_triangle.append(edge_node_2)
                            break
                # Repeat and find most central edge node
                # Edge node 3 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_3'], corners['corner_1']]) is True:
                        edge_nodes_along_edge3.append(j)
                if len(edge_nodes_along_edge3) > 0:
                    temp_dict_to_measure_distance = {}
                    for edge_node in edge_nodes_along_edge3:
                        temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                    centre = [(corners['corner_3'][0] + corners['corner_1'][0]) / 2,
                              (corners['corner_3'][1] + corners['corner_1'][1]) / 2,
                              (corners['corner_3'][2] + corners['corner_1'][2]) / 2]
                    closest, index = fem_closest_point(centre,
                                                       list(temp_dict_to_measure_distance.values()))
                    id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                        list(temp_dict_to_measure_distance.values()).index(list(closest))]
                    for edge_node in edge_nodes_along_edge3:
                        if edge_node.id == int(id_of_centre_node):
                            edge_node_3 = edge_node
                            edges_nodes_triangle.append(edge_node_3)
                            break
                # To maintain the direction of members, determine if any members along the edges of the plate
                # must be split before creating new plates
                # get any connecting shapes to the current plate
                connecting_elements = shape.get_connecting_shapes()
                for element in connecting_elements:
                    # if an element is a beam/column
                    if hasattr(element.contour, 'node_start'):
                        # determine if it needs to be meshed considering its internal points as well as the new
                        # generated edge nodes
                        returned_list = mesh_line_shape_with_internal_point(project, element,
                                                                            edges_nodes_triangle)
                        if returned_list is None:
                            continue
                        else:
                            temp_beam_dict = returned_list[0]
                            load_to_delete = returned_list[1]
                            shapes_to_remove.append(element)
                            loads_to_delete.extend(load_to_delete)
                            # repeat as above, obtain all elements that are in the effected area of the model to
                            # check for new found connectivity and to ensure mesh is suitable
                            shapes_to_check_connections.extend(element.get_connecting_shapes())
                            if element.internal_lines is not None:
                                for internal_line in element.internal_lines:
                                    for shape_object in project.collections.shapes:
                                        if hasattr(shape_object.contour,
                                                   'node_start') and shape_object.contour == internal_line:
                                            shapes_to_check_connections.append(shape_object)
                                        elif hasattr(shape_object.contour,
                                                     'lines') and internal_line in shape_object.contour.lines:
                                            shapes_to_check_connections.append(shape_object)
                            for value in temp_beam_dict:
                                shapes_to_check_connections.append(temp_beam_dict[value])
                # Create contours for the new areas created from the original panel. This is about the centre of
                # the triangle. Therefore creating, up to 6 new triangles, depending on if there is edge nodes
                temp_contour_dict = {}
                if edge_node_1 is None:
                    temp_contour_dict[f'c1'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                        corners['corner_2'].coordinates,
                                                                        centre_node.coordinates])
                else:
                    temp_contour_dict[f'c1'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                        edge_node_1.coordinates,
                                                                        centre_node.coordinates])
                    temp_contour_dict[f'c2'] = project.create_polyline([edge_node_1.coordinates,
                                                                        corners['corner_2'].coordinates,
                                                                        centre_node.coordinates])
                if edge_node_2 is None:
                    temp_contour_dict[f'c3'] = project.create_polyline([corners['corner_2'].coordinates,
                                                                        corners['corner_3'].coordinates,
                                                                        centre_node.coordinates])
                else:
                    temp_contour_dict[f'c3'] = project.create_polyline([corners['corner_2'].coordinates,
                                                                        edge_node_2.coordinates,
                                                                        centre_node.coordinates])
                    temp_contour_dict[f'c4'] = project.create_polyline([edge_node_2.coordinates,
                                                                        corners['corner_3'].coordinates,
                                                                        centre_node.coordinates])
                if edge_node_3 is None:
                    temp_contour_dict[f'c5'] = project.create_polyline([corners['corner_3'].coordinates,
                                                                        corners['corner_1'].coordinates,
                                                                        centre_node.coordinates])
                else:
                    temp_contour_dict[f'c5'] = project.create_polyline([corners['corner_3'].coordinates,
                                                                        edge_node_3.coordinates,
                                                                        centre_node.coordinates])
                    temp_contour_dict[f'c6'] = project.create_polyline([edge_node_3.coordinates,
                                                                        corners['corner_1'].coordinates,
                                                                        centre_node.coordinates])
                # generate new panels for the project
                temp_surface_dict = {}
                l = 0
                for key in temp_contour_dict:
                    value = temp_contour_dict[key]
                    temp_surface_dict[f'plate{l}'] = project.create_surface(shape_polyline=value,
                                                                            material=material,
                                                                            geometry=geometry)
                    temp_surface_dict[f'plate{l}'].mesh_shape(1, 1)
                    l += 1
                return temp_surface_dict

            def mesh_quadrilateral_shape_with_nodes_along_edge():
                """
                Function meshes a quadrilateral shape that has nodes along its edge and returns a series of new shapes
                to account for this
                """
                # determine the edge nodes to be used within the meshing
                edge_node_1 = None
                edge_node_2 = None
                edge_node_3 = None
                edge_node_4 = None
                # Determine what corner the nodes in edge nodes to mesh sit between to be the intermediate node
                edge_nodes_along_edge1 = []
                edge_nodes_along_edge2 = []
                edge_nodes_along_edge3 = []
                edge_nodes_along_edge4 = []
                # Edge node 1 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_1'], corners['corner_2']]) is True:
                        edge_nodes_along_edge1.append(j)
                # Edge node 2 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_2'], corners['corner_3']]) is True:
                        edge_nodes_along_edge2.append(j)
                # Edge node 3 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_3'], corners['corner_4']]) is True:
                        edge_nodes_along_edge3.append(j)
                # Edge node 4 calc
                for j in edge_nodes_to_mesh:
                    if fem_point_on_line(j, [corners['corner_1'], corners['corner_4']]) is True:
                        edge_nodes_along_edge4.append(j)

                def determine_edge_nodes_to_mesh_quadrilateral_shape_in_both_axis():
                    """
                    Determine the edge nodes to be accounted for from the quadrilateral shape that is being meshed if
                    you are permitted to mesh in both a horizontal and vertical direction. i.e. when ignore centre node
                    is false
                    """
                    # determine the edge nodes to be used within the meshing
                    edge_node_1 = None
                    edge_node_2 = None
                    edge_node_3 = None
                    edge_node_4 = None
                    # Determine edge nodes on each edge closest to the centre of that edge
                    # Edge node 1 calc
                    if len(edge_nodes_along_edge1) > 0:
                        temp_dict_to_measure_distance = {}
                        for edge_node in edge_nodes_along_edge1:
                            temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                        centre = [(corners['corner_1'][0] + corners['corner_2'][0]) / 2,
                                  (corners['corner_1'][1] + corners['corner_2'][1]) / 2,
                                  (corners['corner_1'][2] + corners['corner_2'][2]) / 2]
                        closest, index = fem_closest_point(centre,
                                                           list(temp_dict_to_measure_distance.values()))
                        id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                            list(temp_dict_to_measure_distance.values()).index(list(closest))]
                        for edge_node in edge_nodes_along_edge1:
                            if edge_node.id == int(id_of_centre_node):
                                edge_node_1 = edge_node
                                break
                    # Edge node 2 calc
                    if len(edge_nodes_along_edge2) > 0:
                        temp_dict_to_measure_distance = {}
                        for edge_node in edge_nodes_along_edge2:
                            temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                        centre = [(corners['corner_2'][0] + corners['corner_3'][0]) / 2,
                                  (corners['corner_2'][1] + corners['corner_3'][1]) / 2,
                                  (corners['corner_2'][2] + corners['corner_3'][2]) / 2]
                        closest, index = fem_closest_point(centre,
                                                           list(temp_dict_to_measure_distance.values()))
                        id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                            list(temp_dict_to_measure_distance.values()).index(list(closest))]
                        for edge_node in edge_nodes_along_edge2:
                            if edge_node.id == int(id_of_centre_node):
                                edge_node_2 = edge_node
                                break
                    # Edge node 3 calc
                    if len(edge_nodes_along_edge3) > 0:
                        temp_dict_to_measure_distance = {}
                        for edge_node in edge_nodes_along_edge3:
                            temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                        centre = [(corners['corner_3'][0] + corners['corner_4'][0]) / 2,
                                  (corners['corner_3'][1] + corners['corner_4'][1]) / 2,
                                  (corners['corner_3'][2] + corners['corner_4'][2]) / 2]
                        closest, index = fem_closest_point(centre,
                                                           list(temp_dict_to_measure_distance.values()))
                        id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                            list(temp_dict_to_measure_distance.values()).index(list(closest))]
                        for edge_node in edge_nodes_along_edge3:
                            if edge_node.id == int(id_of_centre_node):
                                edge_node_3 = edge_node
                                break
                    # Edge node 4 calc
                    if len(edge_nodes_along_edge4) > 0:
                        temp_dict_to_measure_distance = {}
                        for edge_node in edge_nodes_along_edge4:
                            temp_dict_to_measure_distance[f'{edge_node.id}'] = edge_node.coordinates
                        centre = [(corners['corner_4'][0] + corners['corner_1'][0]) / 2,
                                  (corners['corner_4'][1] + corners['corner_1'][1]) / 2,
                                  (corners['corner_4'][2] + corners['corner_1'][2]) / 2]
                        closest, index = fem_closest_point(centre,
                                                           list(temp_dict_to_measure_distance.values()))
                        id_of_centre_node = list(temp_dict_to_measure_distance.keys())[
                            list(temp_dict_to_measure_distance.values()).index(list(closest))]
                        for edge_node in edge_nodes_along_edge4:
                            if edge_node.id == int(id_of_centre_node):
                                edge_node_4 = edge_node
                                break
                    # If no node is present between each corner, generate a node exactly halfway along for each
                    # side
                    if edge_node_1 is None:
                        edge_node_1 = project.create_node(coordinates=[(corners['corner_1'].coordinates[0] +
                                                                        corners['corner_2'].coordinates[0]) / 2,
                                                                       (corners['corner_1'].coordinates[1] +
                                                                        corners['corner_2'].coordinates[1]) / 2,
                                                                       (corners['corner_1'].coordinates[2] +
                                                                        corners['corner_2'].coordinates[2]) / 2])
                    if edge_node_2 is None:
                        edge_node_2 = project.create_node(coordinates=[(corners['corner_2'].coordinates[0] +
                                                                        corners['corner_3'].coordinates[0]) / 2,
                                                                       (corners['corner_2'].coordinates[1] +
                                                                        corners['corner_3'].coordinates[1]) / 2,
                                                                       (corners['corner_2'].coordinates[2] +
                                                                        corners['corner_3'].coordinates[2]) / 2])
                    if edge_node_3 is None:
                        edge_node_3 = project.create_node(coordinates=[(corners['corner_3'].coordinates[0] +
                                                                        corners['corner_4'].coordinates[0]) / 2,
                                                                       (corners['corner_3'].coordinates[1] +
                                                                        corners['corner_4'].coordinates[1]) / 2,
                                                                       (corners['corner_3'].coordinates[2] +
                                                                        corners['corner_4'].coordinates[2]) / 2])
                    if edge_node_4 is None:
                        edge_node_4 = project.create_node(coordinates=[(corners['corner_4'].coordinates[0] +
                                                                        corners['corner_1'].coordinates[0]) / 2,
                                                                       (corners['corner_4'].coordinates[1] +
                                                                        corners['corner_1'].coordinates[1]) / 2,
                                                                       (corners['corner_4'].coordinates[2] +
                                                                        corners['corner_1'].coordinates[2]) / 2])
                    # nodes along the edge which are now new are to be created as a list
                    return [edge_node_1, edge_node_2, edge_node_3, edge_node_4]

                def determine_edge_nodes_to_mesh_quadrilateral_shape_in_one_direction():
                    """
                    Determine the edge nodes to be accounted for from the quadrilateral shape that is being meshed if
                    you are permitted to mesh in one direction, ignoring the centre node. i.e. when ignore centre node
                    is true
                    """
                    edge_nodes = []
                    edge_nodes.extend(edge_nodes_to_mesh)
                    edge_to_mesh_1 = []
                    edge_to_mesh_2 = []
                    # If edge node present along edge 1, split shape from edge 1 to edge 3
                    if len(edge_nodes_along_edge1) > 0 or len(edge_nodes_along_edge3) > 0:
                        # Create a list of nodes along each edge and order it
                        edge_to_mesh_1.append(corners['corner_1'])
                        edge_to_mesh_1.extend(edge_nodes_along_edge1)
                        edge_to_mesh_1.append(corners['corner_2'])
                        edge_to_mesh_2.append(corners['corner_3'])
                        edge_to_mesh_2.extend(edge_nodes_along_edge3)
                        edge_to_mesh_2.append(corners['corner_4'])
                        edge_to_mesh_2.reverse()
                        corner_1_of_edge_1 = corners['corner_1'].coordinates
                        corner_2_of_edge_1 = corners['corner_2'].coordinates
                        corner_1_of_edge_2 = corners['corner_4'].coordinates
                        corner_2_of_edge_2 = corners['corner_3'].coordinates
                    # If edge node present along edge 2, split shape from edge 2 to edge 4
                    else:
                        # Create a list of nodes along each edge and order it
                        edge_to_mesh_1.append(corners['corner_2'])
                        edge_to_mesh_1.extend(edge_nodes_along_edge2)
                        edge_to_mesh_1.append(corners['corner_3'])
                        edge_to_mesh_2.append(corners['corner_4'])
                        edge_to_mesh_2.extend(edge_nodes_along_edge4)
                        edge_to_mesh_2.append(corners['corner_1'])
                        edge_to_mesh_2.reverse()
                        corner_1_of_edge_1 = corners['corner_2'].coordinates
                        corner_2_of_edge_1 = corners['corner_3'].coordinates
                        corner_1_of_edge_2 = corners['corner_1'].coordinates
                        corner_2_of_edge_2 = corners['corner_4'].coordinates
                    # If the two sides in question have the same number of nodes then fine and move on
                    if len(edge_to_mesh_2) != len(edge_to_mesh_1):
                        # If either side has only 2 and the other has more than 2, add additional nodes to the
                        # edge that has only 2 to ensure it has the same number as the side that has more than 2
                        # so that a full mesh can be formed
                        if len(edge_to_mesh_2) == 2 and len(edge_to_mesh_1) > 2:
                            plate_divider = len(edge_to_mesh_1) - 1 + 0.000001
                            for m in range(len(edge_to_mesh_1) - 2):
                                temp_node = project.create_node(coordinates=
                                                                [((m + 1) * (corner_2_of_edge_2[0] - corner_1_of_edge_2[
                                                                    0]) / plate_divider) + corner_1_of_edge_2[0],
                                                                 ((m + 1) * (corner_2_of_edge_2[1] - corner_1_of_edge_2[
                                                                     1]) / plate_divider) + corner_1_of_edge_2[1],
                                                                 ((m + 1) * (corner_2_of_edge_2[2] - corner_1_of_edge_2[
                                                                     2]) / plate_divider) + corner_1_of_edge_2[2]])
                                edge_to_mesh_2.insert(len(edge_to_mesh_2) - 1, temp_node)
                                edge_nodes.append(temp_node)
                            return edge_nodes, edge_to_mesh_1, edge_to_mesh_2
                        elif len(edge_to_mesh_1) == 2 and len(edge_to_mesh_2) > 2:
                            plate_divider = len(edge_to_mesh_2) - 1 + 0.000001
                            for m in range(len(edge_to_mesh_2) - 2):
                                temp_node = project.create_node(coordinates=
                                                                [((m + 1) * (corner_2_of_edge_1[0] - corner_1_of_edge_1[
                                                                    0]) / plate_divider) + corner_1_of_edge_1[0],
                                                                 ((m + 1) * (corner_2_of_edge_1[1] - corner_1_of_edge_1[
                                                                     1]) / plate_divider) + corner_1_of_edge_1[1],
                                                                 ((m + 1) * (corner_2_of_edge_1[2] - corner_1_of_edge_1[
                                                                     2]) / plate_divider) + corner_1_of_edge_1[2]])
                                edge_to_mesh_1.insert(len(edge_to_mesh_1) - 1, temp_node)
                                edge_nodes.append(temp_node)
                            return edge_nodes, edge_to_mesh_1, edge_to_mesh_2
                        else:
                            raise ValueError(
                                'Check edge nodes to ensure there is the same number on each edge')
                    else:
                        return edge_nodes, edge_to_mesh_1, edge_to_mesh_2

                # Create contours for the new areas created from the original panel
                temp_contour_dict = {}
                # If you want to consider the shape being split up into 4 about the centre node
                if ignore_centre_node is False:
                    edge_nodes = determine_edge_nodes_to_mesh_quadrilateral_shape_in_both_axis()
                    edge_node_1 = edge_nodes[0]
                    edge_node_2 = edge_nodes[1]
                    edge_node_3 = edge_nodes[2]
                    edge_node_4 = edge_nodes[3]
                    temp_contour_dict[f'c1'] = project.create_polyline([corners['corner_1'].coordinates,
                                                                        edge_node_1.coordinates,
                                                                        centre_node.coordinates,
                                                                        edge_node_4.coordinates])
                    temp_contour_dict[f'c2'] = project.create_polyline([edge_node_1.coordinates,
                                                                        corners['corner_2'].coordinates,
                                                                        edge_node_2.coordinates,
                                                                        centre_node.coordinates])
                    temp_contour_dict[f'c3'] = project.create_polyline([centre_node.coordinates,
                                                                        edge_node_2.coordinates,
                                                                        corners['corner_3'].coordinates,
                                                                        edge_node_3.coordinates])
                    temp_contour_dict[f'c4'] = project.create_polyline([edge_node_4.coordinates,
                                                                        centre_node.coordinates,
                                                                        edge_node_3.coordinates,
                                                                        corners['corner_4'].coordinates])
                # Else, if you are to split the shape in one direction, either vertically or horizontally
                else:
                    print(determine_edge_nodes_to_mesh_quadrilateral_shape_in_one_direction())
                    edge_nodes, edge_to_mesh_1, edge_to_mesh_2 = \
                        determine_edge_nodes_to_mesh_quadrilateral_shape_in_one_direction()
                    # if ignoring the centre node and doing either splitting the shape horizontally or vertically,
                    # create X no. of new shapes
                    meshing_counter = 0
                    for node_no in range(len(edge_to_mesh_1) - 1):
                        temp_contour_dict[f'{meshing_counter}'] = \
                            project.create_polyline([edge_to_mesh_1[node_no].coordinates,
                                                     edge_to_mesh_1[node_no + 1].coordinates,
                                                     edge_to_mesh_2[node_no + 1].coordinates,
                                                     edge_to_mesh_2[node_no].coordinates])
                        meshing_counter += 1
                # generate 4 new panels for the project
                temp_surface_dict = {}
                l = 0
                for key in temp_contour_dict:
                    value = temp_contour_dict[key]
                    temp_surface_dict[f'plate{l}'] = project.create_surface(shape_polyline=value,
                                                                            material=material,
                                                                            geometry=geometry)
                    temp_surface_dict[f'plate{l}'].mesh_shape(1, 1)
                    l += 1

                # To maintain the direction of members, determine if any members along the edges of the plate
                # must be split before creating new plates
                # get any connecting shapes to the current plate
                connecting_elements = shape.get_connecting_shapes()
                if connecting_elements is None:
                    connecting_elements = []
                # Remove Nones from list
                for element in connecting_elements:
                    # if an element is a beam/column
                    if hasattr(element.contour, 'node_start'):
                        # determine if it needs to be meshed considering its internal points as well as the new
                        # generated edge nodes
                        returned_list = mesh_line_shape_with_internal_point(project, element, edge_nodes)
                        if returned_list is None:
                            continue
                        else:
                            temp_beam_dict = returned_list[0]
                            load_to_delete = returned_list[1]
                            shapes_to_remove.append(element)
                            loads_to_delete.extend(load_to_delete)
                            # repeat as above, obtain all elements that are in the effected area of the model to
                            # check for new found connectivity and to ensure mesh is suitable
                            shapes_to_check_connections.extend(element.get_connecting_shapes())
                            if element.internal_lines is not None:
                                for internal_line in element.internal_lines:
                                    for shape_object in project.collections.shapes:
                                        if hasattr(shape_object.contour,
                                                   'node_start') and shape_object.contour == internal_line:
                                            shapes_to_check_connections.append(shape_object)
                                        elif hasattr(shape_object.contour,
                                                     'lines') and internal_line in shape_object.contour.lines:
                                            shapes_to_check_connections.append(shape_object)
                            for value in temp_beam_dict:
                                shapes_to_check_connections.append(temp_beam_dict[value])

                return temp_surface_dict

            if no_of_corners == 3:
                temp_surface_dict = mesh_triangle_shape_with_edges_nodes()
            # Else, when there are edge nodes present and the shape is a quadrilateral
            else:
                temp_surface_dict = mesh_quadrilateral_shape_with_nodes_along_edge()
            return temp_surface_dict

        temp_surface_dict = mesh_shape_with_edge_nodes(edge_nodes_to_mesh, internal_nodes_to_mesh)
    # Get all shapes that need are to be checked for new connections
    shapes_to_check_connections.extend(shape.get_connecting_shapes())
    # repeat as above, obtain all elements that are in the effected area of the model to
    # check for new found connectivity and to ensure mesh is suitable
    if shape.internal_lines is not None:
        for internal_line in shape.internal_lines:
            for shape_object in project.collections.shapes:
                if hasattr(shape_object.contour, 'node_start') and \
                        shape_object.contour == internal_line:
                    shapes_to_check_connections.append(shape_object)
                elif hasattr(shape_object.contour, 'lines') and \
                        internal_line in shape_object.contour.lines:
                    shapes_to_check_connections.append(shape_object)
    for value in temp_surface_dict:
        shapes_to_check_connections.extend(temp_surface_dict[value].get_connecting_shapes())
        shapes_to_check_connections.append(temp_surface_dict[value])
    # Account for loads in plates
    # determine if any point loads are associated with the original plate and replace connecting shape
    # with new plate that has been created that shares the node
    for load in project.collections.point_loads:
        if load.connecting_shapes[0]['connecting_shape'] == shape:
            for key in temp_surface_dict:
                for line in temp_surface_dict[key].contour.lines:
                    if line.node_start == load.connecting_shapes[0]['shape_geometry'] or \
                            line.node_end == load.connecting_shapes[0]['shape_geometry']:
                        load.connecting_shapes[0]['connecting_shape'] = temp_surface_dict[key]
    # determine if any line loads are associated with the original plate
    line_load_counter = 0
    temp_line_load_dict = {}
    for load in project.collections.line_loads:
        if load.connecting_shapes[0]['connecting_shape'] == shape:
            for key in temp_surface_dict:
                for line in temp_surface_dict[key].contour.lines:
                    if line.node_start == load.connecting_shapes[0]['shape_geometry'].node_end or \
                            line.node_start == load.connecting_shapes[0]['shape_geometry'].node_start or \
                            line.node_end == load.connecting_shapes[0]['shape_geometry'].node_end or \
                            line.node_end == load.connecting_shapes[0]['shape_geometry'].node_start:
                        # Get load attributes
                        line_load_direction = load.direction
                        line_load_value = load.value
                        line_load_type = load.load_type
                        line_load_case = load.loadcase
                        loads_to_delete.append(load)
                        temp_line_load_dict[f'line_load_{line_load_counter}'] = project.create_lineload(
                            load_type=line_load_type,
                            value=line_load_value,
                            direction=line_load_direction,
                            loadcase=line_load_case,
                            connecting_shapes=[{"connecting_shape": temp_surface_dict[key],
                                                "shape_geometry": line}])
                        line_load_counter += 1
    # determine if any plate loads are associated with the original plate and create new plate loads on
    # each new plate generated
    temp_surface_load_dict = {}
    sl = 0
    for load in project.collections.surface_loads:
        if load.connecting_shapes[0]['connecting_shape'] == shape:
            loads_to_delete.append(load)
            for key in temp_surface_dict:
                temp_surface_load_dict[f'surface_load_{sl}'] = project.create_surfaceload(
                    load_type=load.load_type,
                    value=load.value,
                    direction=load.direction,
                    connecting_shapes=[{"connecting_shape": temp_surface_dict[key]}],
                    loadcase=load.loadcase)
                sl += 1
    # Account for supports where plates are the connected items
    # point supports
    for support in project.collections.point_supports:
        if support.connecting_shapes[0]['connecting_shape'] == shape:
            for key in temp_surface_dict:
                for line in temp_surface_dict[key].contour.lines:
                    if line.node_start == support.connecting_shapes[0]['shape_geometry'] or \
                            line.node_end == support.connecting_shapes[0]['shape_geometry']:
                        support.connecting_shapes[0]['connecting_shape'] = temp_surface_dict[key]
    # line supports
    line_support_dict = {}
    line_support_counter = 0
    # if shape geometry is a line of the original plate and the connecting shape is the original plate
    for support in project.collections.line_supports:
        if support.connecting_shapes[0]['connecting_shape'] == shape:
            for key in temp_surface_dict:
                for line in temp_surface_dict[key].contour.lines:
                    if line.node_start == support.connecting_shapes[0]['shape_geometry'].node_end or \
                            line.node_start == support.connecting_shapes[0]['shape_geometry'].node_start or \
                            line.node_end == support.connecting_shapes[0]['shape_geometry'].node_end or \
                            line.node_end == support.connecting_shapes[0]['shape_geometry'].node_start:
                        degrees_of_freedom = support.degrees_of_freedom
                        axes = support.axes
                        spring_stiffnesses = support.spring_stiffnesses
                        support_set = support.support_set
                        line_support_dict[
                            f'line_support{line_support_counter}'] = project.create_linesupport(
                            connecting_shapes=[{'connecting_shape': temp_surface_dict[key],
                                                'shape_geometry': line}],
                            degrees_of_freedom=degrees_of_freedom,
                            support_set=support_set,
                            axes=axes,
                            spring_stiffnesses=spring_stiffnesses)
                        line_support_counter += 1
    # Surface support check/creation
    surface_support_dict = {}
    surface_support_counter = 0
    for support in project.collections.surface_supports:
        if support.connecting_shapes[0]['connecting_shape'] == shape:
            degrees_of_freedom = support.degrees_of_freedom
            axes = support.axes
            spring_stiffnesses = support.spring_stiffnesses
            support_set = support.support_set
            for key in temp_surface_dict:
                surface_support_dict[
                    f'surface_support{surface_support_counter}'] = project.create_surfacesupport(
                    connecting_shapes=[{'connecting_shape': temp_surface_dict[key],
                                        'shape_geometry': temp_surface_dict[key].contour}],
                    degrees_of_freedom=degrees_of_freedom,
                    support_set=support_set,
                    axes=axes,
                    spring_stiffnesses=spring_stiffnesses)
                surface_support_counter += 1
    return shapes_to_remove, loads_to_delete, shapes_to_check_connections, mesh_suitable


def fem_mesh_suitability_checker(project: 'Project', triangle_mesh_allowed=False, ignore_centre_node=False):
    """
    This function is used to check the suitability of the mesh within the structure. It ensures that all shapes (line
    shapes, surface shape and nodes) are connected appropriately. This is done using the following workflow.
    1) Connects all shapes within the project to identify any internal/incorrectly connected members
    2) For each shape in the project (line shape, surface shape), the shape is checked to ensure it does not have any
    internal points either inside the objects contour or along the contour of the object.
    3) If an internal node or not along the edge of the contour is found, the following decision can be made:
        - If there are internal nodes only:
            - If the shape is a quadrilateral
                - If triangle, mesh is allowed, the shape will be split into 4 triangles about the internal point
                - Otherwise, the shape will be split into 4, about the centre node
            - If the shape is a triangle
                - The shape will be split into three triangles about the internal node
        - If there are edge nodes and internal nodes:
            - If the shape is a quadrilateral
                - If ignore_centre_node is true, the shape will be split in one axis only. I.e. a rectangle would be
                be split vertically or horizontally based on what edge the nodes to mesh are on
                - Else, the shape will be split into four, using the edge nodes and any internal nodes (if no internal
                nodes, a node at the centroid will be created)
            - If the shape is a triangle
                - The triangle plate will be split into up to 6 triangle plates, based on the number of edges with edge
                nodes to mesh
    4) If new line shapes/ surface shapes are created. Any loads applied to the original object are translated onto the
    line shapes/ surface shapes. If the original object is a connected shape to a load/support, the connected object
    is updated to be the new generated object which is connected to the line/node.
    5) The original object which was split and all its repositories are removed from the project
    6) All relevant shapes in the project are reconnected and the process repeats until the mesh is suitable across the
    project.

    NOTE: - For line loads it does not consider if a function was applied to the original line load

    Input:
        - project: Project object containing collections of fem objects an project variables.
        - triangle_mesh_allowed (bool): Permit the use of triangular plates. Note: This often can be far faster to
        complete solving the mesh
        - ignore_centre_node (bool): If true, this will ignore the centre node when splitting a rectangular plate up. It
        is advised that this is left as true unless being used in the mesh suitability checker.
    Output:
        The project is updated by removing all shapes that have been split up as well as any loads and supports
        associated with any shape that has been split up. The project is updated with all new shapes, loads and supports
        for all newly generated objects. The mesh across the structure is now all suitably connected.
    """
    # connect all shapes in the project to determine any internal nodes for all shapes
    project.connect_all_shapes()
    mesh_suitable = False
    while mesh_suitable is False:
        shapes_to_remove = []
        loads_to_delete = []
        shapes_to_check_connections = []
        for i in project.collections.shapes:
            # Check if the shape is a column or beam
            if hasattr(i.contour, 'node_start'):
                # use mesh_member_with_internal_point to determine if member is to be meshed or not
                returned_list = mesh_line_shape_with_internal_point(project, i)
                # if member doesnt require to be meshed, it will return None
                if returned_list is None:
                    continue
                else:
                    # obtain objects that were created
                    temp_beam_dict = returned_list[0]
                    load_to_delete = returned_list[1]
                    # Append original object ready to be removed from the project later on
                    shapes_to_remove.append(i)
                    loads_to_delete.extend(load_to_delete)
                    # Create a list of all the new objects created, any neighbouring objects and any internal beams so
                    # they can be checked for new connections formed
                    shapes_to_check_connections.extend(i.get_connecting_shapes())
                    if i.internal_lines is not None:
                        for internal_line in i.internal_lines:
                            for shape_object in project.collections.shapes:
                                if hasattr(shape_object.contour,
                                           'node_start') and shape_object.contour == internal_line:
                                    shapes_to_check_connections.append(shape_object)
                                elif hasattr(shape_object.contour,
                                             'lines') and internal_line in shape_object.contour.lines:
                                    shapes_to_check_connections.append(shape_object)
                    for value in temp_beam_dict:
                        shapes_to_check_connections.append(temp_beam_dict[value])
                    break
            # Else the shape is a floor or wall
            else:
                shapes_to_remove, loads_to_delete, shapes_to_check_connections, mesh_suitable = \
                    mesh_surface_shape(project, i, shapes_to_remove, loads_to_delete, shapes_to_check_connections,
                                       triangle_mesh_allowed, ignore_centre_node)
                if mesh_suitable is False:
                    break
        # Remove duplicates to optimise speed
        temp_shape_dict = {}
        temp_shapes_to_delete = {}
        # remove duplicates of shapes which are to be removed from the project
        for shape in shapes_to_remove:
            if shape.name not in temp_shapes_to_delete.keys():
                temp_shapes_to_delete[f'{shape.name}'] = shape
            else:
                pass
        # remove duplicates of shapes which are to be checked for connections
        for shape in shapes_to_check_connections:
            if shape.name not in temp_shape_dict.keys() and shape.name not in temp_shapes_to_delete.keys():
                temp_shape_dict[f'{shape.name}'] = shape
            else:
                pass
        shapes_to_check_connections = []
        for key in temp_shape_dict:
            shapes_to_check_connections.append(temp_shape_dict[key])
        # Remove shapes from project
        if len(temp_shapes_to_delete) > 0:
            for key, value in temp_shapes_to_delete.items():
                value.remove_shape()
            project.connect_all_shapes(shapes_list=shapes_to_check_connections)
        else:
            mesh_suitable = True


def shape_mesh_suitability_corrector(project, triangle_mesh_allowed=False, allowable_aspect_ratio=4,
                                     maximum_internal_angle=120, minimum_internal_angle=60):
    """
        This function is used to check the suitability of the mesh within the model and to ensure all surface shapes
        have suitable geometry. In finite element modelling, it is advised that mesh plates have appropriate aspect
        ratios (width to height ratio etc). The function will determine if all surface shapes within the model comply
        with the rules outlined in the input parameters. If a surface shape is found to have an inappropriate aspect
        ratio, the function will split this shape up into a minimum number of new shapes that all comply with the aspect
        ratio defined. This uses the fem_mesh_suitability_checker function to do so (see this function for further
        information as to how this is done). In addition, a surface shape is also checked to ensure all internal angles
        are appropriate and ae within the range between the maximum_internal_angle and the minimum_internal_angle
        defined. If found to be inappropriate, a node will be produced at the centre of this surface shape and the shape
        is split into 4 triangles.

        Note: Only quadrilateral shapes are checked currently. All triangular shapes are not assessed.

        Input:
            - project: Project object containing collections of fem objects an project variables.
            - triangle_mesh_allowed (bool): Permit the use of triangular plates. Note: This is defaulted as false as
            all triangular shapes produced cant be checked.
            - allowable_aspect_ratio (int): Maximum aspect ratio permitted. Default value is 4 which indicates a 4:1
            ratio is allowed
            - maximum_internal_angle (int): Maximum permitted internal angle within the shape
            - minimum_internal_angle (int): Minimum permitted internal angle within the shape
        Output:
            - Updates the project with all surface shapes which are compliant with the rules outlined by the input
            parameters
        """
    # Check the mesh suitability
    project.connect_all_shapes()
    fem_mesh_suitability_checker(project, triangle_mesh_allowed=triangle_mesh_allowed)
    # Set the geometry check to false
    shape_geometry_checker_ok = False
    # Begin while loop to circle through shapes to ensure all ok
    while shape_geometry_checker_ok is False:
        # Set now to true, if any not found suitable, this will be then changed to false as the below loop goes on
        shape_geometry_checker_ok = True
        max_aspect_ratio = 0
        max_aspect_ratio_shape = None
        for shape in project.collections.shapes:
            # if shape is a triangle
            if hasattr(shape.contour, 'node_start'):
                continue
            elif len(shape.contour.lines) != 4:
                continue
            else:
                def determine_aspect_ratio_of_shape(shape):
                    """
                    Determines the aspect ratio of the shape and returns the maximum aspect ratio and the shape in
                    question
                    """
                    # Gather the contour nodes
                    contour_nodes = []
                    for j in range(len(shape.contour.lines)):
                        if j != len(shape.contour.lines) - 1:
                            if shape.contour.lines[j].node_start == shape.contour.lines[j + 1].node_start or \
                                    shape.contour.lines[j].node_start == shape.contour.lines[j + 1].node_end:
                                contour_nodes.append(shape.contour.lines[j].node_end)
                            else:
                                contour_nodes.append(shape.contour.lines[j].node_start)
                        else:
                            if shape.contour.lines[j].node_start == shape.contour.lines[0].node_start or \
                                    shape.contour.lines[j].node_start == shape.contour.lines[0].node_end:
                                contour_nodes.append(shape.contour.lines[j].node_end)
                            else:
                                contour_nodes.append(shape.contour.lines[j].node_start)
                    # Identify the corners
                    corner1 = contour_nodes[0].coordinates
                    corner2 = contour_nodes[1].coordinates
                    corner3 = contour_nodes[2].coordinates
                    corner4 = contour_nodes[3].coordinates
                    side_ab = fem_distance_coordinates(corner1, corner2)
                    side_bc = fem_distance_coordinates(corner2, corner3)
                    side_cd = fem_distance_coordinates(corner3, corner4)
                    side_da = fem_distance_coordinates(corner4, corner1)
                    # Determine if any side has an aspect ratio larger than the allowable aspect ratio
                    if max(side_ab / side_bc, side_ab / side_da, side_cd / side_bc,
                           side_cd / side_da) > allowable_aspect_ratio:
                        # if true, determine what the ratio is
                        aspect_ratio = max(side_ab / side_bc, side_ab / side_da, side_cd / side_bc, side_cd / side_da)
                    else:
                        # If true, determine what the aspect ratio is
                        aspect_ratio = max(side_bc / side_ab, side_bc / side_cd, side_da / side_ab, side_da / side_cd)
                    return aspect_ratio

                aspect_ratio = determine_aspect_ratio_of_shape(shape)
                if aspect_ratio > max_aspect_ratio:
                    max_aspect_ratio = aspect_ratio
                    max_aspect_ratio_shape = shape

        def split_shape_with_aspect_ratio_which_is_too_large():
            """
            Function to create the necessary edge nodes ready for the shape to meshed so that it then is split up
            into enough shapes that all comply with the aspect ratio requirements.
            """
            # Gather the contour nodes
            contour_nodes = []
            for j in range(len(max_aspect_ratio_shape.contour.lines)):
                if j != len(max_aspect_ratio_shape.contour.lines) - 1:
                    if max_aspect_ratio_shape.contour.lines[j].node_start == \
                            max_aspect_ratio_shape.contour.lines[j + 1].node_start or \
                            max_aspect_ratio_shape.contour.lines[j].node_start == \
                            max_aspect_ratio_shape.contour.lines[j + 1].node_end:
                        contour_nodes.append(max_aspect_ratio_shape.contour.lines[j].node_end)
                    else:
                        contour_nodes.append(max_aspect_ratio_shape.contour.lines[j].node_start)
                else:
                    if max_aspect_ratio_shape.contour.lines[j].node_start == \
                            max_aspect_ratio_shape.contour.lines[0].node_start or \
                            max_aspect_ratio_shape.contour.lines[j].node_start == \
                            max_aspect_ratio_shape.contour.lines[0].node_end:
                        contour_nodes.append(max_aspect_ratio_shape.contour.lines[j].node_end)
                    else:
                        contour_nodes.append(max_aspect_ratio_shape.contour.lines[j].node_start)
            # Identify the corners
            corner1 = contour_nodes[0].coordinates
            corner2 = contour_nodes[1].coordinates
            corner3 = contour_nodes[2].coordinates
            corner4 = contour_nodes[3].coordinates
            side_ab = fem_distance_coordinates(corner1, corner2)
            side_bc = fem_distance_coordinates(corner2, corner3)
            side_cd = fem_distance_coordinates(corner3, corner4)
            side_da = fem_distance_coordinates(corner4, corner1)
            # Determine if any side has an aspect ratio larger than the allowable aspect ratio
            if max(side_ab / side_bc, side_ab / side_da, side_cd / side_bc, side_cd / side_da) > allowable_aspect_ratio:
                # if true, determine what the ratio is
                aspect_ratio = max(side_ab / side_bc, side_ab / side_da, side_cd / side_bc, side_cd / side_da)
                # Determine the number of times the plates need to be split up to make them fit within the allowable
                # range
                plate_divider = math.ceil(aspect_ratio / 4)
                temp_node_dict = {}
                node_counter_ab = -1
                node_counter_dc = -1
                # Nodes along the edges AB and CD are then created based on the number of times the plate needs to be
                # divided up. Following this, the newly created nodes are connected into the plate in question to
                # become part of its contour. The same number of nodes are created on both sides
                # Plate divider is offset deliberately so that when the new plates are generated, a clear order can be
                # obtained. without this, if you were to order the nodes along AB against CD, there is no certainty that
                # the nodes will be ordered correctly
                plate_divider += 0.000001
                for j in range(int(plate_divider)):
                    if j == 0:
                        pass
                    else:
                        node_counter_ab += 1
                        temp_node_dict[f'{node_counter_ab} AB'] \
                            = project.create_node(coordinates=[(j * (corner2[0] - corner1[0]) / plate_divider) +
                                                               corner1[0],
                                                               (j * (corner2[1] - corner1[1]) / plate_divider) +
                                                               corner1[1],
                                                               (j * (corner2[2] - corner1[2]) / plate_divider) +
                                                               corner1[2]])
                        max_aspect_ratio_shape.contour.add_node(temp_node_dict[f'{node_counter_ab} AB'],
                                                                node_counter_ab)
                for j in range(int(plate_divider)):
                    if j == 0:
                        pass
                    else:
                        node_counter_dc += 1
                        temp_node_dict[f'{node_counter_dc} DC'] \
                            = project.create_node(coordinates=[(j * (corner3[0] - corner4[0]) / plate_divider) +
                                                               corner4[0],
                                                               (j * (corner3[1] - corner4[1]) / plate_divider) +
                                                               corner4[1],
                                                               (j * (corner3[2] - corner4[2]) / plate_divider) +
                                                               corner4[2]])
                        max_aspect_ratio_shape.contour.add_node(temp_node_dict[f'{node_counter_dc} DC'],
                                                                node_counter_ab + 3)
            # Determine if any side has an aspect ratio larger than the allowable aspect ratio
            elif max(side_bc / side_ab, side_bc / side_cd, side_da / side_ab,
                     side_da / side_cd) > allowable_aspect_ratio:
                # If true, determine what the aspect ratio is
                aspect_ratio = max(side_bc / side_ab, side_bc / side_cd, side_da / side_ab, side_da / side_cd)
                # Determine the number of times the plates need to be split up to make them fit within the allowable
                # range
                plate_divider = math.ceil(aspect_ratio / 4)
                temp_node_dict = {}
                node_counter_bc = -1
                node_counter_ad = -1
                # Nodes along the edges BC and DA are then created based on the number of times the plate needs to be
                # divided up. Following this, the newly created nodes are connected into the plate in question to
                # become part of its contour. The same number of nodes are created on both sides
                # Plate divider is offset deliberately so that when the new plates are generated, a clear order can be
                # obtained. without this, if you were to order the nodes along BC against DA, there is no certainty that
                # the nodes will be ordered correctly
                plate_divider += 0.000001
                for j in range(int(plate_divider)):
                    if j == 0:
                        pass
                    else:
                        node_counter_bc += 1
                        temp_node_dict[f'{node_counter_bc} BC'] \
                            = project.create_node(coordinates=[(j * (corner3[0] - corner2[0]) / plate_divider) +
                                                               corner2[0],
                                                               (j * (corner3[1] - corner2[1]) / plate_divider) +
                                                               corner2[1],
                                                               (j * (corner3[2] - corner2[2]) / plate_divider) +
                                                               corner2[2]])
                        max_aspect_ratio_shape.contour.add_node(temp_node_dict[f'{node_counter_bc} BC'],
                                                                node_counter_bc + 1)
                for j in range(int(plate_divider)):
                    if j == 0:
                        pass
                    else:
                        node_counter_ad += 1
                        temp_node_dict[f'{node_counter_ad} AD'] \
                            = project.create_node(coordinates=[(j * (corner4[0] - corner1[0]) / plate_divider) +
                                                               corner1[0],
                                                               (j * (corner4[1] - corner1[1]) / plate_divider) +
                                                               corner1[1],
                                                               (j * (corner4[2] - corner1[2]) / plate_divider) +
                                                               corner1[2]])
                        max_aspect_ratio_shape.contour.add_node(temp_node_dict[f'{node_counter_ad} AD'],
                                                                node_counter_bc + 4)

        # if the plate in question is above the allowable aspect ratio then do as follows
        if max_aspect_ratio > allowable_aspect_ratio:
            split_shape_with_aspect_ratio_which_is_too_large()
            # run the mesh suitability checker to create the new shapes from the original one
            fem_mesh_suitability_checker(project,
                                         triangle_mesh_allowed=triangle_mesh_allowed,
                                         ignore_centre_node=True)
            shape_geometry_checker_ok = False

        # Once all plates have a suitable aspect ratio, check all plates for internal angles
        for shape_for_angle_check in project.collections.shapes:
            if hasattr(shape_for_angle_check.contour, 'node_start'):
                continue
            elif len(shape_for_angle_check.contour.lines) != 4:
                continue
            internal_angle_error = False
            # gather the contour nodes
            contour_nodes = []
            for j in range(len(shape_for_angle_check.contour.lines)):
                if j != len(shape_for_angle_check.contour.lines) - 1:
                    if shape_for_angle_check.contour.lines[j].node_start == \
                            shape_for_angle_check.contour.lines[j + 1].node_start or \
                            shape_for_angle_check.contour.lines[j].node_start == \
                            shape_for_angle_check.contour.lines[j + 1].node_end:
                        contour_nodes.append(shape_for_angle_check.contour.lines[j].node_end)
                    else:
                        contour_nodes.append(shape_for_angle_check.contour.lines[j].node_start)
                else:
                    if shape_for_angle_check.contour.lines[j].node_start == \
                            shape_for_angle_check.contour.lines[0].node_start or \
                            shape_for_angle_check.contour.lines[j].node_start == \
                            shape_for_angle_check.contour.lines[0].node_end:
                        contour_nodes.append(shape_for_angle_check.contour.lines[j].node_end)
                    else:
                        contour_nodes.append(shape_for_angle_check.contour.lines[j].node_start)
            # Identify the corners
            corner1 = contour_nodes[0].coordinates
            corner2 = contour_nodes[1].coordinates
            corner3 = contour_nodes[2].coordinates
            corner4 = contour_nodes[3].coordinates
            # Check the angle at corner 1 and if it doesnt comply, set the internal angle error to true
            vector1 = fem_vector_2_points(corner1, corner2)
            vector2 = fem_vector_2_points(corner1, corner4)
            if fem_angle_between_2_vectors(vector1, vector2, degrees=True) <= minimum_internal_angle or \
                    fem_angle_between_2_vectors(vector1, vector2, degrees=True) >= maximum_internal_angle:
                internal_angle_error = True
            # Check the angle at corner 2 and if it doesnt comply, set the internal angle error to true
            vector1 = fem_vector_2_points(corner2, corner3)
            vector2 = fem_vector_2_points(corner2, corner1)
            if fem_angle_between_2_vectors(vector1, vector2, degrees=True) <= minimum_internal_angle or \
                    fem_angle_between_2_vectors(vector1, vector2, degrees=True) >= maximum_internal_angle:
                internal_angle_error = True
            # Check the angle at corner 3 and if it doesnt comply, set the internal angle error to true
            vector1 = fem_vector_2_points(corner3, corner2)
            vector2 = fem_vector_2_points(corner3, corner4)
            if fem_angle_between_2_vectors(vector1, vector2, degrees=True) <= minimum_internal_angle or \
                    fem_angle_between_2_vectors(vector1, vector2, degrees=True) >= maximum_internal_angle:
                internal_angle_error = True
            # Check the angle at corner 4 and if it doesnt comply, set the internal angle error to true
            vector1 = fem_vector_2_points(corner4, corner3)
            vector2 = fem_vector_2_points(corner4, corner1)
            if fem_angle_between_2_vectors(vector1, vector2, degrees=True) <= minimum_internal_angle or \
                    fem_angle_between_2_vectors(vector1, vector2, degrees=True) >= maximum_internal_angle:
                internal_angle_error = True
            # if the internal angle error is true, create a new node at the centre of the shape and split the shape
            # into 4 triangles to break up the shape and half the internal angles
            if internal_angle_error is True:
                centre_coord_of_shape = shape_for_angle_check.contour.get_centroid()
                new_centre_node = project.create_node(coordinates=centre_coord_of_shape)
                shape_for_angle_check.add_internal_point(new_centre_node)
                fem_mesh_suitability_checker(project, triangle_mesh_allowed=True)

### ===================================================================================================================
###   5. End of script
### ===================================================================================================================
