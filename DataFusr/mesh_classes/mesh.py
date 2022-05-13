### ===================================================================================================================
###   CLASS: Mesh
### ===================================================================================================================

### ===================================================================================================================
###   1. Import modules
### ===================================================================================================================

# Import general functions
from typing import List, Dict, Any

# References for functions and classes in the rhdhv_fem package
from rhdhv_fem.mesh.mesh_element import MeshElement
from rhdhv_fem.fem_tools import fem_unique_id_generator
from rhdhv_fem.client.fem_parser import RhdhvFemParser
from rhdhv_fem.fem_math import fem_unit_vector, fem_compare_coordinates, fem_point_in_surface
from rhdhv_fem.fem_config import Config

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
    plt = None


### ===================================================================================================================
###   2. Mesh class
### ===================================================================================================================

@RhdhvFemParser(category='Meshing')
class Mesh:
    """
    This is the class of the mesh objects in the fem-model.
    """
    def __init__(self, elements: List[MeshElement]):
        """
        Input:
            - elements (list of obj): List of instances of MeshElement class that contain the information of the mesh of
              the shape.
        """
        # When the instance of Mesh class is initialised, the project is set to None
        self.project = None

        # Set unique ID for the mesh object
        self.unique_id = fem_unique_id_generator()

        # Set the element dictionary
        self.elements = elements

    def __repr__(self):
        ids_string = ''
        last_element = None
        start_element = None
        ids = self.get_meshelement_ids()
        for i, element in enumerate(ids):
            if i == 0:
                start_element = element
                last_element = element
                ids_string += str(element)
            else:
                if element != last_element + 1:
                    if start_element != last_element:
                        ids_string += '-' + str(last_element)
                    else:
                        ids_string += ', ' + str(element)
                    start_element = element
                last_element = element
                if i == len(ids) - 1:
                    ids_string += '-' + str(element)
        return f"RHDHV-Mesh: {ids_string}"

    @property
    def elements(self):
        return self.__elements

    @elements.setter
    def elements(self, new_elements_list):
        if type(new_elements_list) != list:
            raise ValueError(
                f"ERROR: The mesh requires a list for the elements input argument, provided: {new_elements_list}.")
        for item in new_elements_list:
            if not isinstance(item, MeshElement):
                raise ValueError(
                    f"ERROR: The meshe requires a list of mesh elements for the elements input argument, one of "
                    f"the items ({item}) provided is of {item.__class__.__name__}")
        self.__elements = new_elements_list

    def get_meshelement_ids(self):
        """ This method of 'Mesh' is used to return a list of the IDs of the mesh-elements related to the shape."""
        return sorted([element.id for element in self.elements])

    def get_meshnode_ids(self):
        """ This method of 'Mesh' is used to return a list of the IDs of the mesh-nodes related to the shape."""
        nodes = list()
        for element in self.elements:
            for node in element.get_meshnode_ids():
                nodes.append(node)
        return sorted(list(set(nodes)))

    def get_meshnodes(self):
        """ This method of 'Mesh' returns a list of the MeshNode objects related to the shape."""
        nodes = list()
        for element in self.elements:
            for node in element.node_list:
                if node not in nodes:
                    nodes.append(node)
        return nodes

    def get_points(self):
        """ This method of 'Mesh' returns a list of all the points of the mesh."""
        return [node.coordinates for node in self.get_meshnodes()]

    def get_shape(self):
        """ This method of 'Mesh' returns the shape to which this mesh is assigned."""
        if self.project:
            for shape in self.project.collections.shapes:
                if self == shape.mesh:
                    return shape
        return None

    def get_connection(self):
        """ This method of 'Mesh' returns the connection to which this mesh is assigned."""
        if self.project:
            for connection in self.project.collections.connections:
                if hasattr(connection, 'mesh') and self == connection.mesh:
                    return connection
        return None

    def get_host(self):
        """ This method of 'Mesh' returns the host to which this mesh is assigned."""
        host = self.get_shape()
        if host is None:
            host = self.get_connection()
        return host

    def remove_mesh(self) -> bool:
        """ Method of 'Mesh' to remove the mesh. Mesh-elements and unused mesh-nodes are removed."""
        # If the object is not part of the project, is can't be removed
        if not self.project:
            return False

        # Remove elements
        for element in self.elements:
            element.remove_meshelement()

        # Remove mesh object from all collections in project
        if self.project:
            self.project.remove(self)

        # Remove the object
        del self
        return True

    def draw(self):
        # Check availability of matplotlib module
        if not matplot_use:
            self.project.write_log("ERROR: Mesh method draw requires third party matplotlib module.")
            return

        # Function is not to be used in DIANA
        if self.project.rhdhvDIANA.run_diana:
            self.project.write_log("WARNING: Mesh method drawck cannot be used in DIANA.")
            return

        # Collects the coordinates in lists
        x, y, z = [], [], []
        for element in self.elements:
            for node in element.point_list:
                x.append(node.coordinates[0])
                y.append(node.coordinates[1])
                z.append(node.coordinates[2])

        # Create 3D plot for meshnodes
        matplotlib.use(Config.MPL_GUI)
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(x, y, z)
        plt.show()

    def convert_mesh_to_line(self):
        """
        Method of 'Mesh' to collect the points on the contours of the mesh. This can be used to generate a shape
        geometry from the mesh. It expects straight line shaped elements. The function will find the start and end
        point. This function could be extended for nodes on arc shaped lines.

        .. warning: Method will not recognise arced lines.

        Input:
            - No input required.

        Output:
            - Returns a list with the start and end point of the line of the mesh.
        """
        # Collect all mesh-nodes, but remove doubles
        nodes = []
        for element in self.elements:
            if element.node_list[0] not in nodes:
                nodes.append(element.node_list[0])
            else:
                nodes.remove(element.node_list[0])
            if element.node_list[-1] not in nodes:
                nodes.append(element.node_list[-1])
            else:
                nodes.remove(element.node_list[-1])
        return [node.coordinates for node in nodes]

    def convert_mesh_to_plate(self):
        """
        Method of 'Mesh' to collect the points on the contours of the mesh. This can be used to generate a shape
        geometry from the mesh. It expects elements with more then 2 nodes, it finds then the edges of the elements that
        are not shared with other elements. The next step is to find the nodes that are on the same polyline. Then the
        in between nodes are eliminated if the direction of the line segment from the previous node is equal to that
        of the next line segment. This could be extended for nodes on arc shaped edges.

        .. warning:: Method will not recognise arced edges.

        Input:
            - No input required.

        Output:
            - Returns a list with the different contours of the mesh. The first contour is the outer contour.
        """
        # Create dictionary with all nodes
        nodes_dict = {}
        for element in self.elements:
            for node in element.node_list:
                if node.id not in nodes_dict:
                    nodes_dict[node.id] = node

        # Create a list with all the lines between nodes on the outer line of the mesh (or opening)
        # For performance the list is created using the IDs
        lines = list()
        for element in self.elements:
            if len(element.node_list) < 3:
                raise ValueError(
                    "ERROR: Method to convert mesh to plate does not accept elements with only 2 nodes. "
                    "Please check if this mesh is not for a beam shape.")
            for i in range(len(element.node_list)):
                if i == len(element.node_list) - 1:
                    line = [element.node_list[i].id, element.node_list[0].id]
                    inverted_line = [element.node_list[0].id, element.node_list[i].id]
                else:
                    line = [element.node_list[i].id, element.node_list[i+1].id]
                    inverted_line = [element.node_list[i+1].id, element.node_list[i].id]
                if line not in lines and inverted_line not in lines:
                    lines.append(line)
                else:
                    if line in lines:
                        lines.remove(line)
                    elif inverted_line in lines:
                        lines.remove(inverted_line)
                    else:
                        raise ValueError('ERROR: Something went wrong.')

        # Convert to lines with mesh-nodes
        lines = [[nodes_dict[line[0]], nodes_dict[line[1]]] for line in lines]

        # Find the different polylines
        current_node = lines[0][0]
        start_node = current_node
        polylines = list()
        polyline = [current_node]
        while len(lines) != 0:
            for line in lines:
                if current_node in line:
                    if line[0] is current_node:
                        polyline.append(line[1])
                        current_node = line[1]
                    else:
                        polyline.append(line[0])
                        current_node = line[0]
                    lines.remove(line)
                    break
            if current_node is start_node:
                del polyline[-1]
                polylines.append(polyline)
                if len(lines) != 0:
                    current_node = lines[0][0]
                    start_node = current_node
                    polyline = [current_node]

        # Filter the polylines for continuous lines
        filtered_polylines = list()
        for polyline in polylines:
            filtered_polyline = list()
            for i in range(len(polyline)):
                if i == 0:
                    node1 = polyline[-1]
                    node2 = polyline[i]
                    node3 = polyline[1]
                elif i == len(polyline) - 1:
                    node1 = polyline[i-1]
                    node2 = polyline[i]
                    node3 = polyline[0]
                else:
                    node1 = polyline[i-1]
                    node2 = polyline[i]
                    node3 = polyline[i+1]
                direction1 = fem_unit_vector(
                    [node2.coordinates[j] - node1.coordinates[j] for j in range(3)])
                direction2 = fem_unit_vector(
                    [node3.coordinates[j] - node2.coordinates[j] for j in range(3)])
                if not fem_compare_coordinates(direction1, direction2):
                    filtered_polyline.append(node2)
            filtered_polylines.append([node.coordinates for node in filtered_polyline])

        # Find the outer contour and place that one in the first position
        outer_polyline = filtered_polylines[0]
        for i in range(1, len(filtered_polylines)):
            if fem_point_in_surface(point=outer_polyline[0], surface=filtered_polylines[i]):
                outer_polyline = filtered_polylines[i]
        filtered_polylines.remove(outer_polyline)
        filtered_polylines.insert(0, outer_polyline)

        return filtered_polylines

    def to_diana(self):
        pass

    @staticmethod
    def from_diana(project: 'Project', data_dict: Dict[str, Any]):
        """ Static method of 'Mesh' class to convert input from DIANA dat-file to FEM object."""
        return project.create_mesh(elements=data_dict['elements'])

    @staticmethod
    def from_karamba(project: 'Project', kwargs):
        """ Static method of 'Mesh' class to convert input from KARAMBA json-file to FEM object."""
        return project.create_mesh(**kwargs)

### ===================================================================================================================
###   3. End of script
### ===================================================================================================================
