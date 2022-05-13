### ===================================================================================================================
###   CLASS: MeshNode
### ===================================================================================================================

### ===================================================================================================================
###   1. Import modules
### ===================================================================================================================

# Import general functions
from typing import List, Dict, Any

# References for functions and classes in the rhdhv_fem package
from rhdhv_fem.client.fem_parser import RhdhvFemParser
from rhdhv_fem.fem_math import fem_compare_coordinates
from rhdhv_fem.fem_tools import fem_unique_id_generator


### ===================================================================================================================
###   2. MeshNode class
### ===================================================================================================================

@RhdhvFemParser(category='Meshing')
class MeshNode:
    """
    The 'MeshNode' class contains all the nodes for the mesh of the model. MeshNodes are defined in x-, y- and
    z-direction.
    """
    def __init__(self, coordinates: List[float], id: int):
        """
        Input:
            - coordinates (list of 3 floats): x-, y- and z-coordinate of the node.
            - id (int): ID for the meshnode as positive integer (> 0), no further checks performed.
        """
        # When the instance of Support class is initialised, the project is set to None
        self.project = None

        # Set unique ID for the mesh-node
        self.unique_id = fem_unique_id_generator()

        # Set attribute containing the coordinates of the node in x-, y- and z-direction. Format: [x, y, z]
        # See property methods
        self.coordinates = coordinates

        # Set the mesh node ID
        # See property methods
        self.id = id

    def __repr__(self):
        return f"RHDHV-MeshNode: {self.id}: {self.coordinates}"

    def __hash__(self):
        return self.id

    @property
    def project(self):
        return self.__project

    @project.setter
    def project(self, new_project):
        self.__project = new_project

    @property
    def id(self):
        return self.__id

    @id.setter
    def id(self, new_id: int):
        if type(new_id) != int:
            raise ValueError(
                f"ERROR: The meshnode requires an integer for id input argument, provided: {new_id}.")
        if new_id < 1:
            raise ValueError(
                f"ERROR: The meshnode requires a positive integer, minimum 1 for id input argument, provided: "
                f"{new_id}.")
        self.__id = new_id

    @property
    def coordinates(self):
        return self.__coordinates

    @coordinates.setter
    def coordinates(self, new_coordinates):
        if not isinstance(new_coordinates, list):
            raise TypeError(
                f"ERROR: Meshnode input for coordinates of {self.__class__.__name__} must be a list.")
        for item in new_coordinates:
            if not isinstance(item, (float, int)):
                raise TypeError(
                    f"ERROR: Meshnode input for coordinates of {self.__class__.__name__} must be a list of coordinates "
                    f"as floats or integers, representing the coordinates in x-, y- and z-direction in [m].")
        if len(new_coordinates) == 2:
            new_coordinates.append(0)
        if len(new_coordinates) != 3:
            raise ValueError(
                f"ERROR: Meshnode input for coordinates of {self.__class__.__name__} '{new_coordinates}' consists of "
                f"{len(new_coordinates)} coordinates, 3 should be provided (x, y and z coordinate in [m]).")
        self.__coordinates = new_coordinates

    def __eq__(self, other):
        """Overrides the default implementation"""
        if isinstance(other, MeshNode):
            return self.id == other.id and fem_compare_coordinates(self.coordinates, other.coordinates)
        return False

    @property
    def elements(self) -> List['MeshElement']:
        elements = []
        if self.project:
            for element in self.project.collections.mesh_elements:
                if self in element.node_list:
                    elements.append(element)
        return elements

    def compare(self, other):
        """
        Method of 'MeshNode' to compare two mesh nodes if they are equal. First check is if class matches,
        and then if the coordinates match. The precision for this check is set to default in config.

        .. note:: Precision of project check might be set different.
        """
        return (self.__class__ == other.__class__ and
                fem_compare_coordinates(self.coordinates, other.coordinates))

    def remove_meshnode(self) -> bool:
        """ Method of 'MeshNode' to remove the mesh-node. Only removed if no mesh-element is referencing this node."""
        # If the object is not part of the project, it can't be removed
        if not self.project:
            return False

        # Check if node is referenced by any element
        if len(self.elements) > 0:
            return False

        # Remove mesh object from all collections in project
        if self.project:
            self.project.remove(self)

        # Remove the object
        del self
        return True

    def to_diana(self):
        pass

    def to_staad(self):
        return '%i %.3f %.3f %.3f;' % (self.id, self.coordinates[0], self.coordinates[1], self.coordinates[2])

    @staticmethod
    def from_diana(project, data_dict: Dict[str, Any]):
        """ Static method of 'MeshNode' class to convert input from DIANA dat-file to FEM object."""
        return project.create_meshnode(
            coordinates=data_dict['coordinates'], node_id=data_dict['id'], check_duplicate=False)

    @staticmethod
    def from_karamba(project: 'Project', kwargs):
        """ Static method of 'MeshNode' class to convert input from KARAMBA json-file to FEM object."""
        return project.create_meshnode(**kwargs)

    @staticmethod
    def from_staad(input_dict, project: 'Project'):
        """ Static method of 'MeshNode' class to convert input from STAAD to FEM object."""
        return project.add(MeshNode(coordinates=input_dict['coordinates'], id=input_dict['id']))

### ===================================================================================================================
###   3. End of script
### ===================================================================================================================
