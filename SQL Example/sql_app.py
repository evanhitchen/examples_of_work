import sqlite3
from sqlite3 import Error
import os

cwd = os.getcwd()


def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return conn


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute("PRAGMA foreign_keys=ON")
        c.execute(create_table_sql)
    except Error as e:
        print(e)


def creation_of_db():
    """ create a database SQLite database ready for inspection storage
    :return: SQL Database created locally called MOD_inspection_database
    """
    database = cwd + r"/MOD_inspection_database.db"

    sql_create_projects_table = """ CREATE TABLE IF NOT EXISTS projects (
                                        project_id text PRIMARY KEY,
                                        project_name text NOT NULL,
                                        project_manager text
                                    ); """

    sql_create_assets_table = """CREATE TABLE IF NOT EXISTS assets (
                                        asset_id text PRIMARY KEY,
                                        project_id text,
                                        establishment_name text NOT NULL,
                                        owner text NOT NULL,
                                        structure_type text, 
                                        description_of_use text,
                                        height text,                                       
                                        location_of_structure text,                                        
                                        no_of_structures text,
                                        nearest_building text,
                                        access text,
                                        fitted_access text,
                                        climbing_facilities text,                                        
                                        inspection_frequency text,
                                        map_reference text,
                                        FOREIGN KEY (project_id) REFERENCES projects (project_id)
                                    );"""

    sql_create_inspections_table = """CREATE TABLE IF NOT EXISTS inspections (
                                        inspection_id text PRIMARY KEY,
                                        project_id text,
                                        asset_id text,                                        
                                        GA_photo text,                                        
                                        good_condition text,                                        
                                        note text,
                                        inspector_name text,
                                        qualification text,
                                        date_inspected text,                                        
                                        expiry_date text,                                        
                                        FOREIGN KEY (project_id) REFERENCES projects (project_id),
                                        FOREIGN KEY (asset_id) REFERENCES assets (asset_id)
                                    );"""

    sql_create_defects_table = """CREATE TABLE IF NOT EXISTS defects (
                                    defect_id integer PRIMARY KEY AUTOINCREMENT,
                                    asset_id text,
                                    inspection_id text,
                                    project_id text,
                                    element text NOT NULL,
                                    defect text NOT NULL,
                                    remedial text,
                                    cost text,
                                    urgency text NOT NULL,                                    
                                    FOREIGN KEY (asset_id) REFERENCES assets (asset_id),
                                    FOREIGN KEY (inspection_id) REFERENCES inspections (inspection_id),
                                    FOREIGN KEY (project_id) REFERENCES projects (project_id)
                                );"""

    sql_create_photo_table = """CREATE TABLE IF NOT EXISTS photos (
                                        photo_id integer PRIMARY KEY AUTOINCREMENT,
                                        defect_id text,
                                        photo blob,
                                        caption text,
                                        FOREIGN KEY (defect_id) REFERENCES defects (defect_id)
                                    );"""

    # create a database connection
    conn = create_connection(database)

    # create tables
    if conn is not None:
        # create projects table
        create_table(conn, sql_create_projects_table)

        # create assets table
        create_table(conn, sql_create_assets_table)

        # create inspections table
        create_table(conn, sql_create_inspections_table)

        # create defects table
        create_table(conn, sql_create_defects_table)

        # create photo table
        create_table(conn, sql_create_photo_table)
    else:
        print("Error! cannot create the database connection.")


def create_project(database, project):
    """
    Create a new project into the projects table
    :param database:
    :param project:
    :return: project id
    """
    conn = create_connection(database)
    with conn:
        sql = ''' INSERT INTO projects(project_id, project_name, project_manager)
                  VALUES(?,?,?) '''
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute(sql, project)
        conn.commit()
        return cur.lastrowid


def update_project(database, project):
    """
    Update project in the projects table
    :param database:
    :param project:
    :return: updated project
    """
    try:
        conn = create_connection(database)
        cur = conn.cursor()
        sql_update_query = """UPDATE projects SET project_name = ?, project_manager = ? WHERE project_id = ?"""
        cur.execute(sql_update_query, project)
        conn.commit()
        print(f"Project {project[0]} Updated successfully")
        cur.close()

    except sqlite3.Error as error:
        print("Failed to update database", error)
    finally:
        if conn:
            conn.close()


def create_asset(database, asset):
    """
    Create a new asset into the assets table
    :param database:
    :param asset:
    :return: updated asset
    """
    conn = create_connection(database)
    with conn:
        sql = ''' INSERT INTO assets(asset_id, project_id, establishment_name, owner, structure_type, 
                  description_of_use, height, location_of_structure, no_of_structures, 
                  nearest_building, access, fitted_access, climbing_facilities, inspection_frequency, map_reference)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute(sql, asset)
        conn.commit()
        return cur.lastrowid


def update_asset(database, asset):
    """
    Update asset in the assets table
    :param database:
    :param asset:
    :return: updated asset
    """
    try:
        conn = create_connection(database)
        cur = conn.cursor()
        sql_update_query = """UPDATE assets SET project_id = ?, establishment_name = ?, owner = ?, structure_type = ?, 
                  description_of_use = ?, height = ?, location_of_structure = ?, no_of_structures = ?, 
                  nearest_building = ?, access = ?, fitted_access = ?, climbing_facilities = ?, 
                  inspection_frequency = ?, map_reference = ? WHERE asset_id = ?"""
        cur.execute(sql_update_query, asset)
        conn.commit()
        print(f"Asset {asset[0]} Updated successfully")
        cur.close()

    except sqlite3.Error as error:
        print("Failed to update database", error)
    finally:
        if conn:
            conn.close()


def create_inspection(database, inspection):
    """
    Create a new inspection into the inspections table
    :param database:
    :param inspection:
    :return: inspection id
    """
    conn = create_connection(database)
    with conn:
        sql = ''' INSERT INTO inspections(inspection_id, project_id, asset_id, GA_photo, good_condition, 
                  note, inspector_name, qualification, date_inspected, expiry_date)
                  VALUES(?,?,?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute(sql, inspection)
        conn.commit()
        return cur.lastrowid


def update_inspection(database, inspection):
    """
    Update inspection in the inspections table
    :param database:
    :param inspection:
    :return: updated inspection
    """
    try:
        conn = create_connection(database)
        cur = conn.cursor()
        sql_update_query = """UPDATE inspections SET project_id = ?, asset_id = ?, GA_photo = ?, good_condition = ?, 
                              note = ?, inspector_name = ?, qualification = ?, date_inspected = ?, expiry_date = ? 
                              WHERE inspection_id = ?"""
        cur.execute(sql_update_query, inspection)
        conn.commit()
        print(f"Inspection {inspection[0]} Updated successfully")
        cur.close()

    except sqlite3.Error as error:
        print("Failed to update database", error)
    finally:
        if conn:
            conn.close()


def create_defect(database, defect):
    """
    Create a new defect into the defects table
    :param conn:
    :param defect:
    :return: defect id
    """
    conn = create_connection(database)
    with conn:
        sql = ''' INSERT INTO defects(asset_id, inspection_id, project_id, element, defect, remedial, cost,
                  urgency) VALUES(?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute(sql, defect)
        conn.commit()
        return cur.lastrowid


def update_defect(database, defect):
    """
    Update defect in the defects table
    :param database:
    :param defect:
    :return: updated defect
    """
    try:
        conn = create_connection(database)
        cur = conn.cursor()
        sql_update_query = """UPDATE defects SET asset_id = ?, inspection_id = ?, project_id = ?, element = ?, 
                              defect = ?, remedial = ?, cost = ?, urgency = ? WHERE defect_id = ?"""
        cur.execute(sql_update_query, defect)
        conn.commit()
        print(f"Defect {defect[0]} Updated successfully")
        cur.close()

    except sqlite3.Error as error:
        print("Failed to update database", error)
    finally:
        if conn:
            conn.close()


def extract_entire_table(database, table):
    """
    Extract all information from a table of your choice
    :param database:
    :param table name of choice:
    :return: entire contents from table
    """
    conn = create_connection(database)
    with conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"select * from {table}")
        results = cursor.fetchall()
        cursor.close()
        return results


def retrieve_project(database, project_id):
    """
    Retrieve project data
    :param database:
    :param project:
    :return: all information relating to the project
    """
    conn = create_connection(database)
    with conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        rows = cursor.execute(
            "SELECT * FROM projects WHERE project_id = ?",
            (project_id,),
        ).fetchall()
        print(rows)
        cursor.close()
        return rows


def retrieve_asset(database, asset_id=None, project_id=None, both=False):
    """
    Retrieve asset data
    :param database:
    :param asset_id, default false:
    :param project_id, default false:
    :param both, default false

    If both the project id and asset id are known, input both and set both to true to filter search, otherwise input
    either the project id or asset id

    :return: all assets that match the search criteria
    """
    conn = create_connection(database)
    with conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if project_id is None:
            rows = cursor.execute(
                '''SELECT * FROM assets WHERE asset_id = ?''',
                (asset_id,),).fetchall()
        elif both is True:
            rows = cursor.execute(
                '''SELECT * FROM assets WHERE asset_id = ? AND 
                          project_id = ?''',
                (asset_id, project_id,), ).fetchall()
        else:
            rows = cursor.execute(
                '''SELECT * FROM assets WHERE project_id = ?''',
                (project_id,), ).fetchall()
        cursor.close()
        return rows


def retrieve_inspection(database, project_id=None, asset_id=None, inspection_id=None):
    """
    Retrieve inspection data based on search criteria
    :param database:
    :param asset_id, default None:
    :param project_id, default None:
    :param inspection_id, default None:

    Inspections will be retrieved that match the inputs fed in. For example, if project id and asset id are inputted,
    all inspections that have matching keys will be returned

    :return: all inspections that match the inputs
    """
    conn = create_connection(database)
    with conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if project_id is not None and asset_id is None and inspection_id is None:
            rows = cursor.execute(
                '''SELECT * FROM inspections
                WHERE project_id = ?''',
                (project_id,),).fetchall()
        elif project_id is None and asset_id is not None and inspection_id is None:
            rows = cursor.execute(
                '''SELECT * FROM inspections 
                WHERE asset_id = ?''',
                (asset_id,),).fetchall()
        elif project_id is None and asset_id is None and inspection_id is not None:
            rows = cursor.execute(
                '''SELECT * FROM inspections
                WHERE inspection_id = ?''',
                (inspection_id,),).fetchall()
        elif project_id is not None and asset_id is not None and inspection_id is None:
            rows = cursor.execute(
                '''SELECT * FROM inspections 
                WHERE project_id = ? AND asset_id = ?''',
                (project_id, asset_id,), ).fetchall()
        elif project_id is not None and asset_id is None and inspection_id is not None:
            rows = cursor.execute(
                '''SELECT * FROM inspections WHERE project_id= ? AND inspection_id = ?''',
                (project_id, inspection_id,), ).fetchall()
        elif project_id is None and asset_id is not None and inspection_id is not None:
            rows = cursor.execute(
                '''SELECT * FROM inspections 
                WHERE asset_id = ? AND inspection_id = ?''',
                (asset_id, inspection_id,), ).fetchall()
        else:
            rows = cursor.execute(
                '''SELECT * FROM inspections 
                WHERE project_id = ? AND asset_id = ? AND inspection_id = ?''',
                (project_id, asset_id, inspection_id,), ).fetchall()
        print(rows)
        cursor.close()
        return rows


def retrieve_defect(database, defect_id=None, asset_id=None, inspection_id=None):
    """
    Retrieve defect data
    :param database:
    :param asset_id, default None:
    :param defect_id, default None:
    :param inspection_id, default None:

    Defects will be retrieved that match the inputs fed in. For example, if inspection id and asset id are inputted,
    all defects that have matching keys will be returned

    :return: all defects that match the inputs
    """
    conn = create_connection(database)
    with conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if defect_id is not None and asset_id is None and inspection_id is None:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE defect_id = ?''',
                (defect_id,),).fetchall()
        elif defect_id is None and asset_id is not None and inspection_id is None:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE asset_id = ?''',
                (asset_id,),).fetchall()
        elif defect_id is None and asset_id is None and inspection_id is not None:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE inspection_id = ?''',
                (inspection_id,),).fetchall()
        elif defect_id is not None and asset_id is not None and inspection_id is None:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE defect_id = ? AND asset_id = ?''',
                (defect_id, asset_id,), ).fetchall()
        elif defect_id is not None and asset_id is None and inspection_id is not None:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE defect_id = ? AND inspection_id = ?''',
                (defect_id, inspection_id,), ).fetchall()
        elif defect_id is None and asset_id is not None and inspection_id is not None:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE asset_id = ? AND inspection_id = ?''',
                (asset_id, inspection_id,), ).fetchall()
        else:
            rows = cursor.execute(
                '''SELECT * FROM defects 
                WHERE defect_id = ? AND asset_id = ? AND inspection_id = ?''',
                (defect_id, asset_id, inspection_id,), ).fetchall()
        cursor.close()
        return rows


def convert_to_binary_data(filename):
    """
    Convert digital data to binary format
    """
    with open(filename, 'rb') as file:
        blob_data = file.read()
    return blob_data


def add_photo(database, defect_id, photo, caption):
    """
    Add a photo to the database
    :param database
    :param defect_id
    :param photo file
    :param caption for the photo
    """
    conn = create_connection(database)
    with conn:
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            sqlite_insert_blob_query = """ INSERT INTO photos
                                      (defect_id, photo, caption) VALUES (?, ?, ?)"""
            empPhoto = convert_to_binary_data(photo)
            # Convert data into tuple format
            data_tuple = (defect_id, empPhoto, caption)
            cursor.execute(sqlite_insert_blob_query, data_tuple)
            conn.commit()
            print("Image inserted successfully as a BLOB into a table")
            cursor.close()
        except sqlite3.Error as error:
            print("Failed to insert blob data into sqlite table", error)
            cursor.close()


def update_photo_caption(database, photo):
    """
    update a photo caption
    :param database
    :param photo id
    """
    try:
        conn = create_connection(database)
        cur = conn.cursor()
        sql_update_query = """UPDATE photos SET caption = ? WHERE photo_id = ?"""
        cur.execute(sql_update_query, photo)
        conn.commit()
        print(f"Photo {photo[0]} Updated successfully")
        cur.close()

    except sqlite3.Error as error:
        print("Failed to update database", error)
    finally:
        if conn:
            conn.close()


def write_to_file(data, filename):
    """
    Convert binary data into a file format
    """
    with open(filename, 'wb') as file:
        file.write(data)
    print("Stored blob data into: ", filename, "\n")


def read_blob_data(database, defect_id):
    """
    Return photo files that relate to a defect
    :param database
    :param defect_id
    :return photo files created locally to this script pulled from the database
    """
    conn = create_connection(database)
    with conn:
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            sql_fetch_blob_query = """SELECT * from photos where defect_id = ?"""
            cursor.execute(sql_fetch_blob_query, (defect_id,))
            record = cursor.fetchall()
            for row in record:
                photo_id = row[0]
                photo = row[2]
                photo_path = cwd + f"/image_{photo_id}.jpg"
                write_to_file(photo, photo_path)
            cursor.close()
        except sqlite3.Error as error:
            print("Failed to read blob data from sqlite table", error)
            cursor.close()


def obtain_blob_data(database, defect_id):
    """
    Obtain blob data that relate to a specific defect
    :param database
    :param defect_id
    :return blob data of all photos that correspond to the defect
    """
    conn = create_connection(database)
    with conn:
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            sql_fetch_blob_query = """SELECT * from photos where defect_id = ?"""
            cursor.execute(sql_fetch_blob_query, (defect_id,))
            record = cursor.fetchall()
            cursor.close()
            return record
        except sqlite3.Error as error:
            print("Failed to read blob data from sqlite table", error)
            cursor.close()


if __name__ == '__main__':

    creation_of_db()
    database = cwd + r"/MOD_inspection_database.db"
    conn = create_connection(database)
    with conn:
        update_project(database, ('updated', 'Me', '1'))
        # create a new project
        project = ('1', 'test', 'test')
        asset = ('3', '1', '1', '1', '1', '1', '1', '1', 2, '1', '1', '1', '1', '1', '1')
        inspection = ('2', '1', '3', '1', '1', '1', '1', '1', '1', '1')
        defect = ('3', '2', '1', 'test', 'test', 'test', 'test', 'test')
        project_id = create_project(database, project)
        asset_id = create_asset(database, asset)
        inspection_id = create_inspection(database, inspection)
        defect_id = create_defect(database, defect)
        add_photo(database, '1', cwd + "\Picture1.jpg", 'tester')
        add_photo(database, '1', cwd + "\Capture.jpg", 'tester1')

        project = ('2', 'test', 'test')
        asset = ('4', '2', '1', '1', '1', '1', '1', '1', '2', '1', '1', '1', '1', '1', '1')
        inspection = ('3', '2', '4', '1', '1', '1', '1', '1', '1', '1')
        defect = ('4', '3', '2', 'test', 'test', 'test', 'test', 'test')
        project_id1 = create_project(database, project)
        asset_id1 = create_asset(database, asset)
        inspection_id1 = create_inspection(database, inspection)
        defect_id1 = create_defect(database, defect)

        read_blob_data(database, 1)
        read_blob_data(database, 2)

        # print(table_count(conn, 'projects'))
        # print(table_count(conn, 'assets'))
        # print(table_count(conn, 'defects'))

        print('projects')
        # project
        retrieve_project(database, '1')

        print('assets')
        # asset
        retrieve_asset(database=database, asset_id='3', project_id=None)
        retrieve_asset(database, '3', '1')
        retrieve_asset(database, '3', '1', both=True)

        print('inspections')
        # inspections
        retrieve_inspection(database, '1')
        retrieve_inspection(database, None, '3', None)
        retrieve_inspection(database, None, None, '2')
        retrieve_inspection(database, None, '3', '2')
        retrieve_inspection(database, '1', '3', None)
        retrieve_inspection(database, '1', None, '2')
        retrieve_inspection(database, '1', '3', '2')

        print('DEFECTS')
        # defects
        retrieve_defect(database, 1)
        retrieve_defect(database, None, '3', None)
        retrieve_defect(database, None, None, '2')
        retrieve_defect(database, None, '3', '2')
        retrieve_defect(database, 1, '3', None)
        retrieve_defect(database, 1, None, '2')
        retrieve_defect(database, 1, '3', '2')

    conn.commit()
    conn.close()