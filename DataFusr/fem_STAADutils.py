### =============================================================================================================== ###
###                                                                                                                 ###
###                                                fem_STAADutils.py                                                ###
###                                                                                                                 ###
### =============================================================================================================== ###
# The module ``STAADutils`` contains the functions to create the model to convert models from FEM to STAAD and from
# STAAD to FEM. The conversion is based on the std-file format.
# Units are in m, N, rads and kg

# This version is applicable for modelling in Staad.Pro Connection Edition.

### ===================================================================================================================
###   Contents script
### ===================================================================================================================

#   1. Import modules

#   2. Helper functions for STAAD-client

#   3. Convert FEM to STAAD

#   4. Convert STAAD to FEM

#   5. Run analysis in STAAD

#   6. Get results from STAAD

#   7. End of script

### ===================================================================================================================
###   1. Import modules
### ===================================================================================================================

import copy
import os
import re
import math
# Import general functions
import subprocess
import time
from datetime import date
from pathlib import Path
from typing import Union, List, Optional

from rhdhv_fem.output_items import ForceOutputItem, DisplacementOutputItem, ElementForceOutputItem
# References for functions and classes in the rhdhv_fem package
from rhdhv_fem.fem_tools import fem_create_folder, fem_write_log, fem_read_file
from rhdhv_fem.geometries import SurfaceGeometryModel, ProfileGeometryModel, ArbitraryPolygonProfile
from rhdhv_fem.shape_geometries import Polyline, Line

# Module usef for retrieving results from STAAD API
try:
    import comtypes
    import comtypes.client
    import comtypes.automation
    import ctypes

    comtypes_use = True
except ImportError:
    comtypes = None
    ctypes = None
    comtypes_use = False


### ===================================================================================================================
###   2. Helper functions for STAAD-client
### ===================================================================================================================

def _check_row_length(project: 'Project', string_list: List[str]):
    """
    This function sorts the list of joints, elements and members and combines them to rows with a maximum length, set
    in the project-constants for STAAD.

    Input:
        - project: Project object containing collections of fem objects an project variables.
        - string_list (list): List of strings, starting with the number of the joint, member or element and separated
          with a space.

    Output:
        - Returns list with a condesed and sorted list with the joints, members or elements.
    """
    # Numbering the elements in order
    ref_strings = {}
    for item in string_list:
        ref_strings[int(item.split(' ')[0])] = item
    string_list = list()
    for key in sorted(ref_strings.keys()):
        string_list.append(ref_strings[key])

    # Filling lines to maximum length
    output_list = ['']
    row = 0
    for i, string in enumerate(string_list):
        if len(output_list[row]) + len(string) > project.staad_settings.staad_column_limit:
            row += 1
            output_list.append(string)
        elif i == 0:
            output_list[row] += string
        else:
            output_list[row] += ' ' + string
    return output_list


def _fem_assign_material_staad(project: 'Project'):
    """
    This function is the script that to assign material to the elements for STAAD Model.

    Input:
        - project: Project object containing collections of fem objects an project variables.

    Output:
        - The std-file containing the Staad project is generated.
        - a list containing texts to std file
    """
    lst = list()
    lst.append('CONSTANTS')
    for material in project.collections.materials:
        shapes = material.get_shapes()
        shapes.sort(key=lambda x: x.id, reverse=False)
        for obj in shapes:
            if len(obj.mesh.elements) == 1:
                lst.append('MATERIAL %s MEMB %d' % (material.name, obj.mesh.elements[0].id))
            else:
                lst.append('MATERIAL %s MEMB %d TO %d' % (material.name, obj.mesh.elements[0].id,
                                                          obj.mesh.elements[-1].id))
    return lst


def beta_angle_to_staad(project: 'Project'):
    """
        This function is the script that assigns the appropriate beta angle to the element in STAAD dependent on the
        z axis defined by the user.

        Input:
            - project: Project object containing collections of fem objects an project variables.

        Output:
            - The std-file containing the Staad project is generated.
            - a list containing texts to std file
        """
    lst = list()
    beta_dict = {}

    # Determine the local z axis of the member, ID and to check its direction is in a global direction
    for line in project.collections.lines:
        local_z_axis = line.element_z_axis.vector
        member_no = line.mesh.elements[0].id
        vector = line.contour.get_direction()
        if vector.count(0) != 2:
            project.write_log('WARNING: member is not spanning in global axis, this feature has not been incorporated '
                              'yet and therefore no beta angle will be applied')
            continue
        else:
            if vector[0] > 0:
                member_direction = '+X'
            elif vector[0] < 0:
                member_direction = '-X'
            elif vector[1] > 0:
                member_direction = '+Y'
            elif vector[1] < 0:
                member_direction = '-Y'
            elif vector[2] > 0:
                member_direction = '+Z'
            elif vector[2] < 0:
                member_direction = '-Z'

        # If the member is in a global direction, determines the necessary beta angle and string to input into STAAD
        beta_text = None
        if member_direction == '+Z':
            if local_z_axis[0] > 0:
                beta_text = 'BETA 180 MEMB '
            elif local_z_axis[0] < 0:
                beta_text = None
            elif local_z_axis[1] > 0:
                beta_text = 'BETA 270 MEMB '
            elif local_z_axis[1] < 0:
                beta_text = 'BETA 90 MEMB '
        elif member_direction == '-Z':
            if local_z_axis[0] > 0:
                beta_text = None
            elif local_z_axis[0] < 0:
                beta_text = 'BETA 180 MEMB '
            elif local_z_axis[1] > 0:
                beta_text = 'BETA 270 MEMB '
            elif local_z_axis[1] < 0:
                beta_text = 'BETA 90 MEMB '
        elif member_direction == '+Y':
            if local_z_axis[2] > 0:
                beta_text = None
            elif local_z_axis[2] < 0:
                beta_text = 'BETA 180 MEMB '
            elif local_z_axis[0] < 0:
                beta_text = 'BETA 270 MEMB '
            elif local_z_axis[0] > 0:
                beta_text = 'BETA 90 MEMB '
        elif member_direction == '-Y':
            if local_z_axis[2] > 0:
                beta_text = None
            elif local_z_axis[2] < 0:
                beta_text = 'BETA 180 MEMB '
            elif local_z_axis[0] < 0:
                beta_text = 'BETA 90 MEMB '
            elif local_z_axis[0] > 0:
                beta_text = 'BETA 270 MEMB '
        elif member_direction == '+X':
            if local_z_axis[2] > 0:
                beta_text = None
            elif local_z_axis[2] < 0:
                beta_text = 'BETA 180 MEMB '
            elif local_z_axis[1] > 0:
                beta_text = 'BETA 270 MEMB '
            elif local_z_axis[1] < 0:
                beta_text = 'BETA 90 MEMB '
        elif member_direction == '-X':
            if local_z_axis[2] < 0:
                beta_text = None
            elif local_z_axis[2] > 0:
                beta_text = 'BETA 180 MEMB '
            elif local_z_axis[1] > 0:
                beta_text = 'BETA 270 MEMB '
            elif local_z_axis[1] < 0:
                beta_text = 'BETA 90 MEMB '

        # if there is a beta angle to be applied to the member, this is added to the dictionary
        if beta_text is not None:
            beta_dict[member_no] = beta_text

    # output list is created with all the lines to be printed to staad formed of member id and relevant beta angle
    for key, value in beta_dict.items():
        lst.append(str(value) + str(key))

    return lst


def offsets_to_staad(project: 'Project'):
    """
    This function is the script that assigns the appropriate offset to the element in STAAD dependent on the
    eccentricity defined by the user to that member

    Input:
        - project: Project object containing collections of fem objects an project variables.

    Output:
        - The std-file containing the Staad project is generated.
        - a list containing texts to std file
    """
    lst = list()

    for line in project.collections.lines:
        # if eccentricity has been applied, eccentricity attribute has been defined
        if isinstance(line.eccentricities, dict) and \
                any(eccentricity != 0 for eccentricity in line.eccentricities.values()):
            # determine beam id that will be reported in staad
            member_no = line.mesh.elements[0].id
            # obtain offset values
            list_of_vectors = list(line.eccentricities.values())
            # Append the offset at the start and end of the member to the output list
            lst.append(f'{member_no} START {list_of_vectors[0]} {list_of_vectors[1]} {list_of_vectors[2]}')
            lst.append(f'{member_no} END {list_of_vectors[0]} {list_of_vectors[1]} {list_of_vectors[2]}')

    return lst


def _check_duplicate_entries(string_list: List[str], position: Optional[int] = 0):
    """
    Input:
        - string_list (list of strings): List of strings that are to be written to STAAD for a specific feature.
          feature example is beta angles, offsets, properties etc.
        - position : must be int 0 or -1, default value is 0. 0 means that the list of members come before the property,
          node or plate ids. - 1 means member ids come first then the feature is written after. For example:
          '1 , 2, 3, 5 BETA 90' means the position is 0 as 'BETA 90' is at the end.

    Output:
        - Returns a comprehensive, compressed list so that for example 1, 2, 3, 4, 5 was 1 TO 5 and therefore far more
          readable. In addition, it will ensure that the string does not become unreadable by STAAD Editor. What it will
          do is determine the max character limit of a line for STAAD, split it at the nearest space and instead insert
          '-'.
    """
    data = dict()

    for list_of_shapes in string_list:
        # determine the 'feature' which is effectively the feature text based on the position defined
        if position == 0:
            feature = ' '.join(list_of_shapes.split()[1:])
        else:
            feature = ' '.join(list_of_shapes.split()[:-1])
        # obtain members
        memb = list_of_shapes.split()[position]

        # add feature to data dictionary and if it is already present, add the member to the list of members with that
        # feature
        if not (feature in data):
            data[feature] = [int(memb)]
        else:
            data[feature].append(int(memb))

    # list to be returned
    out_list = []

    for feature, memb in data.items():
        # members are sorted in terms of their ID
        member = sorted(memb)
        # obtain numnber of members
        lmb = len(member)
        list_of_shapes = ''
        # tidies the list of members so for example 1, 2, 3, 4, 10 becomes 1 TO 4, 10
        for i in range(lmb):
            if list_of_shapes == '':
                list_of_shapes += str(member[i])
            elif (i == lmb - 1) and (member[i] == member[i - 1] + 1):
                list_of_shapes += ' TO ' + str(member[i])
            elif i == lmb - 1:
                list_of_shapes += ' ' + str(member[i])
            elif (i < lmb - 1) and (member[i] == member[i - 1] + 1) and (member[i] + 1 != member[i + 1]):
                list_of_shapes += ' TO ' + str(member[i])
            elif (i < lmb - 1) and (member[i] != member[i - 1] + 1):
                list_of_shapes += ' ' + str(member[i])

        # reassign the tidied list of members to the 'feature'
        data[feature] = list_of_shapes

        if 'SPRINGS' in feature:
            # Multi linear springs work in a unique way and therefore at this point of the code this flip needs to
            # occur
            original_feature = feature
            original_list_of_shapes = list_of_shapes
            list_of_shapes = original_feature
            feature = original_list_of_shapes
            position = -1

        split_string = []
        # initial check to see if a sentance formed of the list of members and the feature string is greater than 78
        # 78 is the max character length in STAAD
        if (len(list_of_shapes) + len(feature)) > 78:
            counter = 0
            # if position is -1 that means the the 78 character limit must take into account this and also 2 spaces for
            # ' -' at the end of the line which is a requirement in STAAD. If position is 0, allowance of 2 spaces only
            # is required for ' -'
            if position == -1:
                n = 78 - len(feature) - 2
            else:
                n = 78 - 2
            string_to_breakdown = list_of_shapes
            # while the length of the string to be written is more than n (the allowable character length) follow the
            # loop below
            while len(string_to_breakdown) > n:
                # determine the portion of the full sentance that can fit
                str_in_range = string_to_breakdown[0:n]
                # anything left of the original string is kept aside
                leftover = string_to_breakdown[n:]
                # reverse the string that can fit on the line to be written
                reverse_string = str_in_range[::-1]
                # determine in the reversed string where the first space is which is effectively the last space in the
                # string when it is in the correct order to determine where you want to split the original string
                location_of_split_in_rvrse = reverse_string.index(' ')
                # determine the location of the split in the non reversed string
                location_of_split = len(str_in_range) - location_of_split_in_rvrse
                # the line to be written is determined
                string_to_write = str_in_range[0:location_of_split] + '-'
                # if it is the first line being written and the position is -1 then the feature is written first
                if counter == 0 and position == -1:
                    split_string.append(feature + ' ' + string_to_write)
                # otherwise write normal line
                else:
                    split_string.append(string_to_write)
                string_to_breakdown = str_in_range[location_of_split:] + leftover
                # n increased/kept to 76 and counter upped as no longer first sentance. n is increased if
                # feature is at the start
                n = 78 - 2
                counter = 1
            if position == 0:
                # if position of the feature is at the end then determine if its the final line. If it is write feature,
                # if it is not the final line and one more line needs to be written. Write the member ids and then ' -'
                # before starting a new line to write the rest
                if len(string_to_breakdown) + len(feature) > 78:
                    split_string.append(string_to_breakdown + ' -')
                    split_string.append(feature)
                else:
                    split_string.append(string_to_breakdown + ' ' + feature)
            else:
                # if position is -1 then no need to worry about the feature and write the final line
                split_string.append(string_to_breakdown)
            out_list.extend(split_string)

        else:
            # if total line is not longer than 78 characters do the following based on the position
            if position == 0:
                out_list.append(list_of_shapes + ' ' + feature)
            else:
                out_list.append(feature + ' ' + list_of_shapes)

    return out_list


def check_length_of_line(string_to_check: str):
    '''
    Input:
        - line to check (string): line in which the length needs to be checked and potentially be split to suit staads character
          limit

    Output:
        - Returns a list of strings that is split to account for the max character limit of a line for STAAD,
        split it at the nearest space and instead inserts '-'.
    '''

    # This is likely to overrun the staad max line count and therefore needs to be split
    split_string = []
    # initial check to see if a sentance formed of the list of members and the feature string is greater than 78
    # 78 is the max character length in STAAD
    if len(string_to_check) > 78:
        n = 78 - 2
        # while the length of the string to be written is more than n (the allowable character length) follow the
        # loop below
        string_to_breakdown = string_to_check
        while len(string_to_breakdown) > n:
            # determine the portion of the full sentance that can fit
            str_in_range = string_to_breakdown[0:n]
            # anything left of the original string is kept aside
            leftover = string_to_breakdown[n:]
            # reverse the string that can fit on the line to be written
            reverse_string = str_in_range[::-1]
            # determine in the reversed string where the first space is which is effectively the last space in the
            # string when it is in the correct order to determine where you want to split the original string
            location_of_split_in_rvrse = reverse_string.index(' ')
            # determine the location of the split in the non reversed string
            location_of_split = len(str_in_range) - location_of_split_in_rvrse
            # the line to be written is determined
            string_to_write = str_in_range[0:location_of_split] + '-'
            # otherwise write normal line
            split_string.append(string_to_write)
            string_to_breakdown = str_in_range[location_of_split:] + leftover
            # n increased/kept to 76 and counter upped as no longer first sentance. n is increased if
            # feature is at the start
        split_string.append(string_to_breakdown)
    else:
        split_string.append(string_to_check)
    return split_string


def fem_create_envelope_combination(project: 'Project'):
    """
    Input:
        - project (obj): Project object containing collections of fem objects an project variables.

    Output:
        - Returns comprehensed lists of envelope combination.
    """
    lst = list()
    data = dict()
    envelope_id = 0
    if len(project.collections.loadcombinations) != 0:
        for comb in project.collections.loadcombinations:
            if comb.category is None:
                pass
            elif comb.category in data:
                if comb.id > len(project.collections.loadcases) and comb.id > 99:
                    loadcombination_id = comb.id
                else:
                    loadcombination_id = max(len(project.collections.loadcases) + comb.id, 99 + comb.id)
                lst.append(f'{loadcombination_id} ENVELOPE {data[comb.category]}')
            else:
                if comb.id > len(project.collections.loadcases) and comb.id > 99:
                    loadcombination_id = comb.id
                else:
                    loadcombination_id = max(len(project.collections.loadcases) + comb.id, 99 + comb.id)
                envelope_id += 1
                data[str(comb.category)] = envelope_id
                lst.append(f'{loadcombination_id} ENVELOPE {data[comb.category]}')
    return _check_duplicate_entries(lst)


### ===================================================================================================================
###   3. Convert FEM to STAAD
### ===================================================================================================================

def _fem_create_model_staad(project: 'Project', folder: Union[Path, str] = None):
    """
    This function generates a std-file, the input file for STAAD.

    Input:
        - project: Project object containing collections of fem objects an project variables.

    Output:
        - Function creates the model by std file.
    """
    # import objects
    from rhdhv_fem.loads import LoadCombination

    # Select the subfolder
    if not folder:
        folder = Path.cwd()
    if type(folder) == str:
        folder = Path.cwd() / folder
    if not folder.exists():
        fem_create_folder(folder)
    std_filename = folder / str(project.name + '_STAAD.std')

    # Start list of strings to be written to inputfile for STAAD
    list_content = list()

    # Write Basic Information
    list_content.append('STAAD SPACE ' + project.name)
    list_content.append('START JOB INFORMATION')
    list_content.append('ENGINEER DATE ' + date.today().strftime('%d/%m/%Y'))
    list_content.append('ENGINEER NAME ' + project.project_information.get('author'))
    list_content.append('JOB PART ' + project.project_information.get('part'))
    list_content.append('END JOB INFORMATION')
    list_content.append('INPUT WIDTH 79')
    list_content.append('UNIT METER KN')
    list_content.append('SET Z UP')

    # Check all shapes are meshed
    for shape in project.collections.shapes:
        if isinstance(shape.contour, Polyline):
            if shape.mesh is None:
                shape.mesh_shape(1, 1)
        elif isinstance(shape.contour, Line):
            if shape.mesh is None:
                shape.mesh_shape(1)
        else:
            raise NotImplementedError(f"ERROR: {type(shape.contour)} is not supported by STAAD, only contour subclasses"
                                      f" which are supported are Polyline and Line currently.")

    # Write Joint Coordinates (MeshNodes)
    list_content.append('JOINT COORDINATES')
    list_joint_coordinates = []
    for meshnode in project.collections.mesh_nodes:
        list_joint_coordinates.append(meshnode.to_staad())
    list_content.extend(_check_row_length(project, list_joint_coordinates))

    # Write Member incidences (MeshElements of line_shape shapes)
    if len(project.collections.lines) > 0:
        list_content.append('MEMBER INCIDENCES')
        list_member_incidences = []
        for line_shape in project.collections.lines:
            list_member_incidences.extend(line_shape.to_staad())
        list_content.extend(_check_row_length(project, list_member_incidences))

    # Write Member incidences (MeshElements of line_shape shapes)
    if len(project.collections.surfaces) > 0:
        list_content.append('ELEMENT INCIDENCES SHELL')
        list_shell_incidences = []
        for surface_shape in project.collections.surfaces:
            list_shell_incidences.extend(surface_shape.to_staad())
        list_content.extend(_check_row_length(project, list_shell_incidences))

    # Write User tables
    user_table = False
    for geom in project.collections.geometry_models:
        if isinstance(geom, ArbitraryPolygonProfile):
            list_content.append('START USER TABLE')
            list_content.append('TABLE 1')
            list_content.append('GENERAL')
            user_table = True
            break
    for geom in project.collections.geometry_models:
        if isinstance(geom, ArbitraryPolygonProfile):
            section_data = geom.to_staad()
            for line_of_text in section_data:
                list_content.extend(check_length_of_line(line_of_text))
    if user_table is True:
        list_content.append('END')

    # Write Groups
    if len(project.collections.groups) > 0:
        list_content.append('START GROUP DEFINITION')
        joint_groups = []
        geometry_groups = []
        for group in project.collections.groups:
            group_dict = group.to_staad(project)
            if len(group_dict['JOINT']) > 0:
                for group_name, joint_list in group_dict['JOINT'].items():
                    for joint in joint_list:
                        joint_groups.append(f'_{group_name} {joint}')
            if len(group_dict['GEOMETRY']) > 0:
                for group_name, shape_list in group_dict['GEOMETRY'].items():
                    for shape in shape_list:
                        geometry_groups.append(f'_{group_name} {shape}')
        if len(joint_groups) > 0:
            list_content.append('JOINT')
            list_content.extend(_check_duplicate_entries(joint_groups, -1))
        if len(geometry_groups) > 0:
            list_content.append('GEOMETRY')
            list_content.extend(_check_duplicate_entries(geometry_groups, -1))
        list_content.append('END GROUP DEFINITION')

    # Write Element property
    for geom in project.collections.geometries:
        if isinstance(geom.geometry_model, SurfaceGeometryModel):
            list_content.append('ELEMENT PROPERTY')
            break
    for geom in project.collections.geometries:
        if isinstance(geom.geometry_model, SurfaceGeometryModel):
            list_content.append(geom.to_staad())

    # Write materials
    if len(project.collections.materials) > 0:
        list_content.append('DEFINE MATERIAL START')
        for material in project.collections.materials:
            list_content.extend(material.to_staad())
        list_content.append('END DEFINE MATERIAL')

    # Write beam section
    for geom in project.collections.geometries:
        if isinstance(geom.geometry_model, ProfileGeometryModel):
            list_content.append('MEMBER PROPERTY EUROPEAN')
            break
    for geom in project.collections.geometries:
        if isinstance(geom.geometry_model, ProfileGeometryModel):
            list_content.append(geom.to_staad())

    # Assign materials
    if len(project.collections.materials) > 0:
        list_content.append('CONSTANTS')
        list_content.extend(_check_duplicate_entries(beta_angle_to_staad(project), -1))
        list_content.extend(_check_duplicate_entries(project.assign_material_staad()[1:], -1))

    # Write support
    if len(project.collections.supports) > 0:
        list_content.append('SUPPORTS')
        list_support = []
        list_support_multilinear_spring = []
        for support in project.collections.supports:
            list_support.append(support.to_staad()[0])
            if len(support.to_staad()) == 2:
                list_support_multilinear_spring.append(support.to_staad()[1])
        list_content.extend(_check_duplicate_entries(list_support))
        if list_support_multilinear_spring:
            list_content.append('MULTILINEAR SPRINGS')
            list_content.extend(_check_duplicate_entries(list_support_multilinear_spring))

    # Write Offsets
    if len(offsets_to_staad(project)) > 0:
        list_content.append('MEMBER OFFSET')
        list_content.extend(_check_duplicate_entries(offsets_to_staad(project), 0))

    # Write hinge connection
    if len(project.collections.connections) > 0:
        list_content.append('MEMBER RELEASE')
        list_hinges = []
        for hinge in project.collections.connections:
            list_hinges.append(hinge.to_staad())
        list_content.extend(_check_duplicate_entries(list_hinges))

    # Write load cases
    for loadcase in project.collections.loadcases:
        list_content.extend(loadcase.to_staad())

    # Write repeat loads
    repeat_load_loadcase_counter = 0
    for loadcombination in project.collections.loadcombinations:
        if isinstance(loadcombination, LoadCombination) and loadcombination.non_linear_combination is \
                True:
            repeat_load_loadcase_counter += 1
            loadgroupname = 'None'
            temp_load_group = project.find(loadgroupname, 'loadgroups')
            if temp_load_group is None:
                temp_load_group = project.create_loadgroup(name=loadgroupname)
            if type(temp_load_group) is list:
                new_loadcase = project.create_loadcase(name=f'Repeat Load {repeat_load_loadcase_counter}',
                                                       loadgroup=temp_load_group[0])
            else:
                new_loadcase = project.create_loadcase(name=f'Repeat Load {repeat_load_loadcase_counter}',
                                                       loadgroup=temp_load_group)
            list_content.extend(new_loadcase.to_staad())
            list_content.append('REPEAT LOAD')
            list_content.extend(loadcombination.to_staad())

    # Write load combinations
    for loadcombination in project.collections.loadcombinations:
        if isinstance(loadcombination, LoadCombination) and loadcombination.non_linear_combination is not True:
            list_content.extend(loadcombination.to_staad())

    # Perform analysis
    list_content.append('PERFORM ANALYSIS')

    # Write envelope combinations
    list_envelope = fem_create_envelope_combination(project)
    if list_envelope:
        list_content.append('DEFINE ENVELOPE')
        list_content.extend(list_envelope)
        list_content.append('END DEFINE ENVELOPE')

    # End of file
    list_content.append('FINISH')

    # Write std-file
    with open(std_filename, 'w') as f:
        for item in list_content:
            f.write('%s\n' % item)

    # Notification of end of process
    if std_filename.exists():
        fem_write_log(project.logfile,
                      f"Inputfile for STAAD for fem-model created: {std_filename.as_posix()}", True)
        return std_filename
    else:
        fem_write_log(project.logfile, f"ERROR: Inputfile for model for STAAD could not be created.", True)
        return None


### ===================================================================================================================
###   4. Convert STAAD to FEM
### ===================================================================================================================

class RawStdFile:
    """
    This class contains a copy of the std-file (model file created by STAAD) in python.
    """

    def __init__(self, std_file: Path):
        """
        Input:
            - file (Path): Path of the STAAD input file.

        Output:
            - Object for dat-file reference is created.
            - Attribute dictionaries for the different items in the dat-file are initialised.
            - The DATfile object is added as reference in the 'Project' class.
        """
        # get data from std and collect them into list std_data
        self.file = std_file

        # Set the attributes containing parts of the model
        self.units = dict()  # default unit in staad is meter and kN
        self.direction = dict()  # default direction in staad is 'Y'
        self.joint_coordinates = dict()  # contains of node ID, cooordinates of nodes
        self.member_incidences = dict()  # contains of beam ID, start node ID, end node ID
        self.element_incidences_shell = dict()  # contains of plate ID, node ID
        self.materials = dict()  # contains of material names and parameters of materials
        self.member_properties = dict()  # section of frame element
        self.element_properties = dict()  # properties of plate or surface element
        self.supports = dict()  # collect type of support and node which assigned with supports
        self.constants = dict()  # contains of materials name and list of assigned members
        self.beta_angles = dict()  # contains beta angles and list of assigned members
        self.offsets = dict()  # contains mebers and their respective offsets that have been assigned
        self.primary_loadcases = dict()  # contains of loadcase name, loadcase ID, and load items inside itself
        self.load_combinations = dict()  # contains of load combinations
        self.envelopes = dict()  # contains of load envelope ID, and list of load combinations

        # Read std file
        self.read_file()


    def read_file(self):
        """ Sub-function to read the std file and collect the lines."""
        # Read the std file
        lines = fem_read_file(self.file, 'std')

        # Delete comment line and blank line
        refine_data = []
        i = 0
        while i < len(lines):
            if re.search("(\*)", lines[i]) or lines[i] == '':
                pass
                i += 1
            elif lines[i].split(" ")[0] == "*" or lines[i][0] == "*":
                pass
                i += 1
            elif lines[i - 1][-1:] == '-' and 'TITLE' not in lines[i - 1]:
                refine_data[-1] = refine_data[-1][:-1]
                if lines[i - 1][-2] == ' ':
                    extra = ''
                else:
                    extra = ' '
                refine_data[-1] = refine_data[-1] + extra + lines[i]
                i += 1
            elif lines[i -1][-2:] == '- ':
                refine_data[-1] = refine_data[-1][:-2]
                if lines[i -1][-3] == ' ':
                    extra = ''
                else:
                    extra = ' '
                refine_data[-1] = refine_data[-1] + extra + lines[i]
                i += 1
            else:
                refine_data.append(lines[i])
                i += 1

        # Execute method to get data from std file
        self.get_unit(refine_data)
        self.get_direction(refine_data)
        self.get_joint_coordinates(refine_data)
        self.get_member_incidences(refine_data)
        self.get_element_incidences_shell(refine_data)
        self.get_groups(refine_data)
        self.get_material(refine_data)
        self.get_member_properties(refine_data)
        self.get_constants(refine_data)
        self.get_beta_angles(refine_data)
        self.get_offsets(refine_data)
        self.get_supports(refine_data)
        self.get_element_properties(refine_data)
        self.get_primary_loadcases(refine_data)
        self.get_load_combinations(refine_data)
        self.get_envelopes(refine_data)

    def get_groups(self, std_data):
        """
        to obtain the groups within a staad file
        input: RAW Staad file data list
        :return: a dictionary of all staad groups. Grouped into nodes and shape groups
        """

        node_groups = {}
        shape_groups = {}

        i = 0
        while i < len(std_data):
            if std_data[i] == "START GROUP DEFINITION":
                i += 1
            elif std_data[i] == "END GROUP DEFINITION":
                break
            else:
                if std_data[i] == "JOINT":
                    # Get Node IDS
                    i += 1
                    while std_data[i][0] == '_':
                        group_name = std_data[i].split(" ")[0]
                        if group_name[0] == "_":
                            group_name = group_name[1:]
                        entries = self.detail_members(std_data[i].split(" ")[1:])
                        node_groups[f'{group_name}'] = entries
                        i += 1
                elif std_data[i] == "MEMBER":
                    # Get Member Groups
                    i += 1
                    while std_data[i][0] == '_':
                        group_name = std_data[i].split(" ")[0]
                        if group_name[0] == "_":
                            group_name = group_name[1:]
                        entries = self.detail_members(std_data[i].split(" ")[1:])
                        shape_groups[f'{group_name}'] = entries
                        i += 1
                elif std_data[i] == "ELEMENT":
                    # Get Element Groups
                    i += 1
                    while std_data[i][0] == '_':
                        group_name = std_data[i].split(" ")[0]
                        if group_name[0] == "_":
                            group_name = group_name[1:]
                        entries = self.detail_members(std_data[i].split(" ")[1:])
                        shape_groups[f'{group_name}'] = entries
                        i += 1
                elif std_data[i] == "FLOOR":
                    # Get Floor Groups
                    i += 1
                    while std_data[i][0] == '_':
                        group_name = std_data[i].split(" ")[0]
                        if group_name[0] == "_":
                            group_name = group_name[1:]
                        entries = self.detail_members(std_data[i].split(" ")[1:])
                        shape_groups[f'{group_name}'] = entries
                        i += 1
                elif std_data[i] == "GEOMETRY":
                    # Get Geometry Groups
                    i += 1
                    while std_data[i][0] == '_':
                        group_name = std_data[i].split(" ")[0]
                        if group_name[0] == "_":
                            group_name = group_name[1:]
                        entries = self.detail_members(std_data[i].split(" ")[1:])
                        shape_groups[f'{group_name}'] = entries
                        i += 1
                else:
                    i += 1
        self.groups = {}
        self.groups['node_groups'] = node_groups
        self.groups['shape_groups'] = shape_groups

    def detail_members(self, string_list: []):
        """
        to detail one bye one members ID
        :param string_list: is a list contains strings
        :return: a list comtains members ID
        """
        members = []
        for j in range(len(string_list)):
            if string_list[j] != 'TO':
                members.append(string_list[j])
            else:
                for k in range(int(string_list[j - 1]) + 1, int(string_list[j + 1])):
                    members.append(str(k))

        while ("" in members):
            members.remove("")

        return members

    def get_unit(self, std_data):
        """
        to get the unit using in STAAD model.
        :return: a string of unit ("kN", "N",...)
        """
        # defaut unit in staad model is 'kN' for forcce and "METER" for dimension
        unit_dimension = 'METER'
        unit_force = 'kN'
        convert_fator = 1000
        self.units['unit'] = {
            'unit_dimension': unit_dimension,
            'unit_force': unit_force,
            'convert_factor_force': 1000
        }

        i = 0
        while i < len(std_data):
            if len(re.findall("UNIT", std_data[i])) != 0:
                unit_dimension = std_data[i].split(" ")[1]
                unit_force = std_data[i].split(" ")[2]
                if unit_force == "KN":
                    convert_fator = 1000
                elif unit_force == "N":
                    convert_fator = 1
                else:
                    raise NotImplementedError("ERROR: Only kiloNewton or Newton force are implemented. "
                                              "Please check the unit of force in .std file again.")
                self.units['unit'] = {
                    'unit_dimension': unit_dimension,
                    'unit_force': unit_force,
                    'convert_factor_force': convert_fator
                }

            i += 1

    def get_direction(self, std_data):
        """
        Function to get the directon using in staad model (std file)
        :return: a string name of direction ('X', '-X', 'Y', '-Y', 'Z', '-Z')
        """
        # defaut value for direction
        name = "Y"
        self.direction['direction'] = name

        i = 0
        while i < len(std_data):
            if len(re.findall("SET . UP", std_data[i])) != 0:
                if std_data[i].split(" ")[0] != "*":
                    name = std_data[i].split(" ")[1]
                    self.direction['direction'] = name

            i += 1

    def get_joint_coordinates(self, std_data):
        id = None
        x = None
        y = None
        z = None
        i = 0
        while i < len(std_data):
            if std_data[i] == "JOINT COORDINATES":
                # blank line or comment line
                i += 1
                if std_data[i] == '' or std_data[i].split("*")[0] == '*':
                    i += 1

                while std_data[i].split(" ")[0].isnumeric() == True:
                    for text in std_data[i].split(";"):
                        if text != '':
                            if len(text.split(" ")) == 5:
                                id = text.split(" ")[1]
                                x = float(text.split(" ")[2])
                                y = float(text.split(" ")[3])
                                z = float(text.split(" ")[4])
                                self.joint_coordinates[id] = [x, y, z]
                            else:
                                id = text.split(" ")[0]
                                x = float(text.split(" ")[1])
                                y = float(text.split(" ")[2])
                                z = float(text.split(" ")[3])
                                self.joint_coordinates[id] = [x, y, z]
                    i += 1
            i += 1

    def get_member_incidences(self, std_data):
        """
        get member incidences in the std_data
        :return:
        """
        id = None
        start_node_id = None
        end_node_id = None
        i = 0
        while i < len(std_data):
            if std_data[i] == "MEMBER INCIDENCES":
                # blank line or comment line
                i += 1
                if std_data[i] == '' or std_data[i].split("*")[0] == '*':
                    i += 1
                # find data
                while std_data[i].split(" ")[0].isnumeric() == True:
                    for text in std_data[i].split(";"):
                        if text != '':
                            if len(text.split(" ")) == 4:
                                id = text.split(" ")[1]
                                start_node_id = text.split(" ")[2]
                                end_node_id = text.split(" ")[3]
                                self.member_incidences[id] = {
                                    'start_node': self.joint_coordinates[start_node_id],
                                    'end_node': self.joint_coordinates[end_node_id],
                                    'start_node_ID': start_node_id,
                                    'end_node_ID': end_node_id
                                }
                            else:
                                id = text.split(" ")[0]
                                start_node_id = text.split(" ")[1]
                                end_node_id = text.split(" ")[2]
                                self.member_incidences[id] = {
                                    'start_node': self.joint_coordinates[start_node_id],
                                    'end_node': self.joint_coordinates[end_node_id],
                                    'start_node_ID': start_node_id,
                                    'end_node_ID': end_node_id
                                }
                    i += 1
            i += 1

    def get_element_incidences_shell(self, std_data):
        """
        get ELEMENT INCIDENCES SHELL in the std_data
        :return:
        """
        id = None
        node_1 = None
        node_2 = None
        node_3 = None
        node_4 = None

        i = 0
        while i < len(std_data):
            if std_data[i] == "ELEMENT INCIDENCES SHELL":
                # blank line or comment line
                i += 1
                if std_data[i] == '' or std_data[i].split("*")[0] == '*':
                    i += 1
                # find data
                while std_data[i] != 'ELEMENT PROPERTY' and std_data[i] != 'START GROUP DEFINITION' \
                        or std_data[i].split(" ")[0].isnumeric() is True:
                    if std_data[i] == 'START GROUP DEFINITION':
                        print()
                    for text in std_data[i].split(";"):
                        if text != '':
                            split_list = text.split(" ")
                            if '' in split_list:
                                split_list.remove('')
                            if len(split_list) == 4:
                                id = split_list[0]
                                node_1 = split_list[1]
                                node_2 = split_list[2]
                                node_3 = split_list[3]
                                node_4 = None
                            else:
                                id = split_list[0]
                                node_1 = split_list[1]
                                node_2 = split_list[2]
                                node_3 = split_list[3]
                                node_4 = split_list[4]
                            self.element_incidences_shell[id] = {
                                'node_1': node_1,
                                'node_2': node_2,
                                'node_3': node_3,
                                'node_4': node_4
                                }
                    i += 1
            i += 1

    def get_material(self, std_data):
        try:
            start_index = std_data.index("DEFINE MATERIAL START")
            end_index = std_data.index("END DEFINE MATERIAL")
            i = start_index
            while i < end_index + 1:
                if "ISOTROPIC" in std_data[i]:
                    name = std_data[i].split(" ")[1]
                    youngs_modulus = None
                    poissons_ratio = None
                    mass_density = None
                    alpha = None
                    damping_coefficient = None
                    shear_modulus = None
                    type = None

                    while ("ISOTROPIC" not in std_data[i + 1]) and (
                            "END DEFINE MATERIAL" not in std_data[i + 1]):
                        if std_data[i].split(" ")[0] == 'E':
                            youngs_modulus = float(std_data[i].split(" ")[1]) * self.units['unit'][
                                'convert_factor_force']
                        if std_data[i].split(" ")[0] == 'POISSON':
                            poissons_ratio = float(std_data[i].split(" ")[1])
                        if std_data[i].split(" ")[0] == 'DENSITY':
                            mass_density = \
                                float(std_data[i].split(" ")[1]) * self.units['unit']['convert_factor_force'] / 9.81
                        if std_data[i].split(" ")[0] == 'ALPHA':
                            alpha = float(std_data[i].split(" ")[1])
                        if std_data[i].split(" ")[0] == 'DAMP':
                            damping_coefficient = float(std_data[i].split(" ")[1])
                        if std_data[i].split(" ")[0] == 'TYPE':
                            type = std_data[i].split(" ")[1]
                        if std_data[i].split(" ")[0] == 'G':
                            shear_modulus = float(std_data[i].split(" ")[1]) * self.units['unit'][
                                'convert_factor_force']

                        i += 1

                    if std_data[i].split(" ")[0] == 'E':
                        youngs_modulus = float(std_data[i].split(" ")[1]) * self.units['unit'][
                            'convert_factor_force']
                    if std_data[i].split(" ")[0] == 'POISSON':
                        poissons_ratio = float(std_data[i].split(" ")[1])
                    if std_data[i].split(" ")[0] == 'DENSITY':
                        mass_density = \
                            float(std_data[i].split(" ")[1]) * self.units['unit']['convert_factor_force'] / 9.81
                    if std_data[i].split(" ")[0] == 'ALPHA':
                        alpha = float(std_data[i].split(" ")[1])
                    if std_data[i].split(" ")[0] == 'DAMP':
                        damping_coefficient = float(std_data[i].split(" ")[1])
                    if std_data[i].split(" ")[0] == 'TYPE':
                        type = std_data[i].split(" ")[1]
                    if std_data[i].split(" ")[0] == 'G':
                        shear_modulus = float(std_data[i].split(" ")[1]) * self.units['unit'][
                            'convert_factor_force']

                    self.materials[name] = {
                        'name': name,
                        'youngs_modulus': youngs_modulus,
                        'poissons_ratio': poissons_ratio,
                        'mass_density': mass_density,
                        'alpha': alpha,
                        'damping_coefficient': damping_coefficient,
                        'shear_modulus': shear_modulus,
                        'type': type,
                        'feature': 'isotropic'
                    }
                i += 1

        except ValueError:
            pass

    def get_member_properties(self, std_data):
        """
        to get properties , section from std file
        :return: a dictionary contain of section properties
        """
        i = 0
        count = 0
        while i < len(std_data):
            if len(re.findall("START USER TABLE", std_data[i])) != 0:
                i += 1
                while std_data[i] != 'END':
                    if 'TABLE' in std_data[i]:
                        table_no = std_data[i].split(' ')[1]
                        i += 1
                    elif 'UNIT' in std_data[i]:
                        i += 1
                    elif std_data[i] == 'GENERAL':
                        i += 1
                        name_of_section = std_data[i]
                        i += 1
                        section_data = std_data[i]
                        i += 1
                        while std_data[i] != 'PROFILE_POINTS':
                            section_data += std_data[i]
                            i += 1
                        area = section_data.split(' ')[0]
                        depth = section_data.split(' ')[1]
                        web_thickness = section_data.split(' ')[2]
                        width = section_data.split(' ')[3]
                        flange_thickness = section_data.split(' ')[4]
                        second_moment_area_z = section_data.split(' ')[5]
                        second_moment_area_y = section_data.split(' ')[6]
                        second_moment_area_x = section_data.split(' ')[7]
                        section_modulus_z = section_data.split(' ')[8]
                        section_modulus_y = section_data.split(' ')[9]
                        shear_area_y = section_data.split(' ')[10]
                        shear_area_z = section_data.split(' ')[11]
                        plastic_section_modulus_z = section_data.split(' ')[12]
                        plastic_section_modulus_y = section_data.split(' ')[13]
                        warping_constant = section_data.split(' ')[14]
                        depth_of_web = section_data.split(' ')[15]
                        i += 1
                        profile_points = std_data[i]
                        while std_data[i+1][0].isnumeric():
                            profile_points += std_data[i+1]
                            i += 1
                        profile_coordinates = []
                        if profile_points[0] == ' ':
                            profile_points_split = profile_points[1:].split(' ')
                        else:
                            profile_points_split = profile_points.split(' ')
                        for j in range(int(len(profile_points_split)/2)):
                            profile_coordinates.append([float(profile_points_split[2*j]),
                                                        float(profile_points_split[2*j + 1])])
                        count += 1
                        type_section = "user_defined"
                        self.member_properties[count] = dict()
                        self.member_properties[count] = {'table_no': table_no,
                                                         'profile_name': name_of_section,
                                                         'type_section': type_section,
                                                         'profile': profile_coordinates,
                                                         'assigned_beam': None,
                                                         'area': area,
                                                         'depth': depth,
                                                         'web_thickness': web_thickness,
                                                         'width': width,
                                                         'flange_thickness': flange_thickness,
                                                         'second_moment_area_z':second_moment_area_z,
                                                         'second_moment_area_y': second_moment_area_y,
                                                         'second_moment_area_x': second_moment_area_x,
                                                         'section_modulus_z': section_modulus_z,
                                                         'section_modulus_y': section_modulus_y,
                                                         'shear_area_y': shear_area_y,
                                                         'shear_area_z': shear_area_z,
                                                         'plastic_section_modulus_z': plastic_section_modulus_z,
                                                         'plastic_section_modulus_y': plastic_section_modulus_y,
                                                         'warping_constant': warping_constant,
                                                         'depth_of_web': depth_of_web
                                                         }
                    else:
                        i += 1
            if len(re.findall("MEMBER PROPERTY", std_data[i])) != 0:
                while std_data[i + 1].split(" ")[0].isnumeric() == True:
                    i += 1
                    if len(re.findall("PRIS ROUND", std_data[i])) != 0:  # for circular hollow section
                        count += 1
                        # type of section
                        type_section = "circular_hollow_section"
                        self.member_properties[count] = dict()
                        # dimension STA, END, THI
                        STA = std_data[i].split("PRIS ROUND ")[1].split(" ")[1]
                        END = std_data[i].split("PRIS ROUND ")[1].split(" ")[3]
                        THI = std_data[i].split("PRIS ROUND ")[1].split(" ")[5]

                        self.member_properties[count] = {
                            'type_section': type_section,
                            'start_diameter': STA,
                            'end_diamter': END,
                            'thickness': THI,
                            'assigned_beam': self.detail_members(std_data[i].split(" PRIS ROUND ")[0].split(" "))
                        }

                        i -= 1

                    elif len(re.findall("UPTABLE", std_data[i])) != 0:
                        name_and_table_no = std_data[i].split('UPTABLE ')[1]
                        table_no = name_and_table_no.split(' ')[0]
                        name_of_user_section = std_data[i].split(f'UPTABLE {table_no} ')[1]
                        assigned_beams = std_data[i].split(' UPTABLE ')[0]
                        for key, value in self.member_properties.items():
                            if value['table_no'] == table_no and value['profile_name'] == name_of_user_section:
                                section_counter = key
                                break
                        self.member_properties[section_counter]['assigned_beam'] = self.detail_members(assigned_beams)

                    elif len(re.findall("PRIS", std_data[i])) != 0 and len(re.findall("YD", std_data[i])) != 0 \
                            and len(re.findall("ZD", std_data[i])) != 0 and len(
                        re.findall("YB", std_data[i])) != 0 \
                            and len(re.findall("ZB", std_data[i])) != 0:  # for rectangular section
                        # type of section
                        type_section = "prismatic_tee"
                        count += 1
                        self.member_properties[count] = dict()
                        # dimension YD, ZD
                        YD = std_data[i].split("PRIS ")[1].split(" ")[1]
                        ZD = std_data[i].split("PRIS ")[1].split(" ")[3]
                        YB = std_data[i].split("PRIS ")[1].split(" ")[5]
                        ZB = std_data[i].split("PRIS ")[1].split(" ")[7]

                        self.member_properties[count] = {
                            'type_section': type_section,
                            'YD': YD,
                            'ZD': ZD,
                            'YB': YB,
                            'ZB': ZB,
                            'assigned_beam': self.detail_members(std_data[i].split(" PRIS ")[0].split(" "))
                        }
                        i -= 1

                    elif len(re.findall("PRIS", std_data[i])) != 0 and len(re.findall("YD", std_data[i])) != 0 \
                            and len(re.findall("ZD", std_data[i])) != 0 \
                            and len(re.findall("ZB", std_data[i])) != 0:  # for prismatic_trapzoid section
                        # type of section
                        type_section = "prismatic_trapzoid"
                        count += 1
                        self.member_properties[count] = dict()
                        # dimension YD, ZD
                        YD = std_data[i].split("PRIS ")[1].split(" ")[1]
                        ZD = std_data[i].split("PRIS ")[1].split(" ")[3]
                        ZB = std_data[i].split("PRIS ")[1].split(" ")[5]

                        self.member_properties[count] = {
                            'type_section': type_section,
                            'YD': YD,
                            'ZD': ZD,
                            'ZB': ZB,
                            'assigned_beam': self.detail_members(std_data[i].split(" PRIS ")[0].split(" "))
                        }
                        i -= 1

                    elif len(re.findall("PRIS", std_data[i])) != 0 and len(re.findall("YD", std_data[i])) != 0 \
                            and len(re.findall("ZD", std_data[i])) != 0:  # for rectangular section
                        # type of section
                        type_section = "rectangular"
                        count += 1
                        self.member_properties[count] = dict()
                        # dimension YD, ZD
                        YD = std_data[i].split("PRIS ")[1].split(" ")[1]
                        ZD = std_data[i].split("PRIS ")[1].split(" ")[3]

                        self.member_properties[count] = {
                            'type_section': type_section,
                            'YD': YD,
                            'ZD': ZD,
                            'assigned_beam': self.detail_members(std_data[i].split(" PRIS ")[0].split(" "))
                        }
                        i -= 1

                    elif len(re.findall("PRIS", std_data[i])) != 0 and len(re.findall("YD", std_data[i])) != 0 \
                            and len(re.findall("ZD", std_data[i])) == 0:  # for circular section
                        # type of section
                        type_section = "circle"
                        count += 1
                        self.member_properties[count] = dict()
                        # dimension YD, ZD
                        YD = std_data[i].split("PRIS ")[1].split(" ")[1]

                        self.member_properties[count] = {
                            'type_section': type_section,
                            'diameter': YD,
                            'assigned_beam': self.detail_members(std_data[i].split(" PRIS ")[0].split(" "))
                        }
                        i -= 1

                    elif len(re.findall("TAPERED", std_data[i])) != 0:  # for TAPERED section
                        # type of section
                        type_section = "tapered"
                        count += 1
                        self.member_properties[count] = dict()
                        # dimension F1,F2, .., F7
                        F1 = std_data[i].split("TAPERED ")[1].split(" ")[0]
                        F2 = std_data[i].split("TAPERED ")[1].split(" ")[1]
                        F3 = std_data[i].split("TAPERED ")[1].split(" ")[2]
                        F4 = std_data[i].split("TAPERED ")[1].split(" ")[3]
                        F5 = std_data[i].split("TAPERED ")[1].split(" ")[4]
                        F6 = std_data[i].split("TAPERED ")[1].split(" ")[5]
                        F7 = std_data[i].split("TAPERED ")[1].split(" ")[6]

                        self.member_properties[count] = {
                            'type_section': type_section,
                            'F1': F1,
                            'F2': F2,
                            'F3': F3,
                            'F4': F4,
                            'F5': F5,
                            'F6': F6,
                            'F7': F7,
                            'assigned_beam': self.detail_members(std_data[i].split(" TAPERED ")[0].split(" "))
                        }
                        i -= 1

                    elif len(re.findall("TABLE ST PIPE", std_data[i])) != 0 and len(re.findall("ID", std_data[i])) != 0 \
                            and len(re.findall("OD", std_data[i])) != 0:  # for circular section
                        # type of section
                        type_section = "pipe"
                        count += 1
                        self.member_properties[count] = dict()
                        # dimension OD, ID
                        od = re.findall('(OD\s+)([+-]?([0-9]*[.])?[0-9]+)', std_data[i])[0][1]
                        id = re.findall('(ID\s+)([+-]?([0-9]*[.])?[0-9]+)', std_data[i])[0][1]
                        self.member_properties[count] = {
                            'type_section': type_section,
                            'OD': od,
                            'ID': id,
                            'assigned_beam': self.detail_members(std_data[i].split(" TABLE ST ")[0].split(" "))
                        }
                        i -= 1

                    elif len(re.findall("TABLE ST", std_data[i])) != 0:  # for predefined section
                        # type of section
                        type_section = "predefined"
                        count += 1
                        self.member_properties[count] = dict()
                        # temp_dict=dict()
                        # name of section
                        name = std_data[i].split("TABLE ST ")[1].split(" ")[0]
                        if (name[:2] == 'HE' and name[2].isdigit()) or name[-3:] == 'CHS' or name[-3:] == 'RHS' \
                                or name[-3:] == 'SHS':
                            section_size = ''.join(i for i in name if i.isdigit())
                            section_type = ''.join(i for i in name if not i.isdigit())
                            name = section_type + section_size
                        self.member_properties[count] = {
                            'type_section': type_section,
                            'name': name,
                            'assigned_beam': self.detail_members(std_data[i].split(" TABLE ST ")[0].split(" "))
                        }
                        if 'X' in name:
                            name = name.replace("X", "x")
                        self.member_properties[count] = {
                            'type_section': type_section,
                            'name': name,
                            'assigned_beam': self.detail_members(std_data[i].split(" TABLE ST ")[0].split(" "))
                        }
                        i -= 1

                    else:
                        i -= 1
                    i += 1

            i += 1

    def get_element_properties(self, std_data):
        """
        to get the properties of plate or surface from the list string which extracted from std file
        :return: a dictionary contains of section properties and list of plate ID
        """
        i = 0
        while i < len(std_data):
            if len(re.findall("ELEMENT PROPERTY", std_data[i])) != 0:
                i += 1
                count = 0
                while std_data[i].split(" ")[0].isnumeric() == True:
                    count += 1
                    if len(std_data[i].split(" THICKNESS ")[1].split(" ")) == 4:
                        node1 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[0])
                        node2 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[1])
                        node3 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[2])
                        node4 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[3])

                    elif len(std_data[i].split(" THICKNESS ")[1].split(" ")) == 3:
                        node1 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[0])
                        node2 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[1])
                        node3 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[2])

                    elif len(std_data[i].split(" THICKNESS ")[1].split(" ")) == 2:
                        node1 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[0])
                        node2 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[1])
                    else:
                        node1 = node2 = node3 = node4 = float(std_data[i].split(" THICKNESS ")[1].split(" ")[0])

                    self.element_properties["thickness " + str(count)] = {
                        'node_1': node1,
                        'node_2': node2,
                        'node_3': node3,
                        'node_4': node4,
                        'assigned_plate': self.detail_members(std_data[i].split(" THICKNESS ")[0].split(" "))
                    }
                    i += 1

            i += 1

    def get_constants(self, std_data):
        """
        a method to get the list of members whichs assigned with specific type of material.
        :return: dictionary
        """
        i = 0
        while i < len(std_data):
            if len(re.findall("CONSTANTS", std_data[i])) != 0:
                i += 1
                while std_data[i].split(" ")[0] == 'MATERIAL' or std_data[i].split(" ")[0] == 'BETA' or \
                        std_data[i].split(" ")[0][0].isdigit() is True:
                    if std_data[i].split(" ")[0] == 'MATERIAL':
                        if len(re.findall(" MEMB ", std_data[i])) != 0:
                            material_name = std_data[i].split('MATERIAL ', 1)[1].split(" MEMB ")[0]
                            if material_name in self.constants:
                                self.constants[material_name].extend(
                                    self.detail_members(std_data[i].split(' MEMB ')[1].split(" ")))
                            else:
                                self.constants[material_name] = self.detail_members(
                                    std_data[i].split(' MEMB ')[1].split(" "))
                        elif len(re.findall("ALL", std_data[i])) != 0:
                            material_name = std_data[i].split('MATERIAL ')[1].split(" ALL")[0]
                            self.constants[material_name] = 'ALL'
                    i += 1
            i += 1

    def get_beta_angles(self, std_data):
        """
        This function to obtain all of the members that have a beta angle assigned to them and their respective beta
        angle from STAAD

        Input:
            - std_data: std file which has been read as a list of strings

        Output:
            - Returns a dictionary of members and the direction of their local z axis
        """
        i = 0
        beta_counter = 0
        temp_beta_angle_dict = dict()
        while i < len(std_data):
            if len(re.findall("CONSTANTS", std_data[i])) != 0:
                i += 1
                while std_data[i].split(" ")[0] == 'MATERIAL' or std_data[i].split(" ")[0] == 'BETA' or \
                        std_data[i].split(" ")[0][0].isdigit() is True:
                    # if material is present ignore
                    if std_data[i].split(" ")[0] == 'MATERIAL':
                        beta_counter = 0
                    # if beta is present determine the beta angle in that line relative to the string 'BETA'
                    elif std_data[i].split(" ")[0] == 'BETA':
                        beta_counter = 1
                        beta_angle = f'{std_data[i].split(" ")[0]} {std_data[i].split(" ")[1]} {std_data[i].split(" ")[2]}'
                        # if beta angle already defined in the dictionary, add member id to the value
                        if beta_angle in temp_beta_angle_dict:
                            temp_beta_angle_dict[beta_angle].extend(
                                self.detail_members(std_data[i].split(' MEMB ')[1].split(" ")))
                        # else create new key
                        else:
                            temp_beta_angle_dict[beta_angle] = self.detail_members(
                                std_data[i].split(' MEMB ')[1].split(" "))
                    # if line starts with a number and a beta angle has been defined then add line to the previous beta
                    elif std_data[i].split(" ")[0][0].isdigit() is True and beta_counter == 1:
                        temp_beta_angle_dict[beta_angle].extend(self.detail_members(std_data[i].split(" ")))
                    i += 1
            i += 1

        for key in temp_beta_angle_dict:
            value = temp_beta_angle_dict[key]
            for i in value:
                # check if the line has '-' or ' ' as that isnt a member
                if '-' in i or ' ' in i:
                    pass
                else:
                    # obtain angle and the vector of the member
                    angle_of_beta = str(key).split(' ')[1]
                    start_node_coords = self.member_incidences[i]['start_node']
                    end_node_coords = self.member_incidences[i]['end_node']
                    member_vector = [start_node_coords[0] - end_node_coords[0],
                                     start_node_coords[1] - end_node_coords[1],
                                     start_node_coords[2] - end_node_coords[2]]
                    # check that the member has a vector in the global axis and determine the global direction
                    if member_vector.count(0) != 2:
                        continue
                    if member_vector[0] > 0:
                        member_direction = '-X'
                    elif member_vector[0] < 0:
                        member_direction = '+X'
                    elif member_vector[1] > 0:
                        member_direction = '-Y'
                    elif member_vector[1] < 0:
                        member_direction = '+Y'
                    elif member_vector[2] > 0:
                        member_direction = '-Z'
                    elif member_vector[2] < 0:
                        member_direction = '+Z'
                    else:
                        continue
                    # from the member direction and the beta angle applied to it in staad, determine the vector to
                    # be applied to it to define its local z axis
                    vector_list = None
                    if member_direction == '+Z':
                        if angle_of_beta == '0':
                            vector_list = [-1, 0, 0]
                        elif angle_of_beta == '90':
                            vector_list = [0, -1, 0]
                        elif angle_of_beta == '180':
                            vector_list = [1, 0, 0]
                        elif angle_of_beta == '270':
                            vector_list = [0, 1, 0]
                    elif member_direction == '-Z':
                        if angle_of_beta == '0':
                            vector_list = [1, 0, 0]
                        elif angle_of_beta == '90':
                            vector_list = [0, -1, 0]
                        elif angle_of_beta == '180':
                            vector_list = [-1, 0, 0]
                        elif angle_of_beta == '270':
                            vector_list = [0, 1, 0]
                    elif member_direction == '+Y':
                        if angle_of_beta == '0':
                            vector_list = [0, 0, 1]
                        elif angle_of_beta == '90':
                            vector_list = [1, 0, 0]
                        elif angle_of_beta == '180':
                            vector_list = [0, 0, -1]
                        elif angle_of_beta == '270':
                            vector_list = [-1, 0, 0]
                    elif member_direction == '-Y':
                        if angle_of_beta == '0':
                            vector_list = [0, 0, 1]
                        elif angle_of_beta == '90':
                            vector_list = [-1, 0, 0]
                        elif angle_of_beta == '180':
                            vector_list = [0, 0, -1]
                        elif angle_of_beta == '270':
                            vector_list = [1, 0, 0]
                    elif member_direction == '+X':
                        if angle_of_beta == '0':
                            vector_list = [0, 0, 1]
                        elif angle_of_beta == '90':
                            vector_list = [0, -1, 0]
                        elif angle_of_beta == '180':
                            vector_list = [0, 0, -1]
                        elif angle_of_beta == '270':
                            vector_list = [0, 1, 0]
                    elif member_direction == '-X':
                        if angle_of_beta == '0':
                            vector_list = [0, 0, -1]
                        elif angle_of_beta == '90':
                            vector_list = [0, -1, 0]
                        elif angle_of_beta == '180':
                            vector_list = [0, 0, 1]
                        elif angle_of_beta == '270':
                            vector_list = [0, 1, 0]
                    # if vector list present, append to dictionary ready to update local z axis
                    if vector_list is None:
                        pass
                    else:
                        self.beta_angles[i] = vector_list
                    print('')

    def get_offsets(self, std_data):
        """
        This function to obtain all of the members that have an offset assigned to them and their respective offset
         from STAAD

        Input:
            - std_data: std file which has been read as a list of strings

        Output:
            - Returns a dictionary of members and their respective eccentricities at the start and end of the member
        """
        i = 0
        temp_offset_dict = dict()
        temp_list = []
        while i < len(std_data):
            if len(re.findall("MEMBER OFFSET", std_data[i])) != 0:
                i += 1
                # once member offset has been found, while loop until the first value in the line is not a number
                while std_data[i].split(" ")[0][0].isdigit() is True:
                    # if - present in line that means that the line has overflowed onto the next and therefore append
                    # all members in this line to the temp_list
                    if std_data[i].split(" ")[-1] == '-':
                        temp_list.extend(self.detail_members(std_data[i].split(" -")[0].split(' ')))
                    elif 'START' in std_data[i]:
                        # if start present in line, split the line up to obtain all members and add them to temp_list
                        temp_list.extend(self.detail_members(std_data[i].split('START')[0].split(' ')))
                        # offset vector is obtained below
                        offset_str = std_data[i].split('START ')[1]
                        # if the vector is already present then add members to existing key otherwise create new one
                        if f'START {offset_str}' in temp_offset_dict.keys():
                            temp_offset_dict[f'START {offset_str}'].extend(temp_list)
                        else:
                            temp_offset_dict[f'START {offset_str}'] = []
                            temp_offset_dict[f'START {offset_str}'].extend(temp_list)
                        temp_list.clear()
                    # repeat process for start above for when it is replaced with END
                    elif 'END' in std_data[i]:
                        temp_list.extend(self.detail_members(std_data[i].split('END')[0].split(' ')))
                        offset_str = std_data[i].split('END ')[1]
                        if f'END {offset_str}' in temp_offset_dict.keys():
                            temp_offset_dict[f'END {offset_str}'].extend(temp_list)
                        else:
                            temp_offset_dict[f'END {offset_str}'] = []
                            temp_offset_dict[f'END {offset_str}'].extend(temp_list)
                        temp_list.clear()
                    i += 1
            i += 1
        for key in temp_offset_dict:
            # get a list of all values in the dictionary above
            lst = temp_offset_dict[key]
            for i in range(len(lst)):
                # if member nos (i) not present in self.offsets, create new entry for it
                if lst[i] not in self.offsets:
                    self.offsets[lst[i]] = {'START': None,
                                            'END': None}
                # assign offset vector to the start and end depending on what string is present
                if 'START' in key:
                    self.offsets[lst[i]]['START'] = [key.split(' ')[1], key.split(' ')[2], key.split(' ')[3]]
                elif 'END' in key:
                    self.offsets[lst[i]]['END'] = [key.split(' ')[1], key.split(' ')[2], key.split(' ')[3]]

    def get_supports(self, std_data):
        """
        to get the supports from std file
        :return: a dictionary contains of type of support and list of assigned node
        """
        i = 0
        count = 0
        self.supports['FIXED BUT'] = dict()
        while i < len(std_data):
            if re.search('^SUPPORT', std_data[i]):
                i += 1
                while std_data[i].split(" ")[0].isnumeric() == True:
                    if len(re.findall(" FIXED BUT ", std_data[i])) != 0:
                        count += 1
                        KFX = None
                        KFY = None
                        KFZ = None
                        KMX = None
                        KMY = None
                        KMZ = None
                        if len(re.findall("KFX", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KFX = re.findall("(KFX\s\d+)", std_data[i].split(" FIXED BUT ")[1])[0].split(" ")[1]
                        elif len(re.findall("FX", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KFX = 0
                        if len(re.findall("KFY", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KFY = re.findall("(KFY\s\d+)", std_data[i].split(" FIXED BUT ")[1])[0].split(" ")[1]
                        elif len(re.findall("FY", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KFY = 0
                        if len(re.findall("KFZ", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KFZ = re.findall("(KFZ\s\d+)", std_data[i].split(" FIXED BUT ")[1])[0].split(" ")[1]
                        elif len(re.findall("FZ", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KFZ = 0
                        if len(re.findall("KMX", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KMX = re.findall("(KMX\s\d+)", std_data[i].split(" FIXED BUT ")[1])[0].split(" ")[1]
                        elif len(re.findall("MX", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KMX = 0
                        if len(re.findall("KMY", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KMY = re.findall("(KMY\s\d+)", std_data[i].split(" FIXED BUT ")[1])[0].split(" ")[1]
                        elif len(re.findall("MY", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KMY = 0
                        if len(re.findall("KMZ", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KMZ = re.findall("(KMZ\s\d+)", std_data[i].split(" FIXED BUT ")[1])[0].split(" ")[1]
                        elif len(re.findall("MZ", std_data[i].split(" FIXED BUT ")[1])) != 0:
                            KMZ = 0

                        self.supports['FIXED BUT'][count] = {
                            'KFX': KFX,
                            'KFY': KFY,
                            'KFZ': KFZ,
                            'KMX': KMX,
                            'KMY': KMY,
                            'KMZ': KMZ,
                            'assigned_node': self.detail_members(std_data[i].split(" FIXED BUT ")[0].split(" "))
                        }
                    elif len(re.findall(" PINNED", std_data[i])) != 0:
                        self.supports['PINNED'] = self.detail_members(std_data[i].split(" PINNED")[0].split(" "))
                    elif len(re.findall(" FIXED", std_data[i])) != 0:
                        self.supports['FIXED'] = self.detail_members(std_data[i].split(" FIXED")[0].split(" "))
                    else:
                        i += 1
                    i += 1
            i += 1

    def get_primary_loadcases(self, std_data):
        """
        a method to get load primary in staad file
        :return: a dictionary contains all of loadcase and load items inside itself
        """
        for i in range(len(std_data)):
            while len(re.findall('LOAD\s\d', std_data[i])) != 0:
                # Find load case title line in STAAD
                load_id = re.findall('(LOAD\s\d+)', std_data[i])[0].split(' ')[1]
                # If load type has been defined on this line, split it and find the load type
                if 'LOADTYPE' in std_data[i]:
                    load_type = re.findall('(LOADTYPE\s\w+)', std_data[i])[0].split(' ')[1]
                # Else assume it is a live load
                else:
                    load_type = 'Live'
                # if TITLE not present, the name is the text after LOAD CASE
                if 'TITLE' not in std_data[i]:
                    load_name = std_data[i].split(' ')[2]
                # elif TITLE LOAD CASE present the name is the string after this
                elif len(re.findall('TITLE LOAD CASE\s\w+', std_data[i])) != 0:
                    load_name = 'LOAD CASE ' + re.findall('TITLE LOAD CASE\s\w+', std_data[i])[0].split(' ')[3]
                # else its the text after TITLE
                elif re.findall('TITLE\s\w+', std_data[i]) != 0:
                    load_name = std_data[i].split('TITLE ')[1]

                self.primary_loadcases[load_id] = {
                    'load_type': load_type,
                    'load_name': load_name,
                    'load_items': dict()
                }

                i += 1
                while std_data[i].split(' ')[0] == 'SELFWEIGHT' or len(re.findall('JOINT LOAD', std_data[i])) != 0 or \
                        len(re.findall('SUPPORT DISPLACEMENT LOAD', std_data[i])) != 0 or \
                        len(re.findall('MEMBER LOAD', std_data[i])) != 0 or \
                        len(re.findall('ELEMENT LOAD', std_data[i])) != 0 or \
                        len(re.findall('REPEAT LOAD', std_data[i])) != 0:
                    if std_data[i].split(' ')[0] == 'SELFWEIGHT':
                        if 'SELFWEIGHT' not in self.primary_loadcases[load_id]['load_items']:
                            self.primary_loadcases[load_id]['load_items']['SELFWEIGHT'] = dict()
                            count = 0
                        else:
                            count = len(self.primary_loadcases[load_id]['load_items']['SELFWEIGHT'])
                        while std_data[i].split(' ')[0] == 'SELFWEIGHT':
                            temp_dict = dict()
                            count += 1
                            direction = re.findall('SELFWEIGHT\s\w+', std_data[i])[0].split(' ')[1]
                            factor = std_data[i].split(' ')[2]
                            if len(re.findall('LIST', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' LIST ')[1].split(' '))
                            else:
                                lst_members = ['ALL']

                            temp_dict = {
                                'direction': direction,
                                'factor': float(factor),
                                'assigned_members': lst_members
                            }
                            self.primary_loadcases[load_id]['load_items']['SELFWEIGHT'][count] = copy.deepcopy(temp_dict)
                            i += 1

                    if len(re.findall('JOINT LOAD', std_data[i])) != 0:
                        i += 1
                        # read joint load and collect to dictionary
                        if 'JOINT LOAD' not in self.primary_loadcases[load_id]['load_items']:
                            self.primary_loadcases[load_id]['load_items']['JOINT LOAD'] = dict()
                            count = 0
                        else:
                            count = len(self.primary_loadcases[load_id]['load_items']['JOINT LOAD'])
                        temp_dict = dict()
                        while std_data[i].split(' ')[0].isnumeric():
                            FX = FY = FZ = MX = MY = MZ = None
                            if len(re.findall('FX', std_data[i])) != 0:
                                FX = float(std_data[i].split('FX ')[1].split(' ')[0]) * self.units['unit'][
                                    'convert_factor_force']
                            if len(re.findall('FY', std_data[i])) != 0:
                                FY = float(std_data[i].split('FY ')[1].split(' ')[0]) * self.units['unit'][
                                    'convert_factor_force']
                            if len(re.findall('FZ', std_data[i])) != 0:
                                FZ = float(std_data[i].split('FZ ')[1].split(' ')[0]) * self.units['unit'][
                                    'convert_factor_force']
                            if len(re.findall('MX', std_data[i])) != 0:
                                MX = float(std_data[i].split('MX ')[1].split(' ')[0]) * self.units['unit'][
                                    'convert_factor_force']
                            if len(re.findall('MY', std_data[i])) != 0:
                                MY = float(std_data[i].split('MY ')[1].split(' ')[0]) * self.units['unit'][
                                    'convert_factor_force']
                            if len(re.findall('MZ', std_data[i])) != 0:
                                MZ = float(std_data[i].split('MZ ')[1].split(' ')[0]) * self.units['unit'][
                                    'convert_factor_force']

                            count += 1
                            if len(re.findall('FX', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' FX')[0].split(' '))
                            elif len(re.findall('FY', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' FY')[0].split(' '))
                            elif len(re.findall('FZ', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' FZ')[0].split(' '))
                            elif len(re.findall('MX', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' MX')[0].split(' '))
                            elif len(re.findall('MY', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' MY')[0].split(' '))
                            elif len(re.findall('MZ', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' MZ')[0].split(' '))
                            temp_dict = {
                                'FX': FX,
                                'FY': FY,
                                'FZ': FZ,
                                'MX': MX,
                                'MY': MY,
                                'MZ': MZ,
                                'assigned_members': lst_members
                            }
                            self.primary_loadcases[load_id]['load_items']['JOINT LOAD'][count] = copy.deepcopy(temp_dict)
                            i += 1

                    if len(re.findall('SUPPORT DISPLACEMENT LOAD', std_data[i])) != 0:
                        i += 1
                        # read support displacement load and collect to dictionary
                        if 'SUPPORT DISPLACEMENT LOAD' not in self.primary_loadcases[load_id]['load_items']:
                            self.primary_loadcases[load_id]['load_items']['SUPPORT DISPLACEMENT LOAD'] = dict()
                            count = 0
                        else:
                            count = len(self.primary_loadcases[load_id]['load_items']['SUPPORT DISPLACEMENT LOAD'])
                        temp_dict = dict()
                        while std_data[i].split(' ')[0].isnumeric():
                            FX = FY = FZ = MX = MY = MZ = None
                            if len(re.findall('FX', std_data[i])) != 0:
                                FX = float(
                                    std_data[i].split('FX ')[1].split(' ')[0]) * self.units['unit']['convert_factor_force']
                            if len(re.findall('FY', std_data[i])) != 0:
                                FY = float(
                                    std_data[i].split('FY ')[1].split(' ')[0]) * self.units['unit']['convert_factor_force']
                            if len(re.findall('FZ', std_data[i])) != 0:
                                FZ = float(
                                    std_data[i].split('FZ ')[1].split(' ')[0]) * self.units['unit']['convert_factor_force']
                            if len(re.findall('MX', std_data[i])) != 0:
                                MX = float(
                                    std_data[i].split('MX ')[1].split(' ')[0]) * self.units['unit']['convert_factor_force']\
                                     * math.pi/ 180
                            if len(re.findall('MY', std_data[i])) != 0:
                                MY = float(
                                    std_data[i].split('MY ')[1].split(' ')[0]) * self.units['unit']['convert_factor_force']\
                                     * math.pi/ 180
                            if len(re.findall('MZ', std_data[i])) != 0:
                                MZ = float(
                                    std_data[i].split('MZ ')[1].split(' ')[0]) * self.units['unit']['convert_factor_force']\
                                     * math.pi/ 180

                            count += 1
                            if len(re.findall('FX', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' FX')[0].split(' '))
                            elif len(re.findall('FY', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' FY')[0].split(' '))
                            elif len(re.findall('FZ', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' FZ')[0].split(' '))
                            elif len(re.findall('MX', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' MX')[0].split(' '))
                            elif len(re.findall('MY', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' MY')[0].split(' '))
                            elif len(re.findall('MZ', std_data[i])) != 0:
                                lst_members = self.detail_members(std_data[i].split(' MZ')[0].split(' '))
                            temp_dict = {
                                'FX': FX,
                                'FY': FY,
                                'FZ': FZ,
                                'MX': MX,
                                'MY': MY,
                                'MZ': MZ,
                                'assigned_members': lst_members
                            }
                            self.primary_loadcases[load_id]['load_items']['SUPPORT DISPLACEMENT LOAD'][count] = \
                                copy.deepcopy(temp_dict)
                            i += 1

                    if len(re.findall('MEMBER LOAD', std_data[i])) != 0:
                        i += 1
                        # read support displacement load and collect to dictionary
                        if 'MEMBER LOAD' not in self.primary_loadcases[load_id]['load_items']:
                            self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'] = dict()
                            count = 0
                        else:
                            count = len(self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'])
                        temp_dict = dict()

                        while std_data[i].split(' ')[0].isnumeric():
                            if len(re.findall(' UNI ', std_data[i])) != 0:
                                count += 1

                                if len(re.findall('GX', std_data[i])) != 0:
                                    direction = 'GX'
                                elif len(re.findall('GY', std_data[i])) != 0:
                                    direction = 'GY'
                                elif len(re.findall('GZ', std_data[i])) != 0:
                                    direction = 'GZ'
                                elif len(re.findall('PX', std_data[i])) != 0:
                                    direction = 'PX'
                                elif len(re.findall('PY', std_data[i])) != 0:
                                    direction = 'PY'
                                elif len(re.findall('PZ', std_data[i])) != 0:
                                    direction = 'PZ'
                                elif len(re.findall('X', std_data[i])) != 0:
                                    direction = 'X'
                                elif len(re.findall('Y', std_data[i])) != 0:
                                    direction = 'Y'
                                elif len(re.findall('Z', std_data[i])) != 0:
                                    direction = 'Z'
                                else:
                                    direction = None

                                # Get value : force, d1, d2, d3
                                values_force = std_data[i].split(' UNI ' + direction + ' ')[1].split(' ')
                                force = 0
                                d1 = d2 = d3 = None
                                lst_members = self.detail_members(
                                    std_data[i].split(' UNI ' + direction + ' ')[0].split(' '))
                                if len(values_force) == 1:
                                    force = float(values_force[0]) * self.units['unit']['convert_factor_force']
                                elif len(values_force) == 2:
                                    force = float(values_force[0]) * self.units['unit']['convert_factor_force']
                                    d1 = values_force[1]
                                elif len(values_force) == 3:
                                    force = float(values_force[0]) * self.units['unit']['convert_factor_force']
                                    d1 = float(values_force[1])
                                    d2 = float(values_force[2])
                                else:
                                    force = float(values_force[0]) * self.units['unit']['convert_factor_force']
                                    d1 = float(values_force[1])
                                    d2 = float(values_force[2])
                                    d3 = float(values_force[3])

                                self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'][count] = {
                                    'load_type': 'uniform_force',
                                    'direction': direction,
                                    'force': force,
                                    'd1': d1,
                                    'd2': d2,
                                    'd3': d3,
                                    'assigned_members': lst_members}

                            # Get uniform moment load
                            if len(re.findall(' UMOM ', std_data[i])) != 0:
                                count += 1

                                if len(re.findall('GX', std_data[i])) != 0:
                                    direction = 'GX'
                                elif len(re.findall('GY', std_data[i])) != 0:
                                    direction = 'GY'
                                elif len(re.findall('GZ', std_data[i])) != 0:
                                    direction = 'GZ'
                                elif len(re.findall('PX', std_data[i])) != 0:
                                    direction = 'PX'
                                elif len(re.findall('PY', std_data[i])) != 0:
                                    direction = 'PY'
                                elif len(re.findall('PZ', std_data[i])) != 0:
                                    direction = 'PZ'
                                elif len(re.findall('X', std_data[i])) != 0:
                                    direction = 'X'
                                elif len(re.findall('Y', std_data[i])) != 0:
                                    direction = 'Y'
                                elif len(re.findall('Z', std_data[i])) != 0:
                                    direction = 'Z'
                                else:
                                    direction = None

                                # Get value : moment, d1, d2, d3
                                values_force = std_data[i].split(' UMOM ' + direction + ' ')[1].split(' ')
                                force = 0
                                d1 = d2 = d3 = None
                                lst_members = self.detail_members(
                                    std_data[i].split(' UMOM ' + direction + ' ')[0].split(' '))
                                if len(values_force) == 1:
                                    force = values_force[0]
                                elif len(values_force) == 2:
                                    force = values_force[0]
                                    d1 = float(values_force[1])
                                elif len(values_force) == 3:
                                    force = values_force[0]
                                    d1 = float(values_force[1])
                                    d2 = float(values_force[2])
                                else:
                                    force = values_force[0]
                                    d1 = float(values_force[1])
                                    d2 = float(values_force[2])
                                    d3 = float(values_force[3])

                                self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'][count] = {
                                    'load_type': 'uniform_moment',
                                    'moment': float(force) * self.units['unit']['convert_factor_force'],
                                    'direction': direction,
                                    'd1': d1,
                                    'd2': d2,
                                    'd3': d3,
                                    'assigned_members': lst_members
                                }

                            # Get concentrate force load
                            if len(re.findall(' CON ', std_data[i])) != 0:
                                count += 1

                                if len(re.findall('GX', std_data[i])) != 0:
                                    direction = 'GX'
                                elif len(re.findall('GY', std_data[i])) != 0:
                                    direction = 'GY'
                                elif len(re.findall('GZ', std_data[i])) != 0:
                                    direction = 'GZ'
                                elif len(re.findall('PX', std_data[i])) != 0:
                                    direction = 'PX'
                                elif len(re.findall('PY', std_data[i])) != 0:
                                    direction = 'PY'
                                elif len(re.findall('PZ', std_data[i])) != 0:
                                    direction = 'PZ'
                                elif len(re.findall('X', std_data[i])) != 0:
                                    direction = 'X'
                                elif len(re.findall('Y', std_data[i])) != 0:
                                    direction = 'Y'
                                elif len(re.findall('Z', std_data[i])) != 0:
                                    direction = 'Z'
                                else:
                                    direction = None

                                # get value : moment, d1, d2, d3
                                values_force = std_data[i].split(' CON ' + direction + ' ')[1].split(' ')
                                force = 0
                                d1 = d2 = d3 = None
                                lst_members = self.detail_members(
                                    std_data[i].split(' CON ' + direction + ' ')[0].split(' '))
                                if len(values_force) == 1:
                                    force = values_force[0]
                                elif len(values_force) == 2:
                                    force = values_force[0]
                                    d1 = float(values_force[1])
                                elif len(values_force) == 3:
                                    force = values_force[0]
                                    d1 = float(values_force[1])
                                    d2 = float(values_force[2])
                                else:
                                    force = values_force[0]
                                    d1 = float(values_force[1])
                                    d2 = float(values_force[2])
                                    d3 = float(values_force[3])

                                self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'][count] = {
                                    'load_type': 'concentrated_force',
                                    'force': float(force) * self.units['unit']['convert_factor_force'],
                                    'direction': direction,
                                    'd1': d1,
                                    'd2': d2,
                                    'd3': d3,
                                    'assigned_members': lst_members}

                            # Get linear varying load
                            if len(re.findall(' LIN ', std_data[i])) != 0:
                                count += 1

                                if len(re.findall('X', std_data[i])) != 0:
                                    direction = 'X'
                                elif len(re.findall('Y', std_data[i])) != 0:
                                    direction = 'Y'
                                elif len(re.findall('Z', std_data[i])) != 0:
                                    direction = 'Z'
                                else:
                                    direction = None

                                # get value : moment, d1, d2, d3
                                values_force = std_data[i].split(' LIN ' + direction + ' ')[1].split(' ')
                                w1 = values_force[0] * self.units['unit']['convert_factor_force']
                                w2 = values_force[1] * self.units['unit']['convert_factor_force']
                                lst_members = self.detail_members(
                                    std_data[i].split(' LIN ' + direction + ' ')[0].split(' '))

                                self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'][count] = {
                                    'load_type': 'linear_varying',
                                    'direction': direction,
                                    'W1': float(w1),
                                    'W2': float(w2),
                                    'assigned_members': lst_members}

                            # get trapezoidal load
                            if len(re.findall(' TRAP ', std_data[i])) != 0:
                                count += 1

                                if len(re.findall('GX', std_data[i])) != 0:
                                    direction = 'GX'
                                elif len(re.findall('GY', std_data[i])) != 0:
                                    direction = 'GY'
                                elif len(re.findall('GZ', std_data[i])) != 0:
                                    direction = 'GZ'
                                elif len(re.findall('PX', std_data[i])) != 0:
                                    direction = 'PX'
                                elif len(re.findall('PY', std_data[i])) != 0:
                                    direction = 'PY'
                                elif len(re.findall('PZ', std_data[i])) != 0:
                                    direction = 'PZ'
                                elif len(re.findall('X', std_data[i])) != 0:
                                    direction = 'X'
                                elif len(re.findall('Y', std_data[i])) != 0:
                                    direction = 'Y'
                                elif len(re.findall('Z', std_data[i])) != 0:
                                    direction = 'Z'
                                else:
                                    direction = None

                                # get value : moment, d1, d2, d3
                                values_force = std_data[i].split(' TRAP ' + direction + ' ')[1].split(' ')
                                w1 = values_force[0]
                                w2 = values_force[1]
                                d1 = values_force[2]
                                d2 = values_force[3]
                                lst_members = self.detail_members(
                                    std_data[i].split(' TRAP ' + direction + ' ')[0].split(' '))

                                self.primary_loadcases[load_id]['load_items']['MEMBER LOAD'][count] = {
                                    'load_type': 'trapezoidal',
                                    'direction': direction,
                                    'W1': float(w1) * self.units['unit']['convert_factor_force'],
                                    'W2': float(w2) * self.units['unit']['convert_factor_force'],
                                    'd1': float(d1) * self.units['unit']['convert_factor_force'],
                                    'd2': float(d2) * self.units['unit']['convert_factor_force'],
                                    'assigned_members': lst_members}
                            i += 1
                    if len(re.findall('REPEAT LOAD', std_data[i])) != 0:
                        i += 1
                        # get loadcase_id and load factors
                        dict_factors = dict()
                        for j in range((len(std_data[i].split(' ')) - 1)):
                            if (j % 2) == 0:
                                dict_factors[std_data[i].split(' ')[j]] = float(std_data[i].split(' ')[j + 1])
                        self.primary_loadcases[load_id]['load_items']['REPEAT LOAD'] = {'factors': dict_factors}
                        i += 1

                    if len(re.findall('ELEMENT LOAD', std_data[i])) != 0:
                        i += 1
                        # read element load
                        if 'ELEMENT LOAD' not in self.primary_loadcases[load_id]['load_items']:
                            self.primary_loadcases[load_id]['load_items']['ELEMENT LOAD'] = dict()
                            count = 0
                        else:
                            count = len(self.primary_loadcases[load_id]['load_items']['ELEMENT LOAD'])
                        temp_dict = dict()

                        while std_data[i].split(' ')[0].isnumeric():
                            if len(re.findall(' PR ', std_data[i])) != 0:
                                count += 1
                                if len(re.findall('GX', std_data[i])) != 0:
                                    direction = 'GX'
                                elif len(re.findall('GY', std_data[i])) != 0:
                                    direction = 'GY'
                                elif len(re.findall('GZ', std_data[i])) != 0:
                                    direction = 'GZ'
                                elif len(re.findall('LX', std_data[i])) != 0:
                                    direction = 'LX'
                                elif len(re.findall('LY', std_data[i])) != 0:
                                    direction = 'LY'
                                elif len(re.findall('LZ', std_data[i])) != 0:
                                    direction = 'LZ'
                                else:
                                    direction = None

                                # get value : forces
                                values_force = std_data[i].split(' PR ' + direction + ' ')[1].split(' ')
                                if len(values_force) == 3:
                                    force = float(values_force[0]) * self.units['unit']['convert_factor_force']
                                    x = values_force[1]
                                    y = values_force[2]
                                    lst_members = self.detail_members(
                                        std_data[i].split(' PR ' + direction + ' ')[0].split(' '))
                                    self.primary_loadcases[load_id]['load_items']['ELEMENT LOAD'][count] = {
                                        'load_type': 'concentrate_load',
                                        'force': force,
                                        'direction': direction,
                                        'X': float(x),
                                        'Y': float(y),
                                        'assigned_members': lst_members}

                                else:
                                    force = float(values_force[0]) * self.units['unit']['convert_factor_force']
                                    lst_members = self.detail_members(
                                        std_data[i].split(' PR ' + direction + ' ')[0].split(' '))
                                    self.primary_loadcases[load_id]['load_items']['ELEMENT LOAD'][count] = {
                                        'load_type': 'pressure_on_full_plate',
                                        'force': force,
                                        'direction': direction,
                                        'assigned_members': lst_members}
                            i += 1

                i += 1

    def get_load_combinations(self, std_data):
        """
        a method to get load combinations from data which extracted from staad file
        :return: a dictionary contains of ...
        """
        i = 0
        while i < len(std_data):
            if len(re.findall('LOAD COMB', std_data[i])) != 0:
                # get loadcomb_id, loadcomb_name
                loadcomb_id = re.findall("LOAD COMB\s\d+", std_data[i])[0].split(" ")[2]
                loadcomb_name = std_data[i].replace(re.findall('LOAD COMB\s+\d+\s+', std_data[i])[0],'')
                i += 1
                # get loadcase_id and load factors
                dict_factors = dict()
                for j in range((len(std_data[i].split(' ')) - 1)):
                    if (j % 2) == 0:
                        dict_factors[std_data[i].split(' ')[j]] = float(std_data[i].split(' ')[j + 1])

                self.load_combinations[loadcomb_id] = {
                    'loadcomb_name': loadcomb_name,
                    'factors': dict_factors
                }
            i += 1

    def get_envelopes(self, std_data):
        """
        a method to get the envelope in staad file
        :return: a dictionary
        """
        i = 0
        while i < len(std_data):
            if len(re.findall('DEFINE ENVELOPE', std_data[i])) != 0:
                i += 1
                while len(re.findall('END DEFINE ENVELOPE', std_data[i])) == 0:
                    if len(re.findall("TYPE\s.+", std_data[i])) == 0:
                        envelope_type = None
                    else:
                        envelope_type = re.findall("TYPE\s.+", std_data[i])[0].split(' ')[1]

                    self.envelopes[re.findall("ENVELOPE\s\d+", std_data[i])[0].split(' ')[1]] = {
                        'envelope_type': envelope_type,
                        'combo_list': self.detail_members(std_data[i].split(' ENVELOPE ')[0].split(' '))
                    }
                    i += 1
            i += 1


def convert_direction(RawStd: RawStdFile):
    # to convert the model from Y or Z to the Z up direction. In other case , please go straight to std file to
    # set the Y or Z direction first.

    if RawStd.direction['direction'] == "Z":
        return RawStd
    elif RawStd.direction['direction'] == "Y":
        # change the up direction
        RawStd.direction['direction'] = "Z"
        # convert joint coordinates
        for key, value in RawStd.joint_coordinates.items():
            x = value[0]
            y = value[1]
            z = value[2]
            RawStd.joint_coordinates[key] = [x, -z, y]

        # convert memeber_incidences
        for key, value in RawStd.member_incidences.items():
            value['start_node'] = RawStd.joint_coordinates[value['start_node_ID']]
            value['end_node'] = RawStd.joint_coordinates[value['end_node_ID']]

        # convert direction for support
        for key, value in RawStd.supports.items():
            if key == "FIXED BUT":
                for key1, value1 in RawStd.supports[key].items():
                    k_fx = k_fy = k_fz = k_mx = k_my = k_mz = None
                    if value1['KFX'] != None:
                        k_fx = float(value1['KFX'])
                    if value1['KFZ'] != None:
                        k_fy = float(value1['KFZ'])
                    if value1['KFY'] != None:
                        k_fz = float(value1['KFY'])
                    if value1['KMX'] != None:
                        k_mx = float(value1['KMX'])
                    if value1['KMZ'] != None:
                        k_my = float(value1['KMZ'])
                    if value1['KMY'] != None:
                        k_mz = float(value1['KMY'])
                    RawStd.supports[key][key1] = {
                        'KFX': k_fx,
                        'KFY': k_fy,
                        'KFZ': k_fz,
                        'KMX': k_mx,
                        'KMY': k_my,
                        'KMZ': k_mz,
                        'assigned_node': RawStd.supports[key][key1]['assigned_node']}

        # convert direction for load items
        for key, value in RawStd.primary_loadcases.items():
            for key1, value1 in value['load_items'].items():
                if key1 == 'SELFWEIGHT':
                    for key2, value2 in value1.items():
                        value2['direction'] = 'Z'

                elif key1 == 'JOINT LOAD':
                    for key2, value2 in value1.items():
                        fx = value2['FX']
                        if value2['FZ'] is None:
                            fy = None
                        else:
                            fy = -1 * value2['FZ']
                        fz = value2['FY']
                        mx = value2['MX']
                        if value2['MZ'] is None:
                            my = None
                        else:
                            my = -1 * value2['MZ']
                        mz = value2['MY']
                        value2 = {
                            'FX': fx,
                            'FY': fy,
                            'FZ': fz,
                            'MX': mx,
                            'MY': my,
                            'MZ': mz}

                elif key1 == 'MEMBER LOAD':
                    for key2, value2 in value1.items():
                        if value2['direction'] == 'GY':
                            value2['direction'] = 'GZ'

                        elif value2['direction'] == 'GZ':
                            value2['direction'] = 'GY'
                            value2['force'] == -1 * value2['force']

                elif key1 == 'ELEMENT LOAD':
                    for key2, value2 in value1.items():
                        if value2['direction'] == 'GY':
                            value2['direction'] = 'GZ'

                        elif value2['direction'] == 'GZ':
                            value2['direction'] = 'GY'
                            value2['force'] = -1 * value2['force']

                else:
                    pass

    else:
        raise NotImplementedError("ERROR: The direction sets in std file is not supported to covert.")
    return RawStd


def check_required_information(raw_data: RawStdFile):
    """
    This function checks if the minimum required items are provided in the std-file.

    Input:
        - raw_data(obj): Object reference of raw data from std-file.

    Output:
        - When required information is missing an error is returned, informing user what is missing.
        - For not required information to create the model, a warning is provided.
    """
    if not raw_data.joint_coordinates:
        print("WARNING: No node has definded in the model")
    if not raw_data.member_incidences:
        print("WARNING: No member has definded in the model")
    if not raw_data.element_incidences_shell:
        print("WARNING: No plate has definded in the model")
    if not raw_data.materials:
        raise NotImplementedError('ERROR: No material has definded in the model')
    if not raw_data.member_properties and raw_data.member_incidences:
        raise NotImplementedError('ERROR: No section profile has definded in the model')
    if not raw_data.element_properties and raw_data.element_incidences_shell:
        raise NotImplementedError('ERROR: No thickness has definded in the model')
    if not raw_data.primary_loadcases:
        print('WARNING: No loadcase has definded in the model')
    if not raw_data.load_combinations:
        print('WARNING: No load combination has definded in the model')


def _fem_staad_to_fem(project: 'Project', std_file: Union[str, Path]):
    """
    This function reads the std-file that STAAD has generated of the model. Currently the function reads the following
    STAAD items: linear elastic materials (steel, concrete), isotropic thickness for plates, profiles for members
    (rectangular, prismatic_tee, prismatic_trapzoid, circular_hollow_section and predefined), joint coordinates (nodes),
    member incidences (line shapes, beam, columns), element incidences shell (surface shapes, floor, wall), supports and
    loads. For the items the corresponding objects are created in the PY-memory.

    .. warning:: Components in the std-inputfile that are not mentioned in the list above will be skipped without
      warning. Always check your imported model.

    .. note:: Result items are not yet available for conversion. Development for this feature is planned. Please inquire
      if you require this functionality in your project.

    Input:
        - project (obj): Project object containing collections of fem object and project variables
        - std_file (str): Location of the input file as string.
          Alternative(path): The file and file-location path can aslo be provided as path.

    Output:
        - The inputfile is read and converted to objects in FEM-client.
        - The objects are added to the class instance.

    For example:
     >>> project.from_staad('C//Users//AnyFolder//inputfile.std')
    """
    # Select file to read
    if isinstance(std_file, str):
        if std_file.endswith('.std'):
            std_file = Path(std_file)
        else:
            std_file = Path(std_file + '.std')
    check_required_information(RawStdFile(std_file))
    staad_data = convert_direction(RawStdFile(std_file))

    from rhdhv_fem.fem_mesh import MeshNode, MeshElement
    from rhdhv_fem.shapes import Surfaces, Lines
    from rhdhv_fem.materials import LinearElasticIsotropicModel, Concrete, Steel, CustomMaterial
    from rhdhv_fem.geometries import Geometry, PredefinedProfile, IsotropicThickness, ArbitraryPolygonProfile, TShape, \
        Pipe, CircleProfile, Rectangle
    from rhdhv_fem.supports import PointSupport
    from rhdhv_fem.loads import LoadCase, ModelLoad, LineLoad, SurfaceLoad, PointLoad, LoadCombination
    from rhdhv_fem.general import Direction
    from rhdhv_fem.groups import Group

    # Initialise a dictionary to connect member_id, material and geometry
    dict_mem_mat_geo = dict()

    ## MATERIALS ##
    dict_material = dict()
    for material in staad_data.materials:
        # Create the material-model
        material_model = None
        if 'isotropic' in staad_data.materials[material].values():
            material_model = LinearElasticIsotropicModel.from_staad(staad_data.materials[material], project=project)
        if not material_model:
            raise NotImplementedError(f'ERROR: Material model for {material} is not yet available.')
        else:
            # Create the material
            if 'CONCRETE' in staad_data.materials[material].values():
                material_dummy = Concrete.from_staad({
                    'name': staad_data.materials[material]['name'],
                    'material_model': material_model,
                    'mass_density': staad_data.materials[material]['mass_density'],
                    'alpha': staad_data.materials[material]['alpha']}, project=project)
            elif 'STEEL' in staad_data.materials[material].values():
                material_dummy = Steel.from_staad({
                    'name': staad_data.materials[material]['name'],
                    'material_model': material_model,
                    'mass_density': staad_data.materials[material]['mass_density'],
                    'alpha': staad_data.materials[material]['alpha']}, project=project)
            else:
                material_dummy = CustomMaterial.from_staad({
                    'name': staad_data.materials[material]['name'],
                    'material_model': material_model,
                    'mass_density': staad_data.materials[material]['mass_density'],
                    'alpha': staad_data.materials[material]['alpha'],
                    'damping_coefficient': staad_data.materials[material]['damping_coefficient']},
                    project=project)
            dict_material[material] = material_dummy
    for material_name in staad_data.constants:
        if staad_data.constants[material_name] == 'ALL':
            for member in staad_data.member_incidences:
                dict_mem_mat_geo[member] = {'mat': dict_material[material_name],
                                            'geo': ""}
            for member in staad_data.element_incidences_shell:
                dict_mem_mat_geo[member] = {'mat': dict_material[material_name],
                                            'geo': ""}
        else:
            for member in staad_data.constants[material_name]:
                dict_mem_mat_geo[member] = {'mat': dict_material[material_name],
                                            'geo': ""}

    ## GEOMETRIES for plates ##
    dict_geometry_plate = dict()
    for geometry in staad_data.element_properties:
        # Create geometry_model
        staad_data.element_properties[geometry]['profile_name'] = staad_data.element_properties[geometry].keys()
        geometry_model = IsotropicThickness.from_staad({'thickness': staad_data.element_properties[geometry]['node_1']},
                                                       project=project)
        # Create geometry
        if not geometry_model:
            raise NotImplementedError(
                f'ERROR: Geometry {geometry} is not defined properly or available for conversion.')
        else:
            input_dict = dict()
            input_dict['name'] = geometry
            input_dict['geometry_model'] = geometry_model
            geometry_dummy = Geometry.from_staad(input_dict=input_dict, project=project)
            dict_geometry_plate[geometry] = geometry_dummy
            for member in staad_data.element_properties[geometry]['assigned_plate']:
                dict_mem_mat_geo[member]['geo'] = geometry_dummy

    ## GEOMETRIES for members ##
    dict_geometry_beam = dict()
    for geometry in staad_data.member_properties:
        # Create the geometry-model for profiles
        geometry_model = None
        if staad_data.member_properties[geometry]['type_section'] == 'rectangular':
            geometry_model = Rectangle.from_staad({
                'profile_name': staad_data.member_properties[geometry]['type_section'],
                'height': float(staad_data.member_properties[geometry]['YD']),
                'width': float(staad_data.member_properties[geometry]['ZD'])}, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'prismatic_tee':
            geometry_model = TShape.from_staad({
                'profile_name': staad_data.member_properties[geometry]['type_section'],
                'height': float(staad_data.member_properties[geometry]['YD']),
                'thickness_flange_top':
                    float(staad_data.member_properties[geometry]['YD']) -
                    float(staad_data.member_properties[geometry]['YB']),
                'width_flange_top': float(staad_data.member_properties[geometry]['ZD']),
                'thickness_web': float(staad_data.member_properties[geometry]['ZB'])}, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'prismatic_trapzoid':
            geometry_model = TShape.from_staad({
                'profile_name': staad_data.member_properties[geometry]['type_section'],
                'height': float(staad_data.member_properties[geometry]['YD']),
                'thickness_flange_top': float(staad_data.member_properties[geometry]['YD']),
                'width_flange_top': float(staad_data.member_properties[geometry]['ZD']),
                'thickness_web': float(staad_data.member_properties[geometry]['ZB'])}, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'circular_hollow_section':
            geometry_model = Pipe.from_staad({
                'profile_name': staad_data.member_properties[geometry]['type_section'],
                'diameter': float(staad_data.member_properties[geometry]['start_diameter']),
                'thickness': float(staad_data.member_properties[geometry]['thickness'])}, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'pipe':
            geometry_model = Pipe.from_staad({
                'profile_name': staad_data.member_properties[geometry]['type_section'],
                'diameter': float(staad_data.member_properties[geometry]['OD']),
                'thickness': (float(staad_data.member_properties[geometry]['OD']) - float(staad_data.member_properties[geometry]['ID'])) / 2
            }, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'predefined':
            geometry_model = PredefinedProfile.from_staad(
                {'profile_name': staad_data.member_properties[geometry]['name']}, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'circle':
            geometry_model = CircleProfile.from_staad({
                'profile_name': staad_data.member_properties[geometry]['type_section'],
                'diameter': float(staad_data.member_properties[geometry]['diameter'])
            }, project=project)
        elif staad_data.member_properties[geometry]['type_section'] == 'user_defined':
            input_dict = dict()
            input_dict['profile_name'] = staad_data.member_properties[geometry]['profile_name']
            input_dict['profile'] = staad_data.member_properties[geometry]['profile']
            input_dict['area'] = float(staad_data.member_properties[geometry]['area'])
            input_dict['depth'] = float(staad_data.member_properties[geometry]['depth'])
            input_dict['web_thickness'] = float(staad_data.member_properties[geometry]['web_thickness'])
            input_dict['width'] = float(staad_data.member_properties[geometry]['width'])
            input_dict['flange_thickness'] = float(staad_data.member_properties[geometry]['flange_thickness'])
            input_dict['second_moment_area_z'] = float(staad_data.member_properties[geometry]['second_moment_area_z'])
            input_dict['second_moment_area_y'] = float(staad_data.member_properties[geometry]['second_moment_area_y'])
            input_dict['second_moment_area_x'] = float(staad_data.member_properties[geometry]['second_moment_area_x'])
            input_dict['section_modulus_z'] = float(staad_data.member_properties[geometry]['section_modulus_z'])
            input_dict['section_modulus_y'] = float(staad_data.member_properties[geometry]['section_modulus_y'])
            input_dict['shear_area_y'] = float(staad_data.member_properties[geometry]['shear_area_y'])
            input_dict['shear_area_z'] = float(staad_data.member_properties[geometry]['shear_area_z'])
            input_dict['plastic_section_modulus_z'] = float(staad_data.member_properties[geometry]['plastic_section_modulus_z'])
            input_dict['plastic_section_modulus_y'] = float(staad_data.member_properties[geometry]['plastic_section_modulus_y'])
            input_dict['warping_constant'] = float(staad_data.member_properties[geometry]['warping_constant'])
            input_dict['depth_of_web'] = float(staad_data.member_properties[geometry]['depth_of_web'])
            geometry_model = ArbitraryPolygonProfile.from_staad(input_dict=input_dict, project=project)
        # Create geometry
        if not geometry_model:
            raise NotImplementedError(f'Geometry {geometry} is not defined.')
        else:
            input_dict = dict()
            input_dict['name'] = str(geometry)
            input_dict['geometry_model'] = geometry_model
            geometry_dummy = Geometry.from_staad(input_dict=input_dict, project=project)
            dict_geometry_beam[geometry] = geometry_dummy
            for member in staad_data.member_properties[geometry]['assigned_beam']:
                dict_mem_mat_geo[member]['geo'] = geometry_dummy

    ## MESH ##
    dict_meshnode = dict()
    dict_meshbeam = dict()
    dict_meshplate = dict()
    dict_beam = dict()
    dict_plate = dict()
    connecting_node_2_member = dict()
    connecting_line_2_member = dict()
    # Create mesh-nodes
    for node_id in staad_data.joint_coordinates:
        dict_meshnode[node_id] = MeshNode.from_staad({'coordinates': staad_data.joint_coordinates[node_id],
                                                      'id': int(node_id)}, project)
    # Create mesh-elements for members
    for member_id in staad_data.member_incidences:
        # Create the mesh elements
        dict_meshbeam[member_id] = MeshElement.from_staad(
            {'node_list': [dict_meshnode[staad_data.member_incidences[member_id]['start_node_ID']],
                           dict_meshnode[staad_data.member_incidences[member_id]['end_node_ID']]],
             'id': int(member_id)}, project)
        # Collect the line shapes
        input_dict = dict()
        input_dict['line_beam'] = dict_meshbeam[member_id]
        input_dict['beam_pile_id'] = member_id
        input_dict['material_model'] = dict_mem_mat_geo[member_id]['mat']
        input_dict['geometry_model'] = dict_mem_mat_geo[member_id]['geo']
        dict_beam[member_id] = Lines.from_staad(input_dict=input_dict, project=project)
        if member_id in staad_data.beta_angles:
            dict_beam[member_id].update_local_z_axis(staad_data.beta_angles[member_id])
        if member_id in staad_data.offsets:
            if staad_data.offsets[member_id]['START'] is not None:
                dict_beam[member_id].add_geometry_eccentricity(float(staad_data.offsets[member_id]['START'][0]),
                                                               float(staad_data.offsets[member_id]['START'][1]),
                                                               float(staad_data.offsets[member_id]['START'][2]))
            elif staad_data.offsets[member_id]['START'] is None and staad_data.offsets[member_id]['END'] is not None:
                dict_beam[member_id].add_geometry_eccentricity(float(staad_data.offsets[member_id]['END'][0]),
                                                               float(staad_data.offsets[member_id]['END'][1]),
                                                               float(staad_data.offsets[member_id]['END'][2]))
        connecting_node_2_member[staad_data.member_incidences[member_id]['start_node_ID']] = dict_beam[member_id]
        connecting_node_2_member[staad_data.member_incidences[member_id]['end_node_ID']] = dict_beam[member_id]
        connecting_line_2_member[member_id] = dict_beam[member_id].contour
    # Create mesh-elements for plates
    for plate_id in staad_data.element_incidences_shell:
        # Create the mesh elements
        if not staad_data.element_incidences_shell[plate_id]['node_4']:
            dict_meshplate[plate_id] = MeshElement.from_staad(
                {'node_list': [dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_1']],
                               dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_2']],
                               dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_3']]],
                 'id': int(plate_id)}, project)
        else:
            dict_meshplate[plate_id] = MeshElement.from_staad(
                {'node_list': [dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_1']],
                               dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_2']],
                               dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_3']],
                               dict_meshnode[staad_data.element_incidences_shell[plate_id]['node_4']]],
                 'id': int(plate_id)}, project)
        # Create the surface shapes
        input_dict = dict()
        input_dict['polyline_plate'] = dict_meshplate[plate_id]
        input_dict['plate_id'] = plate_id
        input_dict['material_model'] = dict_mem_mat_geo[plate_id]['mat']
        input_dict['geometry_model'] = dict_mem_mat_geo[plate_id]['geo']
        dict_plate[plate_id] = Surfaces.from_staad(input_dict=input_dict, project=project)
        connecting_node_2_member[staad_data.element_incidences_shell[plate_id]['node_1']] = dict_plate[plate_id]
        connecting_node_2_member[staad_data.element_incidences_shell[plate_id]['node_2']] = dict_plate[plate_id]
        connecting_node_2_member[staad_data.element_incidences_shell[plate_id]['node_3']] = dict_plate[plate_id]
        connecting_node_2_member[staad_data.element_incidences_shell[plate_id]['node_4']] = dict_plate[plate_id]

    ## GROUPS ##
    group_dict = {}
    for key in staad_data.groups['node_groups']:
        name = key
        list_of_nodes = staad_data.groups['node_groups'][key]
        node_list = []
        for node in list_of_nodes:
            mesh_node = (dict_meshnode[f'{node}'])
            node_list.append(mesh_node)
        group_dict[f'{name}'] = {'name': name,
                                 'shapes': node_list}
        group = Group.from_staad(input_dict={'name': name,
                                             'nodes': node_list},
                                 project=project)
    for key in staad_data.groups['shape_groups']:
        name = key
        list_of_shapes = staad_data.groups['shape_groups'][key]
        shape_list = []
        for shape_id in list_of_shapes:
            if shape_id in dict_beam.keys():
                shape_list.append(dict_beam[f'{shape_id}'])
                continue
            elif shape_id in dict_plate.keys():
                shape_list.append(dict_plate[f'{shape_id}'])
                continue
        group_dict[f'{name}'] = {'name': name,
                                 'shapes': shape_list}
        group = Group.from_staad(input_dict={'name': name,
                                             'shapes': shape_list},
                                 project=project)

    ## SUPPORTS ##
    dict_supports = dict()
    dict_plate_node_geo = dict()
    dict_member_node_geo = dict()
    for beam in staad_data.member_incidences:
        node_no_start = staad_data.member_incidences[beam]['start_node_ID']
        dict_member_node_geo.update({node_no_start: beam})
        node_no_end = staad_data.member_incidences[beam]['end_node_ID']
        dict_member_node_geo.update({node_no_end: beam})

    for shell in staad_data.element_incidences_shell:
        dict_plate_node_geo.update({staad_data.element_incidences_shell[shell]['node_1']: shell})
        dict_plate_node_geo.update({staad_data.element_incidences_shell[shell]['node_2']: shell})
        dict_plate_node_geo.update({staad_data.element_incidences_shell[shell]['node_3']: shell})
        dict_plate_node_geo.update({staad_data.element_incidences_shell[shell]['node_4']: shell})

    for support in staad_data.supports:

        # Fixed supports
        if support == 'FIXED BUT':
            for key in staad_data.supports[support]:
                for node_id in staad_data.supports[support][key]['assigned_node']:
                    input_dict = dict()

                    # Check the node to which beam or plate it belongs

                    if node_id in dict_member_node_geo.keys():
                        beam_id = dict_member_node_geo[node_id]
                        if staad_data.member_incidences[beam_id]['start_node_ID'] == node_id:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': dict_beam[beam_id],
                                'shape_geometry': dict_beam[beam_id].contour.node_start}]
                        else:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': dict_beam[beam_id],
                                'shape_geometry': dict_beam[beam_id].contour.node_end}]
                    elif node_id in dict_plate_node_geo.keys():

                        plate_ID = dict_plate_node_geo[node_id]

                        connecting_shape = dict_plate[plate_ID]

                        node_id_coordinates = staad_data.joint_coordinates[node_id]

                        if dict_plate[plate_ID].contour.lines[0].node_start.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[0].node_start}]
                        elif dict_plate[plate_ID].contour.lines[0].node_end.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[0].node_end}]
                        elif dict_plate[plate_ID].contour.lines[1].node_start.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[1].node_start}]
                        elif dict_plate[plate_ID].contour.lines[1].node_end.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[1].node_end}]
                        elif dict_plate[plate_ID].contour.lines[2].node_start.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[2].node_start}]
                        elif dict_plate[plate_ID].contour.lines[2].node_end.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[2].node_end}]
                        elif dict_plate[plate_ID].contour.lines[3].node_start.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[3].node_start}]
                        elif dict_plate[plate_ID].contour.lines[3].node_end.coordinates == node_id_coordinates:
                            input_dict['connecting_items'] = [{
                                'connecting_shape': connecting_shape,
                                'shape_geometry': dict_plate[plate_ID].contour.lines[3].node_end}]

                    d_kx = 1
                    d_ky = 1
                    d_kz = 1
                    d_mx = 1
                    d_my = 1
                    d_mz = 1
                    s_kx = None
                    s_ky = None
                    s_kz = None
                    s_mx = None
                    s_my = None
                    s_mz = None
                    if staad_data.supports[support][key]['KFX'] is not None:
                        if staad_data.supports[support][key]['KFX'] == 0:
                            d_kx = 0
                        else:
                            d_kx = 2
                            s_kx = float(staad_data.supports[support][key]['KFX'])
                    if staad_data.supports[support][key]['KFY'] is not None:
                        if staad_data.supports[support][key]['KFY'] == 0:
                            d_ky = 0
                        else:
                            d_ky = 2
                            s_ky = float(staad_data.supports[support][key]['KFY'])
                    if staad_data.supports[support][key]['KFZ'] is not None:
                        if staad_data.supports[support][key]['KFZ'] == 0:
                            d_kz = 0
                        else:
                            d_kz = 2
                            s_kz = float(staad_data.supports[support][key]['KFZ'])
                    if staad_data.supports[support][key]['KMX'] is not None:
                        if staad_data.supports[support][key]['KMX'] == 0:
                            d_mx = 0
                        else:
                            d_mx = 2
                            s_mx = float(staad_data.supports[support][key]['KMX'])
                    if staad_data.supports[support][key]['KMY'] is not None:
                        if staad_data.supports[support][key]['KMY'] == 0:
                            d_my = 0
                        else:
                            d_my = 2
                            s_my = float(staad_data.supports[support][key]['KMY'])
                    if staad_data.supports[support][key]['KMZ'] is not None:
                        if staad_data.supports[support][key]['KMZ'] == 0:
                            d_mz = 0
                        else:
                            d_mz = 2
                            s_mz = float(staad_data.supports[support][key]['KMZ'])
                    input_dict['degrees_of_freedom'] = [[d_kx, d_ky, d_kz], [d_mx, d_my, d_mz]]
                    input_dict['spring_stiffnesses'] = [[s_kx, s_ky, s_kz], [s_mx, s_my, s_mz]]
                    dict_supports[node_id] = PointSupport.from_staad(input_dict, project)
        else:
            for node_id in staad_data.supports[support]:
                input_dict = dict()

                # Check the node to which beam or plate it belongs
                if node_id in dict_member_node_geo.keys():
                    beam_id = dict_member_node_geo[node_id]
                    if staad_data.member_incidences[beam_id]['start_node_ID'] == node_id:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': dict_beam[beam_id],
                            'shape_geometry': dict_beam[beam_id].contour.node_start}]
                    else:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': dict_beam[beam_id],
                            'shape_geometry': dict_beam[beam_id].contour.node_end}]
                elif node_id in dict_plate_node_geo.keys():

                    plate_ID = dict_plate_node_geo[node_id]

                    connecting_shape = dict_plate[plate_ID]
                    support_node_coordinates = str(staad_data.joint_coordinates[node_id])

                    if str(dict_plate[plate_ID].contour.lines[0].node_start.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[0].node_start}]
                    elif str(dict_plate[plate_ID].contour.lines[0].node_end.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[0].node_end}]
                    elif str(dict_plate[plate_ID].contour.lines[1].node_start.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[1].node_start}]
                    elif str(dict_plate[plate_ID].contour.lines[1].node_end.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[1].node_end}]
                    elif str(dict_plate[plate_ID].contour.lines[2].node_start.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[2].node_start}]
                    elif str(dict_plate[plate_ID].contour.lines[2].node_end.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[2].node_end}]
                    elif str(dict_plate[plate_ID].contour.lines[3].node_start.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[3].node_start}]
                    elif str(dict_plate[plate_ID].contour.lines[3].node_end.coordinates) == support_node_coordinates:
                        input_dict['connecting_items'] = [{
                            'connecting_shape': connecting_shape,
                            'shape_geometry': dict_plate[plate_ID].contour.lines[3].node_end}]

                if support == 'FIXED':
                    input_dict['degrees_of_freedom'] = [[1, 1, 1], [1, 1, 1]]
                    input_dict['spring_stiffnesses'] = [[None, None, None], [None, None, None]]
                    dict_supports[node_id] = PointSupport.from_staad(input_dict, project)
                elif support == 'PINNED':
                    input_dict['degrees_of_freedom'] = [[1, 1, 1], [0, 0, 0]]
                    input_dict['spring_stiffnesses'] = [[None, None, None], [None, None, None]]
                    dict_supports[node_id] = PointSupport.from_staad(input_dict, project)

                else:
                    raise NotImplementedError(f'ERROR: Support {support} can not be implemented.')

    ## LOADS ##
    loadgroups = {}
    loadcases = {}
    repeat_load_counter = 0
    # Create the primary load cases
    for key, value in staad_data.primary_loadcases.items():
        loaditems = value.get('load_items')
        id = int(key)
        name = value.get('load_name')
        loadgroupname = value.get('load_type')
        if (not loadgroups) or (loadgroupname not in loadgroups):
            loadgroups[loadgroupname] = project.create_loadgroup(name=loadgroupname)
        input_loadcase = {'id': int(id), 'name': name, 'loadgroup': loadgroups[loadgroupname]}

        # Dont create load case if its just repeat load in the loadcase
        if len(loaditems) == 1 and 'REPEAT LOAD' in loaditems.keys():
            pass
        else:
            loadcase = LoadCase.from_staad(input_loadcase=input_loadcase, project=project)
            loadcases[id] = loadcase

        for key_item, value_item in loaditems.items():
            if key_item == 'SELFWEIGHT':
                for key_item2, value_item2 in value_item.items():
                    input_dict = {'gravity_factor': -project.gravitational_acceleration,
                                  'model_load_name': name,
                                  'direction': value_item2.get('direction'),
                                  'load_case': loadcase,
                                  'load_value': value_item2.get('factor')}
                    ModelLoad.from_staad(input_dict=input_dict, project=project)
            elif key_item in ['JOINT LOAD', 'SUPPORT DISPLACEMENT LOAD']:
                for key_item2, value_item2 in value_item.items():
                    for id_node in value_item2.get('assigned_members'):
                        id_node_coordinates = staad_data.joint_coordinates[id_node]
                        if key_item == 'JOINT LOAD':
                            load_type = 'force'
                            load_type_moment = 'moment'
                        else:
                            load_type = 'translation'
                            load_type_moment = 'rotation'
                        # check the node belongs to which beam?
                        for beam in staad_data.member_incidences:
                            if id_node in staad_data.member_incidences[beam].values():

                                if staad_data.member_incidences[beam]['start_node_ID'] == id_node:
                                    connecting_items = [{
                                        'connecting_shape': dict_beam[beam],
                                        'shape_geometry': dict_beam[beam].contour.node_start}]
                                    break
                                else:
                                    connecting_items = [{
                                        'connecting_shape': dict_beam[beam],
                                        'shape_geometry': dict_beam[beam].contour.node_end}]
                                break

                        if "connecting_items" not in locals():
                            for shell in staad_data.element_incidences_shell:
                                if id_node in staad_data.element_incidences_shell[shell].values():
                                    for line in dict_plate[shell].contour.lines:
                                        if line.node_start.coordinates == id_node_coordinates:
                                            connecting_items = [{
                                                'connecting_shape': dict_plate[shell],
                                                'shape_geometry': line.node_start}]
                                            break
                                        elif line.node_end.coordinates == id_node_coordinates:
                                            connecting_items = [{
                                                'connecting_shape': dict_plate[shell],
                                                'shape_geometry': line.node_end}]
                                            break

                        if 'FX' in value_item2 and value_item2.get('FX') is not None:
                            input_dict = {'load_type': load_type,
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'X'}, project=project),
                                          'load_value': float(value_item2.get('FX')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            PointLoad.from_staad(input_dict=input_dict, project=project)

                        if 'FY' in value_item2 and value_item2.get('FY') is not None:
                            input_dict = {'load_type': load_type,
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Y'}, project=project),
                                          'load_value': float(value_item2.get('FY')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            PointLoad.from_staad(input_dict=input_dict, project=project)

                        if 'FZ' in value_item2 and value_item2.get('FZ') is not None:
                            input_dict = {'load_type': load_type,
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Z'}, project=project),
                                          'load_value': float(value_item2.get('FZ')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            PointLoad.from_staad(input_dict=input_dict, project=project)

                        if 'MX' in value_item2 and value_item2.get('MX') is not None:
                            input_dict = {'load_type': load_type_moment,
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'X'}, project=project),
                                          'load_value': float(value_item2.get('MX')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            PointLoad.from_staad(input_dict=input_dict, project=project)

                        if 'MY' in value_item2 and value_item2.get('MY') is not None:
                            input_dict = {'load_type': load_type_moment,
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Y'}, project=project),
                                          'load_value': float(value_item2.get('MY')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            PointLoad.from_staad(input_dict=input_dict, project=project)

                        if 'MZ' in value_item2 and value_item2.get('MZ') is not None:
                            input_dict = {'load_type': load_type_moment,
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Z'}, project=project),
                                          'load_value': float(value_item2.get('MZ')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            PointLoad.from_staad(input_dict=input_dict, project=project)

            elif key_item == 'MEMBER LOAD':
                for key_item2, value_item2 in value_item.items():
                    for id_member in value_item2.get('assigned_members'):
                        # Find beam for load
                        for beam in staad_data.member_incidences:
                            if id_member == beam:
                                connecting_items = [{'connecting_shape': dict_beam[beam]}]
                                break
                        if value_item2.get('load_type') == 'uniform_force' and value_item2.get('direction') == 'GX':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'force',
                                              'direction':
                                                  Direction.from_staad(
                                                      input_dict={'direction_def': 'X'}, project=project),
                                              'load_value': float(value_item2.get('force')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_force' and value_item2.get('direction') == 'GY':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'force',
                                              'direction':
                                                  Direction.from_staad(
                                                      input_dict={'direction_def': 'Y'}, project=project),
                                              'load_value': float(value_item2.get('force')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)

                        elif value_item2.get('load_type') == 'uniform_force' and value_item2.get('direction') == 'GZ':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'force',
                                              'direction':
                                                  Direction.from_staad(
                                                      input_dict={'direction_def': 'Z'}, project=project),
                                              'load_value': float(value_item2.get('force')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_force' and value_item2.get('direction') == 'X':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'force',
                                              'direction': dict_beam[beam].contour.get_direction(),
                                              'load_value': float(value_item2.get('force')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_force' and value_item2.get('direction') == 'Y':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'force',
                                              'direction': dict_beam[beam].y_axis_direction(),
                                              'load_value': float(value_item2.get('force')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)

                        elif value_item2.get('load_type') == 'uniform_force' and value_item2.get('direction') == 'Z':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'force',
                                              'direction': dict_beam[beam].z_axis_direction(),
                                              'load_value': float(value_item2.get('force')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)

                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'GX':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'moment',
                                              'direction':
                                                  Direction.from_staad(
                                                      input_dict={'direction_def': 'X'}, project=project),
                                              'load_value': float(value_item2.get('moment')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'GY':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'moment',
                                              'direction':
                                                  Direction.from_staad(
                                                      input_dict={'direction_def': 'Y'}, project=project),
                                              'load_value': float(value_item2.get('moment')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'GZ':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'moment',
                                              'direction':
                                                  Direction.from_staad(
                                                      input_dict={'direction_def': 'Z'}, project=project),
                                              'load_value': float(value_item2.get('moment')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'X':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'moment',
                                              'direction': dict_beam[beam].contour.get_direction(),
                                              'load_value': float(value_item2.get('moment')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'Y':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'moment',
                                              'direction': dict_beam[beam].y_axis_direction(),
                                              'load_value': float(value_item2.get('moment')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)

                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'Z':
                            if not value_item2.get('d1') and not value_item2.get('d2') and not value_item2.get('d3'):
                                input_dict = {'load_type': 'moment',
                                              'direction': dict_beam[beam].z_axis_direction(),
                                              'load_value': float(value_item2.get('moment')),
                                              'load_case': loadcase,
                                              'connecting_items': connecting_items}
                                LineLoad.from_staad(input_dict=input_dict, project=project)
            elif key_item == 'REPEAT LOAD':
                group = {}
                for key_factors, value_factors in value_item.get('factors').items():
                    load_case = loadcases[int(key_factors)]
                    group[load_case] = value_factors
                repeat_load_counter += 1
                input_dict = {'id': id,
                              'name': f'Non Linear Load Combination {repeat_load_counter}',
                              'non_linear_combination': True,
                              'factors': group,
                              'category': None}
                LoadCombination.from_staad(input_dict, project)
            elif key_item == 'ELEMENT LOAD':
                for key_item2, value_item2 in value_item.items():
                    for id_member in value_item2.get('assigned_members'):

                        # Find surface for load
                        for plate in staad_data.element_incidences_shell:
                            if id_member == plate:
                                connecting_items = [{'connecting_shape': dict_plate[plate]}]
                                break
                        if value_item2.get('load_type') == 'pressure_on_full_plate' and \
                                value_item2.get('direction') == 'GX':
                            input_dict = {'load_type': 'force',
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'X'}, project=project),
                                          'load_value': float(value_item2.get('force')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            SurfaceLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'pressure_on_full_plate' and \
                                value_item2.get('direction') == 'GY':
                            input_dict = {'load_type': 'force',
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Y'}, project=project),
                                          'load_value': float(value_item2.get('force')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            SurfaceLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'pressure_on_full_plate' and \
                                value_item2.get('direction') == 'GZ':
                            input_dict = {'load_type': 'force',
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Z'}, project=project),
                                          'load_value': float(value_item2.get('force')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            SurfaceLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'GX':
                            input_dict = {'load_type': 'force',
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'X'}, project=project),
                                          'load_value': float(value_item2.get('moment')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            SurfaceLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'GY':
                            input_dict = {'load_type': 'force',
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Y'}, project=project),
                                          'load_value': float(value_item2.get('moment')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            SurfaceLoad.from_staad(input_dict=input_dict, project=project)
                        elif value_item2.get('load_type') == 'uniform_moment' and value_item2.get('direction') == 'GZ':
                            input_dict = {'load_type': 'force',
                                          'direction':
                                              Direction.from_staad(input_dict={'direction_def': 'Z'}, project=project),
                                          'load_value': float(value_item2.get('moment')),
                                          'load_case': loadcase,
                                          'connecting_items': connecting_items}
                            SurfaceLoad.from_staad(input_dict=input_dict, project=project)

    category = None
    for key, value in staad_data.load_combinations.items():
        id = int(key)
        name = value.get('loadcomb_name')
        group = {}
        for key_factors, value_factors in value.get('factors').items():
            load_case = loadcases[int(key_factors)]
            group[load_case] = value_factors
        # Find category
        for envelope_name, envelope_value in staad_data.envelopes.items():
            if key in envelope_value['combo_list']:
                category = envelope_name
        input_dict = {'id': id,
                      'name': name,
                      'factors': group,
                      'category': category}
        LoadCombination.from_staad(input_dict, project)


### ===================================================================================================================
###   5. Run analysis in STAAD
### ===================================================================================================================

def _fem_run_model_staad(project: 'Project', std_input_file: Union[str, Path], folder: str = None,
                         location_exe_file: Union[str, Path] = None):
    """
    Function to run analysis in STAAD from std file in command console (silenced).

    .. note:: STAAD pro connect edition is expected to be installed in the default location.

    Input:
        - project (obj): Project object containing collections of fem objects an project variables.
        - std_inputfile (str): Name of the std file to run analysis, for example 'ref_model'. Suffix is not required.
          Alternative (Path): The std-file can be provided as path.
        - folder (Path or str): Folder location where to save the model. Default value is None in
          which case the file is saved in the working folder (the folder of the main script). When the std_inputfile is
          provided input for the folder is not required.
        - location_exe_file (Path or str): Location of SProStaad.exe. Default value is None, in which case the STAAD
          exe-file is expected to be in the default locations.

    Output:
        - The analysed STAAD model is saved to the folder.
    """
    # Retrieve the inputfile
    if isinstance(std_input_file, str):
        if std_input_file.endswith('.std'):
            file = std_input_file
        else:
            file = std_input_file + '.std'

        # Select the folder in which the inputfile is located, if not specified working folder is selected
        if not folder:
            folder = Path.cwd()
        elif isinstance(folder, str):
            folder = Path(folder)

        # Create the complete path
        std_input_file = folder / file

    # Check inputfile is present
    if not std_input_file.exists():
        project.write_log(
            f"ERROR: Can't find the provided input file for STAAD in std-format in '{std_input_file.as_posix()}'.")
        return False

    # Check the location of the exe file
    if location_exe_file is not None:

        # Get the specified path to use STAAD
        if isinstance(location_exe_file, str):
            if not location_exe_file.endswith('.exe'):
                location_exe_file += '.exe'
            # Convert to path
            path_staad = Path(location_exe_file)
        else:
            path_staad = location_exe_file

        # Check if file is present
        if not path_staad.exists():
            project.write_log(
                f"WARNING: The provided location of the STAAD exe file '{path_staad.as_posix()}' "
                f"in input for 'location_exe_file' is not correct.")
            return False

        # Check if the provided path contains reference to the valid STAAD version
        if not ('SProV8i SS6' in path_staad or 'STAAD.Pro CONNECT Edition' in path_staad):
            project.write_log(
                f"WARNING: FEM package is written based on different STAAD version: "
                f"see getting_started_fem_model_to_staad")

    else:
        # Get the default path to use STAAD

        default_paths = [
            Path(r"C:\Program Files (x86)\SProV8i SS6\STAAD\SProStaad\SProStaad.exe"),
            Path(r"C:\Program Files\Bentley\Engineering\STAAD.Pro CONNECT Edition\STAAD\SProStaad\SProStaad.exe")]
        path_staad = None
        for default_path in default_paths:
            if default_path.exists():
                path_staad = default_path
                break
        if path_staad is None:
            project.write_log(
                f"WARNING: Provide the location of the STAAD exe file in input for 'location_exe_file'.")
            return False

    # Send the commands to the command console
    cmd = rf'{path_staad} STAAD {std_input_file} /s'
    subprocess.Popen(cmd).communicate()
    return True

### ===================================================================================================================
###   6. Get results from STAAD
### ===================================================================================================================

class GetResults(RawStdFile):
    """
    Class to get internal forces from the STAAD-model, inherits from RawStdFile class to use .std as objects.

    .. note:: STAAD pro connect edition is expected to be installed in the default location.
    """

    def __init__(self, project: 'Project', std_file: Path):
        """
        Input:
            - project (Obj): Project object containing collections of fem objects an project variables.
            - std_file (Path): Path of the .std file where to extract the results from.

        Output:
            - Open staad-file on desktop and transfer results to dictionary in this class.
        """
        super().__init__(std_file)
        self.std_file = std_file
        self.project = project

        # Check if 3rd party modules are available
        if not comtypes_use:
            self.project(
                "ERROR: Cannot make connection to STAAD API to get results. Python modules 'comtypes' is missing.")
            return

        # Check if Staad is open, if not run _open_staad_file() method
        # Connect to OpenSTAAD and prepare methods which will be used
        try:
            self._connect_openstaad()
            time.sleep(15)
            project.write_log(
                f"WARNING: STAAD is opening. Giving STAAD 15 seconds to open so that it is in a suitable state to open "
                f"and retrieve results.")
        except OSError:
            self.staad_opened = False
            self._open_staad_file()

        # Read .std file and store in dictionary
        self.read_file()
        _fem_staad_to_fem(self.project, self.std_file)

    def _open_staad_file(self):
        """
        Method to open STAAD, and activate methods for OpenSTAAD, tries up until Staad is opened.

        .. note:: This method is called while instantiating the class.

        Input:
            - No input required.

        Output:
            - Opens STAAD.
            - Connection is made to OpenSTAAD.
        """
        if self.staad_opened:
            try:
                self._connect_openstaad()
            except:
                time.sleep(0.01)
                self._open_staad_file()
        else:
            os.startfile(self.std_file)
            self.staad_opened = True
            self._open_staad_file()

    def _connect_openstaad(self):
        """ Open STAAD. """
        self.com_object = comtypes.client.GetActiveObject("StaadPro.OpenSTAAD")
        self.output = self.com_object.Output
        self.output._FlagAsMethod("GetMemberEndForces")
        self.output._FlagAsMethod("GetSupportReactions")
        self.output._FlagAsMethod("GetNodeDisplacements")

    @staticmethod
    def _make_safe_array(size):
        """ Method to create safe array as input for OpenStAAD API (provided by Bentley). """
        return comtypes.automation._midlSAFEARRAY(ctypes.c_double).create([0] * size)

    @staticmethod
    def _make_variant_vt_ref(obj, var_type):
        """ Method to create right type of array for OpenSTAAD API (provided by Bentley).
        Make VARIANT a VT_BYREF by union with original var_type. """
        var = comtypes.automation.VARIANT()
        var._.c_void_p = ctypes.addressof(obj)
        var.vt = var_type | comtypes.automation.VT_BYREF
        return var


class GetInternalForces(GetResults):
    """
    Class to get internal forces from the STAAD-model, inherits from RawStdFile class to use .std as objects.

    .. note:: STAAD pro connect edition is expected to be installed in the default location.
    """

    def __init__(self, project: 'Project', std_file: Path):
        """
        Input:
            - project (Obj): Project object containing collections of fem objects an project variables.
            - std_file (Path): Name of the path of the .std file where you want the results from

        Output:
            - Open staad-file on desktop and transfer results for internal force to dictionary in this class.
        """
        super().__init__(project, std_file)
        self.members_internal_forces_dict = {}
        self.mesh_node_object_dict = {}
        self.load_combination_case_dict = {}
        self.member_dict = {}
        self.element_force_models = []
        self.software = "staad"
        self._get_internal_forces()

    def _get_internal_forces(self):
        """
        Method of 'GetInternalForces' to prepare the input for making the API call and put results in dictionary.

        Input:
            - No input required.

        Output:
            - self.members_internal_forces_list (dict): {member_id : member_id, node_nr: node_nr,
            load_case_id: load_case_id, internal_forces:internal_forces,
            internal_force_specific:internal_force_specific}
        """
        node_1 = 0
        node_2 = 1
        nodes = [node_1, node_2]

        # Join load_cases together in one dictionary
        self.load_cases = {**self.primary_loadcases, **self.load_combinations}
        members_internal_forces = {}
        i = 0

        # Perform the API call
        for member_id, member_nodes in self.member_incidences.items():
            for node in nodes:
                for load_case_id, load_properties in self.load_cases.items():
                    member_end_forces = self._create_api_call(int(member_id), int(node), int(load_case_id))
                    members_internal_forces[i] = {'member_id': member_id,
                                                  'node_nr': node,
                                                  'load_case_id': load_case_id,
                                                  "fx": member_end_forces[0],
                                                  "fy": member_end_forces[1],
                                                  "fz": member_end_forces[2],
                                                  'mx': member_end_forces[3],
                                                  'my': member_end_forces[4],
                                                  'mz': member_end_forces[5]
                                                  }
                    i += 1
                    self.members_internal_forces_dict.update(members_internal_forces)
        self._create_internal_force_fem_object()

    def _create_api_call(self, member_id: int, node_nr: int, load_case_id: int) -> List:
        """
        Method of 'GetInternalForces' to make the API call.

        Input:
            - member_id (int): Member ID derived from .std model objects.
            - node_nr (int): Node of member.
            - load_case_id(int): load case ID derived from .std model objects.

        Output:
            - Returns the member end forces as a list of end forces sorted on [fx, fy, fz, mx, my, mz].
        """
        # The output inputs need to be stored in a C++ array, these methods are used to get access to create this array
        member_end_forces_safe_array = self._make_safe_array(6)
        member_end_forces = self._make_variant_vt_ref(member_end_forces_safe_array,
                                                      comtypes.automation.VT_ARRAY | comtypes.automation.VT_R8)

        # This calls a function to get internal forces from STAAD
        self.output.GetMemberEndForces(member_id, node_nr, load_case_id, member_end_forces)
        return member_end_forces[0]

    def _create_internal_force_fem_object(self):
        """
        Method of 'GetInternalForces' to create internal force objects in RHDHV fem-schema.
        """

        self._create_element_force_models()
        self._create_mesh_nodes_dictionary()
        self._create_load_combination_case_dictionary()
        self._create_member_dictionary()

        for keys, member_internal_forces in self.members_internal_forces_dict.items():
            member_dict = self.member_incidences[member_internal_forces['member_id']]
            member = self.member_dict[int(member_internal_forces['member_id'])]
            load = self.load_combination_case_dict[int(member_internal_forces['load_case_id'])]
            node_nr = member_internal_forces['node_nr']
            if node_nr == 0:
                node_id = int(member_dict["start_node_ID"])
                self._get_shape_results(load, member, member_internal_forces, node_id)
            if node_nr == 1:
                node_id = int(member_dict["end_node_ID"])
                self._get_shape_results(load, member, member_internal_forces, node_id)

    def _get_shape_results(self, load_object: Union['LoadCase', 'LoadCombination'], member: 'Shapes',
                           member_internal_forces: dict, node_id: int):
        """
        Method of 'GetInternalForces' to get shape results from 'ShapeResults' class

        Input:
            - load_object (obj): LoadCase or LoadCombination
            - member (obj): Shapes
            - member_internal_forces (dict): internal force dictionary

        Output:
            - objects are created in project.collections.shape_results
        """

        result_dictionaries = self._create_result_dictionary(node_id, member_internal_forces)
        for index, result_dictionary in enumerate(result_dictionaries):
            self.project.create_shape_result(member, [[self.element_force_models[index], load_object, self.software,
                                                       result_dictionary]])

    def _create_element_force_models(self):
        """
        Method of 'GetInternalForces' to get 'ElementForceOutputItem' object.
        """
        element_force_model_N = self.project.create_element_force_output_item(theoretical_formulation='translation',
                                                                              output_type='total', operation='local', component='x')
        element_force_model_V_y = self.project.create_element_force_output_item(theoretical_formulation='translation',
                                                                                output_type='total', operation='local', component='y')
        element_force_model_V_z = self.project.create_element_force_output_item(theoretical_formulation='translation',
                                                                                output_type='total', operation='local', component='z')
        element_force_model_M_x = self.project.create_element_force_output_item(theoretical_formulation='rotation',
                                                                                output_type='total', operation='local', component='x')
        element_force_model_M_y = self.project.create_element_force_output_item(theoretical_formulation='rotation',
                                                                                output_type='total', operation='local', component='y')
        element_force_model_M_z = self.project.create_element_force_output_item(theoretical_formulation='rotation',
                                                                                output_type='total', operation='local', component='z')

        self.element_force_models = [element_force_model_N, element_force_model_V_y, element_force_model_V_z,
                                     element_force_model_M_x, element_force_model_M_y,
                                     element_force_model_M_z]

    def _create_result_dictionary(self, mesh_node_id: int, member_internal_forces: dict) -> List:
        """
        Method of 'GetInternalForces' to create the results dictionary based on the "ResultsDictionary" class

        Input:
            - mesh_node_id (str): ID of mesh_node derived from internal force dictionary
            - member_internal_forces (dict): dictionary of internal forces
            - mesh_node_object_dictionary(dict): dictionary with ID as key and mesh node object as value

        Output:
            - result_dictionary (list): list of Results Dictionary items
        """

        mesh_node = self.mesh_node_object_dict[mesh_node_id]
        result_dictionary = [self.project.create_result_dictionary([mesh_node, member_internal_forces['fx']]),
                             self.project.create_result_dictionary([mesh_node, member_internal_forces['fy']]),
                             self.project.create_result_dictionary([mesh_node, member_internal_forces['fz']]),
                             self.project.create_result_dictionary([mesh_node, member_internal_forces['mx']]),
                             self.project.create_result_dictionary([mesh_node, member_internal_forces['my']]),
                             self.project.create_result_dictionary([mesh_node, member_internal_forces['mz']])]
        return result_dictionary

    def _create_mesh_nodes_dictionary(self):
        """
        Method of 'GetInternalForces' to create a dictionary of the mesh_node objects of the project.collections and
        the mesh_node_id
        """

        for mesh_node in self.project.collections.mesh_nodes:
            self.mesh_node_object_dict[mesh_node.id] = mesh_node

    def _create_load_combination_case_dictionary(self):
        """
        Method of 'GetInternalForces' to create a dictionary of the load_case and load_combination objects of the
        project.collections and the load id

        Input:
            - No input required.

        Output:
            - load_combination_case_object_dictionary(dict) : {load_case/load_combination.id:load_object}
        """

        for load_case in self.project.collections.loadcases:
            self.load_combination_case_dict[load_case.id] = load_case

        for load_comb in self.project.collections.loadcombinations:
            self.load_combination_case_dict[load_comb.id] = load_comb

    def _create_member_dictionary(self):
        """
          Method of 'GetInternalForces' to create a dictionary of the beam/pile members objects of the
          project.collections and the member id
        """

        for member in self.project.collections.shapes:
            if 'Beam/Pile' in member.name:
                self.member_dict[member.mesh.elements[0].id] = member


class GetReactionForces(GetResults):
    """
    Class to get reaction forces from the STAAD-model, inherits from RawStdFile class to use .std as objects.

    .. note:: STAAD pro connect edition is expected to be installed in the default location.
    """

    def __init__(self, project: 'Project', std_file: Path):
        """
        Input:
            - project (Obj): Project object containing collections of fem objects an project variables.
            - std_file (Path): Name of the path of the .std file where you want the results from

        Output:
            - Open staad-file on desktop and transfer results for reaction force to dictionary in this class.
        """
        super().__init__(project, std_file)
        self.reaction_forces_dict = {}
        self.mesh_node_object_dict = {}
        self.load_combination_case_dict = {}
        self.support_dict = {}
        self.reaction_force_models = []
        self.software = "staad"
        self._get_reaction_forces()

    def _create_api_call(self, node_nr: int, load_case_id: int) -> List:
        """
        Method of 'GetReactionForces' to make the API call.

        Input:
            - node_nr (int): Node of member.
            - load_case_id(int): load case ID derived from .std model objects.

        Output:
            - Returns the support reaction forces as a list of reaction forces sorted on [fx, fy, fz, mx, my, mz].
        """
        # The output inputs need to be stored in a C++ array, these methods are used to get access to create this array
        reaction_forces_safe_array = self._make_safe_array(6)
        reaction_forces = self._make_variant_vt_ref(reaction_forces_safe_array,
                                                    comtypes.automation.VT_ARRAY | comtypes.automation.VT_R8)

        # This calls a function to get internal forces from STAAD
        self.output.GetSupportReactions(node_nr, load_case_id, reaction_forces)
        return reaction_forces[0]

    def _get_reaction_forces(self):
        """
        Method of 'GetReactionForces' to prepare the input for making the API call and put results in dictionary.

        Input:
            - No input required.

        Output:
            - self.support_reaction_forces_list (dict): {node_nr: node_nr,
            load_case_id: load_case_id, reaction_forces:reaction_forces}
        """

        # Join load_cases together in one dictionary
        self.load_cases = {**self.primary_loadcases, **self.load_combinations}
        support_reaction_forces = {}
        nodes = []
        for key in self.supports:
            if key == "FIXED BUT":
                for value in self.supports[key].values():
                    nodes = nodes + value['assigned_node']

            else:
                nodes = nodes + self.supports[key]
        # Perform the API call
        i = 0
        for node in nodes:
            for loadcase_id in self.load_cases:
                reaction_forces = self._reaction_forces_conversion(self._create_api_call(int(node), int(loadcase_id)))
                support_reaction_forces[i] = {'node_nr': node,
                                              'load_case_id': loadcase_id,
                                              "fx": reaction_forces[0],
                                              "fy": reaction_forces[1],
                                              "fz": reaction_forces[2],
                                              'mx': reaction_forces[3],
                                              'my': reaction_forces[4],
                                              'mz': reaction_forces[5]
                                              }
                i += 1

                self.reaction_forces_dict.update(support_reaction_forces)
        self._create_reaction_force_fem_object()

    def _create_reaction_force_fem_object(self):
        """
        Method of 'GetReactionForces' to create reaction force objects in RHDHV fem-schema.
        """

        self._create_reaction_force_models()
        self._create_mesh_nodes_dictionary()
        self._create_load_combination_case_dictionary()

        for keys, support_reaction_forces in self.reaction_forces_dict.items():
            load = self.load_combination_case_dict[int(support_reaction_forces['load_case_id'])]
            node_nr = support_reaction_forces['node_nr']
            for support in self.project.collections.supports:
                for connecting_shapes in support.connecting_shapes:
                    if self.mesh_node_object_dict[int(node_nr)].coordinates == connecting_shapes[
                        'shape_geometry'].coordinates:
                        self._get_support_results(load, support, support_reaction_forces, int(node_nr))
                        break

    def _get_support_results(self, load_object: Union['LoadCase', 'LoadCombination'], support: 'Supports',
                             support_reaction_forces: dict, node_id: int):
        """
        Method of 'GetReactionForces' to get support results from 'SupportResults' class

        Input:
            - load_object (obj): LoadCase or LoadCombination
            - support (obj): Supports
            - support_reaction_forces (dict): reaction force dictionary

        Output:
            - objects are created in project.collections.support_results
        """
        result_dictionaries = self._create_result_dictionary(node_id, support_reaction_forces)
        for index, result_dictionary in enumerate(result_dictionaries):
            self.project.create_support_result(support, [[self.reaction_force_models[index], load_object, self.software,
                                                          result_dictionary]])

    def _create_reaction_force_models(self):
        """
        Method of 'GetReactionForces' to get 'ForceOutputItem' object.
        """

        reaction_force_model_N = self.project.create_force_output_item(theoretical_formulation='translation',
                                                                       output_type='reaction', operation='global', component='x')
        reaction_force_model_V_y = self.project.create_force_output_item(theoretical_formulation='translation',
                                                                         output_type='reaction', operation='global', component='y')
        reaction_force_model_V_z = self.project.create_force_output_item(theoretical_formulation='translation',
                                                                         output_type='reaction', operation='global', component='z')
        reaction_force_model_M_x = self.project.create_force_output_item(theoretical_formulation='rotation',
                                                                         output_type='reaction', operation='global', component='x')
        reaction_force_model_M_y = self.project.create_force_output_item(theoretical_formulation='rotation',
                                                                         output_type='reaction', operation='global', component='y')
        reaction_force_model_M_z = self.project.create_force_output_item(theoretical_formulation='rotation',
                                                                         output_type='reaction', operation='global', component='z')
        self.reaction_force_models = [reaction_force_model_N, reaction_force_model_V_y, reaction_force_model_V_z,
                                      reaction_force_model_M_x, reaction_force_model_M_y,
                                      reaction_force_model_M_z]

    def _create_result_dictionary(self, mesh_node_id: int, support_reaction_forces: dict) -> List:
        """
        Method of 'GetReactionForces' to create the results dictionary based on the "ResultsDictionary" class

        Input:
            - mesh_node_id (str): ID of mesh_node derived from reaction force dictionary
            - reaction_forces (dict): dictionary of reaction forces
            - mesh_node_object_dictionary(dict): dictionary with ID as key and mesh node object as value

        Output:
            - result_dictionary (list): list of Results Dictionary items
        """

        mesh_node = self.mesh_node_object_dict[mesh_node_id]
        result_dictionary = [self.project.create_result_dictionary([mesh_node, support_reaction_forces['fx']]),
                             self.project.create_result_dictionary([mesh_node, support_reaction_forces['fy']]),
                             self.project.create_result_dictionary([mesh_node, support_reaction_forces['fz']]),
                             self.project.create_result_dictionary([mesh_node, support_reaction_forces['mx']]),
                             self.project.create_result_dictionary([mesh_node, support_reaction_forces['my']]),
                             self.project.create_result_dictionary([mesh_node, support_reaction_forces['mz']])]
        return result_dictionary

    def _create_mesh_nodes_dictionary(self):
        """
        Method of 'GetReactionForces' to create a dictionary of the mesh_node objects of the project.collections and
        the mesh_node_id
        """

        for mesh_node in self.project.collections.mesh_nodes:
            self.mesh_node_object_dict[mesh_node.id] = mesh_node

    def _create_load_combination_case_dictionary(self):
        """
        Method of 'GetReactionForces' to create a dictionary of the load_case and load_combination objects of the
        project.collections and the load id

        Input:
            - No input required.

        Output:
            - load_combination_case_object_dictionary(dict) : {load_case/load_combination.id:load_object}
        """

        for load_case in self.project.collections.loadcases:
            self.load_combination_case_dict[load_case.id] = load_case

        for load_comb in self.project.collections.loadcombinations:
            self.load_combination_case_dict[load_comb.id] = load_comb

    def _reaction_forces_conversion(self, reaction_forces: list):
        """
        Methof of 'GetReactionForces' to convert the direction of reaction forces.

        Input:
        - a list of reaction forces which get from staad model [fx, fy, fz, mx, my, mz].

        Output:
        - a list of converted reaction forces [fx, fy, fz, mx, my, mz] following the defaut direction (Z) in FEM schema.
        """

        if self.direction['direction'] == "Z":
            return reaction_forces
        elif self.direction['direction'] == "Y":
            # convert reaction forces
            return [reaction_forces[0], -1 * reaction_forces[2], reaction_forces[1], reaction_forces[3],
                    -1 * reaction_forces[5], reaction_forces[4]]


class GetDisplacements(GetResults):
    """
    Class to get displacements from the STAAD-model, inherits from RawStdFile class to use .std as objects.

    .. note:: STAAD pro connect edition is expected to be installed in the default location.
    """

    def __init__(self, project: 'Project', std_file: Path):
        """
        Input:
            - project (Obj): Project object containing collections of fem objects an project variables.
            - std_file (Path): Name of the path of the .std file where you want the results from

        Output:
            - Open staad-file on desktop and transfer results for displacement to dictionary in this class.
        """
        super().__init__(project, std_file)
        self.members_displacements_dict = {}
        self.mesh_node_object_dict = {}
        self.member_dict = {}
        self.load_combination_case_dict = {}
        self.displacement_models = []
        self.software = "staad"
        self._get_displacements()

    def _get_displacements(self):
        """
        Method of 'GetDisplacements' to prepare the input for making the API call and put results in dictionary.

        Input:
            - No input required.

        Output:
            - self.members_displacements_list (dict): {member_id : member_id, node_nr: node_nr,
            load_case_id: load_case_id, displacements:displacements,
            displacement_specific:displacement_specific}
        """
        node_1 = 0
        node_2 = 1
        nodes = [node_1, node_2]

        # Join load_cases together in one dictionary
        self.load_cases = {**self.primary_loadcases, **self.load_combinations}
        members_displacements = {}
        i = 0

        # Perform the API call
        for member_id, member_nodes in self.member_incidences.items():
            for node in nodes:
                for load_case_id, load_properties in self.load_cases.items():
                    if node == 0:
                        node_id = self.member_incidences[member_id]['start_node_ID']
                    elif node == 1:
                        node_id = self.member_incidences[member_id]['end_node_ID']
                    node_displacement = self._create_api_call(int(node_id), int(load_case_id))
                    members_displacements[i] = {'member_id': member_id,
                                                'node_nr': node,
                                                'load_case_id': load_case_id,
                                                'dx': node_displacement[0],
                                                'dy': node_displacement[1],
                                                'dz': node_displacement[2],
                                                'rx': node_displacement[3],
                                                'ry': node_displacement[4],
                                                'rz': node_displacement[5]
                                                }
                    i += 1
                    self.members_displacements_dict.update(members_displacements)
        self._create_displacement_fem_object()

    def _create_api_call(self, node_id: int, load_case_id: int) -> List:
        """
        Method of 'GetDisplacements' to make the API call.

        Input:
            - node_id (int): Node of member.
            - load_case_id(int): load case ID derived from .std model objects.

        Output:
            - Returns the node displacement as a list of displacements sorted on [dx, dy, dz, rx, ry, rz].
        """
        # The output inputs need to be stored in a C++ array, these methods are used to get access to create this array
        node_displacements_safe_array = self._make_safe_array(6)
        node_displacements = self._make_variant_vt_ref(node_displacements_safe_array,
                                                       comtypes.automation.VT_ARRAY | comtypes.automation.VT_R8)

        # This calls a function to get displacements from STAAD
        self.output.GetNodeDisplacements(node_id, load_case_id, node_displacements)
        return node_displacements[0]

    def _create_displacement_fem_object(self):
        """
        Method of 'GetDisplacements' to create displacement objects in RHDHV fem-schema.
        """
        self._create_displacement_models()
        self._create_mesh_nodes_dictionary()
        self._create_load_combination_case_dictionary()
        self._create_member_dictionary()

        for keys, member_displacements in self.members_displacements_dict.items():
            member_dict = self.member_incidences[member_displacements['member_id']]
            member = self.member_dict[int(member_displacements['member_id'])]
            load = self.load_combination_case_dict[int(member_displacements['load_case_id'])]
            node_nr = member_displacements['node_nr']
            if node_nr == 0:
                node_id = int(member_dict["start_node_ID"])
                self._get_shape_results(load, member, member_displacements, node_id)
            if node_nr == 1:
                node_id = int(member_dict["end_node_ID"])
                self._get_shape_results(load, member, member_displacements, node_id)

    def _get_shape_results(self, load_object: Union['LoadCase', 'LoadCombination'], member: 'Shapes',
                           member_displacements: dict, node_id: int):
        """
        Method of 'GetDisplacements' to get shape results from 'ShapeResults' class

        Input:
            - load_object (obj): LoadCase or LoadCombination
            - member (obj): Shapes
            - member_displacements (dict): displacement dictionary

        Output:
            - objects are created in project.collections.shape_results
        """

        result_dictionaries = self._create_result_dictionary(node_id, member_displacements)
        for index, result_dictionary in enumerate(result_dictionaries):
            self.project.create_shape_result(member, [[self.displacement_models[index], load_object, self.software,
                                                       result_dictionary]])

    def _create_result_dictionary(self, mesh_node_id: int, member_displacements: dict) -> List:
        """
        Method of 'GetDisplacements' to create the results dictionary based on the "ResultsDictionary" class

        Input:
            - mesh_node_id (str): ID of mesh_node derived from displacement dictionary
            - member_displacements (dict): dictionary of displacements
            - mesh_node_object_dictionary(dict): dictionary with ID as key and mesh node object as value

        Output:
            - result_dictionary (list): list of Results Dictionary items
        """

        mesh_node = self.mesh_node_object_dict[mesh_node_id]
        if self.direction == 'z':
            result_dictionary = [self.project.create_result_dictionary([mesh_node, member_displacements['dx']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['dy']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['dz']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['rx']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['ry']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['rz']])]
        else:
            result_dictionary = [self.project.create_result_dictionary([mesh_node, member_displacements['dx']]),
                                 self.project.create_result_dictionary([mesh_node, -member_displacements['dz']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['dy']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['rx']]),
                                 self.project.create_result_dictionary([mesh_node, -member_displacements['rz']]),
                                 self.project.create_result_dictionary([mesh_node, member_displacements['ry']])]
        return result_dictionary

    def _create_displacement_models(self):
        """
        Method of 'GetDisplacements' to get 'DisplacementOutputItem' object.
        """

        dx = self.project.create_displacement_output_item(theoretical_formulation='translation',
                                                          output_type='total', operation='global', component='x')
        dy = self.project.create_displacement_output_item(theoretical_formulation='translation',
                                                          output_type='total', operation='global', component='y')
        dz = self.project.create_displacement_output_item(theoretical_formulation='translation',
                                                          output_type='total', operation='global', component='z')
        rx = self.project.create_displacement_output_item(theoretical_formulation='rotation',
                                                          output_type='total', operation='global', component='x')
        ry = self.project.create_displacement_output_item(theoretical_formulation='rotation',
                                                          output_type='total', operation='global', component='y')
        rz = self.project.create_displacement_output_item(theoretical_formulation='rotation',
                                                          output_type='total', operation='global', component='z')

        self.displacement_models = [dx, dy, dz, rx, ry, rz]

    def _create_mesh_nodes_dictionary(self):
        """
        Method of 'GetDisplacements' to create a dictionary of the mesh_node objects of the project.collections and
        the mesh_node_id
        """

        for mesh_node in self.project.collections.mesh_nodes:
            self.mesh_node_object_dict[mesh_node.id] = mesh_node

    def _create_load_combination_case_dictionary(self):
        """
        Method of 'GetDisplacements' to create a dictionary of the load_case and load_combination objects of the
        project.collections and the load id

        Input:
            - No input required.

        Output:
            - load_combination_case_object_dictionary(dict) : {load_case/load_combination.id:load_object}
        """

        for load_case in self.project.collections.loadcases:
            self.load_combination_case_dict[load_case.id] = load_case

        for load_comb in self.project.collections.loadcombinations:
            self.load_combination_case_dict[load_comb.id] = load_comb

    def _create_member_dictionary(self):
        """
          Method of 'GetDisplacements' to create a dictionary of the beam/pile members objects of the
          project.collections and the member id
        """

        for member in self.project.collections.shapes:
            if 'Beam/Pile' in member.name:
                self.member_dict[member.mesh.elements[0].id] = member

# ### ===================================================================================================================
###   7. End of script
### ===================================================================================================================
