### ===================================================================================================================
###   CLASS: MeshElement
### ===================================================================================================================

### ===================================================================================================================
###   1. Import modules
### ===================================================================================================================

# Import general functions
from typing import List, Dict, Any

# References for functions and classes in the rhdhv_fem package
from rhdhv_fem.mesh.mesh_node import MeshNode
from rhdhv_fem.client.fem_parser import RhdhvFemParser
from rhdhv_fem.fem_tools import fem_unique_id_generator


### ===================================================================================================================
###   2. MeshElement class
### ===================================================================================================================

@RhdhvFemParser(category='Meshing')
class MeshElement:
    """
    The 'MeshElement' class contains all the elements for the mesh of the fem-model. MeshElements are defined as
    an ordered list of the mesh nodes.
    """
    def __init__(self, node_list: List[MeshNode], id: int):
        """
        Input:
            - point_list (list of obj): List of meshnodes that define the element. The list is an ordered list.
            - id (int): ID for the meshelement as positive integer (> 0), no further checks performed.
        """
        # When the instance of MeshElement class is initialised, the project is set to None
        self.project = None

        # Set unique ID for the mesh-element
        self.unique_id = fem_unique_id_generator()

        # Set attribute containing the list with meshnodes
        # See property methods
        self.node_list = node_list

        # Set the mesh element ID
        # See property methods
        self.id = id

    def __repr__(self):
        return f"RHDHV-MeshElement: {self.id}: {self.get_meshnode_ids()}"

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
                f"ERROR: The meshelement requires an integer for id input argument, provided: {new_id}.")
        if new_id < 1:
            raise ValueError(
                f"ERROR: The meshelement requires a positive integer, minimum 1 for id input argument, provided: "
                f"{new_id}.")
        self.__id = new_id

    @property
    def node_list(self):
        return self.__node_list

    @node_list.setter
    def node_list(self, new_node_list):
        if type(new_node_list) != list:
            raise ValueError(
                f"ERROR: The meshelement requires a list for the node_list input argument, provided: {new_node_list}.")
        for item in new_node_list:
            if not isinstance(item, MeshNode):
                raise ValueError(
                    f"ERROR: The meshelement requires a list of mesh nodes for the node_list input argument, one of "
                    f"the items ({item}) provided is of {item.__class__.__name__}")
        self.__node_list = new_node_list

    def get_meshnode_ids(self):
        """ This method of 'MeshElement' is used to return a list of the IDs of the nodes related to the element."""
        return sorted([node.id for node in self.node_list])

    def remove_meshelement(self) -> bool:
        """ Method of 'MeshElement' to remove the mesh-element. Unused mesh-nodes are removed."""
        # If the object is not part of the project, is can't be removed
        if not self.project:
            return False

        # Remove mesh object from all collections in project
        if self.project:
            self.project.remove(self)

        # Remove nodes
        for node in self.node_list:
            node.remove_meshnode()

        # Remove the object
        del self
        return True

    def to_diana(self):
        pass

    def get_mesh(self):
        """ This method of 'MeshElement' is used to return the mesh of the mesh element."""
        if self.project is not None:
            for mesh in self.project.collections.meshes:
                if self in mesh.elements:
                    return mesh
        return None

    def get_host(self):
        """ This method of 'MeshElement' is used to return the host of the mesh element, like a shape or connection."""
        mesh = self.get_mesh()
        if mesh is not None:
            return mesh.get_host()
        return None

    @staticmethod
    def from_diana(project, data_dict: Dict[str, Any]):
        """ Static method of 'MeshElement' class to convert input from DIANA dat-file to FEM object."""
        # Assumes that the item added is unique (for improved performance)
        meshelement = MeshElement(node_list=data_dict['nodes'], id=data_dict['id'])
        project.collections.mesh_elements.append(meshelement)
        meshelement.project = project
        return meshelement

    @staticmethod
    def from_karamba(project: 'Project', kwargs):
        """ Static method of 'MeshElement' class to convert input from KARAMBA json-file to FEM object."""
        return project.create_meshelement(**kwargs)

    @staticmethod
    def from_staad(input_dict, project: 'Project'):
        """ Static method of 'MeshElement' class to convert input from STAAD to FEM object."""
        return project.add(MeshElement(node_list=input_dict['node_list'], id=input_dict['id']))

### ===================================================================================================================
###   3. End of script
### ===================================================================================================================
