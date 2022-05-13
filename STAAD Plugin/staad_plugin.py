### ===================================================================================================================
###   STAAD Plugin
### ===================================================================================================================

### ===================================================================================================================
###   Contents of script
### ===================================================================================================================

#   1. Import modules

#   2. Redirect cwd to location of the exe file and determine user's ID

#   3. Create Classes

#   4. Main tkinter script

#   5. Functions to be used within the script

#   6. Exe layout and graphical interface build up

#   7. Test Harness

#   8. End of script

### ===================================================================================================================
###   1. Import modules
### ===================================================================================================================

# tkinter imports to build the GUI interface, have to import in this manner
from tkinter import *
from tkinter import ttk, scrolledtext, filedialog
import tkinter as tk
# although not shown as active, os and sys used for managing directories throughout the script
import sys
import os
# subprocess used to determine the active std file
from subprocess import call, check_call
# pip used to within the script to update the FEM package after the exe has been packaged
import pip
# datafusr logo converted and then unconverted from byte form so that it can be packaged within the exe file
from pic2str import datafusrimg
import base64
from io import BytesIO
# Used to determine the user's number
import pathlib
from rhdhv_fem import *

### ===================================================================================================================
###   2. Redirect cwd to location of the exe file and determine user's ID
### ===================================================================================================================

# Obtain all processes that are running including the launch of the exe file
cmd = 'WMIC PROCESS get Caption,Commandline,Processid'
proc = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
# Find the line which states the status of the plugin and also its location in which its being called from
for line in proc.stdout:
    if 'STAAD DataFusr Plugin.exe' in str(line):
        split_line = str(line).split('STAAD DataFusr Plugin.exe')
        for i in split_line:
            if 'C:' in i:
                # Now the string has been found, slice it and arrange to obtain the user number and directory of the exe
                temporary_text = str(i)[::-1]
                index_of_c = len(i) - temporary_text.index(":C")
                file_directory = "C:" + i[index_of_c:] + 'STAAD DataFusr Plugin.exe'
                path = os.path.normpath(file_directory)
                split_path = path.split(os.sep)
                user_name = split_path[2]
                exe_directory = ''
                for l in range((len(split_path) - 1)):
                    if l == (len(split_path) - 2):
                        exe_directory = exe_directory + split_path[l]
                    else:
                        exe_directory = exe_directory + split_path[l] + '/'
                # Redirect the working cwd to the path of the exe
                os.chdir(Path(exe_directory))
                break

### ===================================================================================================================
###   3. Create classes
### ===================================================================================================================


class PrintLogger:
    """
    PrintLogger is a class to convert a textbox into a PrintLogger. This will present any text that is being printed by
    python. The class also will make sure that the PrintlLogger textbox is inactive after any text is added so it cant
    be edited. It will make sure a scroll bar is also added and the last text added to the text box is always in view.
    """
    def __init__(self, textbox):  # pass reference to text widget
        self.textbox = textbox  # keep ref

    def write(self, text):
        self.textbox.config(state=NORMAL)
        self.textbox.insert(tk.END, text)  # write text to textbox
        self.textbox.config(state=DISABLED)
        self.textbox.see("end")
        # could also scroll to end of textbox here to make sure always visible

    def flush(self):  # needed for file like object
        pass

### ===================================================================================================================
###   4. Main tkinter script
### ===================================================================================================================


def main():
    """
    Function used to initiate and contain main script for the tkinter application
    """

### ===================================================================================================================
###   5. Functions to be used within the script
### ===================================================================================================================

    def copy_button_function():
        """
        Function to copy all text from the object it is assigned too to the clipboard
        """
        screen.clipboard_clear()
        screen.clipboard_append(output_text.get('1.0', 'end-1c'))

    def upgrade():
        """
        Function used to pip upgrade the FEM package within the script. This can be assigned to a button to initiate
        this function.
        """
        print('Please wait while an update is checked for...')
        call(['pip', 'install', '--upgrade', 'rhdhv_fem'])
        result = call(['pip', 'install', '--upgrade', 'rhdhv_fem'])
        if str(result) == "0":
            print('FEM package is up to date')
        else:
            print('FEM Package could not be updated, please contact Evan Hitchen for further information. The package '
                  'can still be used but is not the latest version, please be aware.')

    def disableEntry(entry):
        """
        Function to disable a tkinter object.

        Input:
            - entry: Textbox object or similar that is to be disabled.
        """
        entry.config(state='disable')

    def allowEntry(entry):
        """
        Function to enable a tkinter object.

        Input:
            - entry: Textbox object or similar that is to be enabled/made active.
        """
        entry.config(state='normal')

    def change_dropdown_tab1(*args):
        """
        Function which changes the input fields on tab 1 based on the drop down menu selection
        """
        if software_variable_tab1.get() == 'SPECKLE':
            allowEntry(stream_name_entry_tab1)
            allowEntry(stream_description_entry_tab1)
            allowEntry(stream_server_entry_tab1)
            allowEntry(speckle_token_entry_tab1)
        else:
            disableEntry(stream_name_entry_tab1)
            disableEntry(stream_description_entry_tab1)
            disableEntry(stream_server_entry_tab1)
            disableEntry(speckle_token_entry_tab1)

    def change_dropdown_tab2(*args):
        """
        Function which changes the input fields on tab 2 based on the drop down menu selection
        """
        if software_variable_tab2.get() == 'SPECKLE':
            allowEntry(stream_id_entry_tab2)
            allowEntry(stream_server_entry_tab2)
            allowEntry(speckle_token_entry_tab2)
            browser_tab2["state"] = "disable"
        else:
            disableEntry(stream_id_entry_tab2)
            disableEntry(stream_server_entry_tab2)
            disableEntry(speckle_token_entry_tab2)
            browser_tab2["state"] = "normal"

    # Tab 1 browse button function and setter
    def browse_button_tab1():
        """
        Browse button on tab 1 to look for std files. Once an std file has been selected, a file name variable is
        assigned which is the form of a directory to the file name.
        """
        # Allow user to select a directory and store it in global var
        filename = filedialog.askopenfilename(initialdir="/",
                                              title="Select a File",
                                              filetypes=(("std Files",
                                                          "*.std*"),
                                                         ("all files",
                                                          "*.*")))
        file_location_label_tab1.configure(text="File chosen: " + filename)
        file_name_variable_tab1.set(filename)

    # Tab 2 browse button function and setter
    def browse_button2():
        """
        Browse button on tab 2 to look for an external file which is to be converted. Once a file has been
        selected, a file name variable is assigned which is the form of a directory to the file name.
        """
        # Allow user to select a directory and store it in global variable called external_file_name_variable_tab2
        filename = filedialog.askopenfilename(initialdir="/",
                                              title="Select a File",
                                              filetypes=(("all files",
                                                          "*.*")))
        file_location_label_tab2.configure(text="File chosen: " + filename)
        external_file_name_variable_tab2.set(filename)

    def generate():
        """
        Generate function is used on both tabs for each generate button to run the chosen method. Firstly, the function
        obtains the speckle token of the user from the speckle token text file that is alongside the exe file. Following
        this, the tab which is currently active will be determined so the script determines the active generate button.
        If tab 1 is active, it will convert the chosen staad file into the programme of choice in accordance with what
        is selected from the dropdown menu on tab 1.
        If tab 2 is active, it will convert the chosen file into an std file or if speckle is selected, pull a stream
        from the speckle server.
        """
        try:
            # Obtain speckle token file
            speckle_token_file = open(f"speckle_tokens/speckle_token_{user_number.get()}.txt", "w+")
            # Creates directory if not already available in documents for the new model files to be dumped
            if os.path.isdir(f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output"):
                pass
            else:
                os.mkdir(f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output")
            # Determine if tab 1 is active
            if tabControl.tab(tabControl.select(), "text") == tab1_name:
                # Overwrites speckle token in text file for user
                speckle_token_file.write(speckle_token_tab1.get())
                # Get file name in question
                file_name = file_name_variable_tab1.get()
                # Checks to see that an std file is actually available and doesnt run if so
                if '.std' not in (file_name.lower() or file_name.lower().endswith('.std')):
                    print('Please select an appropriate std file to use')
                else:
                    # Create project
                    project = fem_start_project('STAAD_PLUGIN_MODEL')
                    # Pull data from staad model and then create new model based on programme of choice in drop down
                    project.from_staad(std_file=file_name)
                    if software_variable_tab1.get() == 'SCIA':
                        project.to_scia(folder=f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output")
                    elif software_variable_tab1.get() == 'SPECKLE':
                        stream_name_text = stream_name_entry_tab1.get()
                        stream_description_text = stream_description_entry_tab1.get()
                        stream_server_text = stream_server_entry_tab1.get()
                        speckle_token_text = speckle_token_entry_tab1.get()
                        project.to_datafusr(stream_name=stream_name_text, stream_description=stream_description_text,
                                            speckle_server_url=stream_server_text,
                                            speckle_token=speckle_token_text)
                    else:
                        project.to_sofistik(folder=f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output")
                    if software_variable_tab1.get() == 'SPECKLE':
                        print('Please login to speckle to view model')
                    else:
                        print("Please go to the following folder for your model:")
                        print(f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output")
            # Determine if tab 2 is active
            elif tabControl.tab(tabControl.select(), "text") == tab2_name:
                # Overwrites speckle token in text file for user
                speckle_token_file.write(speckle_token_tab2.get())
                # Get file name in question
                file_name = external_file_name_variable_tab2.get()
                # Create project and pull from chosen file based on the drop down selection
                project = fem_start_project('STAAD_PLUGIN_MODEL')
                if software_variable_tab2.get() == 'SCIA':
                    project.from_scia(project=project, input_file=file_name)
                elif software_variable_tab2.get() == 'SPECKLE':
                    project.from_datafusr(stream_id=stream_id_tab2.get(), speckle_server_url=stream_server_tab2.get(),
                                          speckle_token=speckle_token_tab2.get())
                else:
                    project.from_sofistik(cdb_file=file_name)
                project.to_staad(folder=f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output")
                if software_variable_tab2.get() == 'SPECKLE':
                    print('Please login to speckle to view model')
                else:
                    print("Please go to the following folder for your model:")
                    print(f"C:/Users/{user_number.get()}/Documents/STAAD_Plugin_Output")
            speckle_token_file.close()
        # Print any exception for the user to see in the PrintLogger
        except Exception as e:
            print(e)

### ===================================================================================================================
###   6. Exe layout and graphical interface build up
### ===================================================================================================================

    # Creates screen for the app and defines geometry.
    screen = Tk()
    screen.geometry("500x600")
    # No adjustment to size of window allowed
    screen.resizable(False, False)

    # Make the two tabs in the exe file and name them
    tabControl = ttk.Notebook(screen)
    tab1 = ttk.Frame(tabControl)
    tab2 = ttk.Frame(tabControl)
    tab1_name = '    Send STAAD model to    '
    tab2_name = '    Receive STAAD model from    '
    tabControl.add(tab1, text=tab1_name)
    tabControl.add(tab2, text=tab2_name)
    tabControl.pack(expand=1, fill="both")

    # Convert image from bytes into a usable graphic and set as icon
    p1 = PhotoImage(data=datafusrimg)
    # Setting icon of master window
    screen.iconphoto(False, p1)

    # Set screen title
    screen.title("STAAD DataFusr Plugin")

    # Set headings
    # Tab 1 Heading
    heading1 = Label(tab1, text= "STAAD DataFusr Plugin", font= ('Helvetica', 12, 'bold'), bg= "DodgerBlue3",
                     fg = "white", height= "3", width= "500")
    heading1.pack()
    # Tab 2 Heading
    heading2 = Label(tab2, text="STAAD DataFusr Plugin", font=('Helvetica', 12, 'bold'), bg="DodgerBlue3", fg="white",
                     height="3", width="500")
    heading2.pack()

    # Set constant for top depth
    top_depth = 20

    # Get user number and make it global
    user_number = StringVar(screen)
    user_number.set(user_name)

    # Redirect cwd to path of the exe directory, not the STAAD Plugin folder in which it thinks it is
    # exe_directory = f'C:/Users/{user_number.get()}/Documents/python_scripts/STAAD Plugin Final/dist'
    # os.chdir(Path(exe_directory))

    # Tab 1 software variable and selection
    software_variable_tab1 = StringVar(screen)
    software_variable_tab1.set('SPECKLE')
    # Define drop down selection and options for tab 1
    softwarechosen_tab1 = ttk.Combobox(tab1, width = 27, textvariable = software_variable_tab1)
    softwarechosen_tab1['values'] = ["SCIA",
                                 "SPECKLE",
                                 "SOFiSTiK"] #etc
    softwarechosen_tab1.place(x=130, y=60 + top_depth)
    # Set initial option
    softwarechosen_tab1.current(1)
    software_label_tab1 = Label(tab1, text="Send model to:", )
    software_label_tab1.place(x=15, y=60 + top_depth)

    # Tab 2 software variable and selection
    software_variable_tab2 = StringVar(screen)
    software_variable_tab2.set('SPECKLE')
    # Define drop down selection and options for tab 2
    softwarechosen_tab2 = ttk.Combobox(tab2, width=27, textvariable=software_variable_tab2)
    softwarechosen_tab2['values'] = ["SCIA",
                                  "SPECKLE",
                                  "SOFiSTiK"]  # etc
    softwarechosen_tab2.place(x=130, y=60 + top_depth)
    # Set initial option
    softwarechosen_tab2.current(1)
    software_label2 = Label(tab2, text="Receive model from:", )
    software_label2.place(x=15, y=60 + top_depth)

    # link function to change dropdown
    software_variable_tab1.trace('w', change_dropdown_tab1)
    software_variable_tab2.trace('w', change_dropdown_tab2)

    # Tab 1 staad file name variable
    file_name_variable_tab1 = StringVar(screen)
    # Automatically determine file name of open staad file
    cmd = 'WMIC PROCESS get Caption,Commandline,Processid'
    proc = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    for line in proc.stdout:
        if "Bentley.Staad.exe" in str(line) and '.std' in str(line):
            line_split = str(line).split('"')
            for i in line_split:
                if ".std" in i:
                    file_name_unedited = i
                    filename = file_name_unedited.replace("\\\\", "/")
                    file_name_variable_tab1.set(filename)
                    break

    # Tab 1 Browse button and label for file chosen etc.
    browser_tab1 = Button(tab1,text="Browse Files", command=browse_button_tab1)
    browser_tab1.place(x=130, y=100 + top_depth)
    browser_label_tab1 = Label(tab1, text=f"Choose file to send: ", )
    browser_label_tab1.place(x=15, y=100 + top_depth)
    file_location_label_tab1 = Label(tab1, text=f"File chosen: {file_name_variable_tab1.get()}", )
    file_location_label_tab1.place(x=15, y=130 + top_depth)

    # Tab 2 external file name variable
    external_file_name_variable_tab2 = StringVar(screen)

    # Tab 2 Browse button and label for file chosen etc.
    browser_tab2 = Button(tab2,text="Browse Files", command=browse_button2)
    browser_tab2.place(x=140, y=100 + top_depth)
    browser_tab2["state"] = "disable"
    browser_label_tab2 = Label(tab2, text=f"Choose file to receive: ", )
    browser_label_tab2.place(x=15, y=100 + top_depth)
    file_location_label_tab2 = Label(tab2, text=f"File chosen: {external_file_name_variable_tab2.get()}", )
    file_location_label_tab2.place(x=15, y=130 + top_depth)

    # Read last used speckle token
    if os.path.isfile(f'speckle_tokens/speckle_token_{user_number.get()}.txt'):
        existing_speckle_token_file = open(f"speckle_tokens/speckle_token_{user_number.get()}.txt", "r")
        existing_token = existing_speckle_token_file.read()
        existing_speckle_token_file.close()
    else:
        existing_token = 'Insert Speckle Token'

    # Tab 1 stream info, buttons and labels for when speckle is selected
    stream_name_label_tab1 = Label(tab1, text="Stream name:", )
    stream_name_label_tab1.place(x=15, y=160 + top_depth)
    stream_name_tab1 = StringVar()
    stream_name_entry_tab1 = Entry(tab1, textvariable=stream_name_tab1, width="55")
    stream_name_entry_tab1.place(x=130, y=160 + top_depth)

    stream_description_label_tab1 = Label(tab1, text="Stream description:", )
    stream_description_label_tab1.place(x = 15, y = 190 + top_depth)
    stream_description_tab1 = StringVar()
    stream_description_entry_tab1 = Entry(tab1, textvariable=stream_description_tab1, width = "55")
    stream_description_entry_tab1.place(x = 130, y = 190 + top_depth)

    stream_server_label_tab1 = Label(tab1, text="Stream server:", )
    stream_server_label_tab1.place(x = 15, y = 220 + top_depth)
    stream_server_tab1 = StringVar(value="https://maritime-research.datafusr.rhdhv.digital")
    stream_server_entry_tab1 = Entry(tab1, textvariable=stream_server_tab1, width = "55")
    stream_server_entry_tab1.place(x = 130, y = 220 + top_depth)

    speckle_token_label_tab1 = Label(tab1, text="Speckle Token:", )
    speckle_token_label_tab1.place(x=15, y=250 + top_depth)
    speckle_token_tab1 = StringVar()
    speckle_token_tab1.set(f'{existing_token}')
    speckle_token_entry_tab1 = Entry(tab1, textvariable=speckle_token_tab1, width = "55")
    speckle_token_entry_tab1.place(x=130, y=250 + top_depth)

    # Tab 2 stream info, buttons and labels for when speckle is selected
    stream_id_label_tab2 = Label(tab2, text="Stream ID:", )
    stream_id_label_tab2.place(x=15, y=160 + top_depth)
    stream_id_tab2 = StringVar()
    stream_id_entry_tab2 = Entry(tab2, textvariable=stream_id_tab2, width="55")
    stream_id_entry_tab2.place(x=130, y=160 + top_depth)

    stream_server_label_tab2 = Label(tab2, text="Stream server:", )
    stream_server_label_tab2.place(x=15, y=220 + top_depth)
    stream_server_tab2 = StringVar(value="https://maritime-research.datafusr.rhdhv.digital")
    stream_server_entry_tab2 = Entry(tab2, textvariable=stream_server_tab2, width="55")
    stream_server_entry_tab2.place(x=130, y=220 + top_depth)

    speckle_token_label_tab2 = Label(tab2, text="Speckle Token:", )
    speckle_token_label_tab2.place(x=15, y=250 + top_depth)
    speckle_token_tab2 = StringVar()
    speckle_token_tab2.set(f'{existing_token}')
    speckle_token_entry_tab2 = Entry(tab2, textvariable=speckle_token_tab2, width="55")
    speckle_token_entry_tab2.place(x=130, y=250 + top_depth)

    # Copy button on both tabs
    copy_out_button = Button(text ="Copy Console Output", command=copy_button_function)
    copy_out_button.place(x=210, y=310 + top_depth)

    # Update button on both tabs
    update_button = Button(text ="Update", command=upgrade)
    update_button.place(x=360, y=310 + top_depth)

    # Console for both tabs
    python_console_label = Label(text="Python Console Output:", )
    python_console_label.place(x=15, y=350 + top_depth)
    output_text = tk.scrolledtext.ScrolledText(height='12', width = '55')
    output_text.place(x=15,y= 370 + top_depth)
    output_text.config(state=DISABLED)

    # create instance of PrintLogger class out of the scrolled text object
    pl = PrintLogger(output_text)
    # replace sys.stdout with our object
    sys.stdout = pl

    # Generate button on both tabs
    generate_button = Button(text ="Generate", bg="DodgerBlue3", fg='white', command=generate)
    generate_button.place(x=130, y=310 + top_depth)

    screen.mainloop()

### ===================================================================================================================
###   7. Test Harness
### ===================================================================================================================


if __name__ == '__main__':
    main()

### ===================================================================================================================
###   8. End of script
### ===================================================================================================================