.. _how_to_use_STAAD_Plugin:

===============================
How to install the STAAD Plugin
===============================
To be able to access the STAAD Plugin, first contact Evan Hitchen for access to the exe file which you will need to
install the plugin. The plugin has no other dependencies, it is not mandatory to have python installed on your machine.

Note: The Plugin is only suitable on windows operating systems.

To install the Plugin, first of all open STAAD. On the top ribbon as shown below, click on the "Utilities" tab.

Following this, then click on the "Configure" button as shown below.

This will open up a new window called "Customise User Defined Tools". In this window, click on the new entry button
which is left of the red cross button on the right hand side of this window, this is again shown below.

On the new entry, type and name it “DataFusr Plugin”

.. figure:: _static/staad_plugin_pic1.png
   :align: center

On the "Customise User Defined Tools" window, next to the "Command" data entry cell, click on the three dots. This will
open a file explorer browser. Select the drop down in the bottom right of this window and on the select “Executable
Program File (*exe)”.

Following this, direct the file explorer browser to the STAAD Plugin exe location which has been provided by Evan
Hitchen. Then select the "STAAD DataFusr Plugin" exe file.

.. figure:: _static/staad_plugin_pic2.png
   :align: center

On the "Customise User Defined Tools" window, next to the "Initial Directory" data entry cell, click on the three dots.
A window called "Browse for Folder" will open. Direct and select the folder which contains the "STAAD DataFusr Plugin"
exe file. Once highlighted, press "Ok". Following this, press "Ok" on the "Customise User Defined Tools" window and the
STAAD Plugin is now ready to use.

.. figure:: _static/staad_plugin_pic3.png
   :align: center

===========================
How to use the STAAD Plugin
===========================

To open the Plugin, first of all open STAAD. On the top ribbon as shown below, click on the "Utilities" tab.

Following this, then click on the "User Tools" button as shown below. On the drop down, then select “DataFusr Plugin”.

.. figure:: _static/staad_plugin_pic4.png
   :align: center

Once the Plugin has opened, the Plugin is split into two tabs, either "Send STAAD model to" or "Receive STAAD model
from".

.. figure:: _static/staad_plugin_pic5.png
   :align: center

To check if you are using the latest version of the FEM Package, you can press the "Update Button". This will do any
necessary updates to the Plugin.

Firstly, the "Send STAAD model to" tab. The plugin should determine the STAAD file that is currently open and assumes
this is the staad file which is desired to be sent. If this is not correct or the file is not detected, the browse
button can be used to select the appropriate std file. You will then need to select where you wish to send
your STAAD file to.

.. figure:: _static/staad_plugin_pic6.png
   :align: center

If "Speckle" is selected, you will also need to enter a stream name and description. The maritime research server
is default for the speckle server entry, please change this if you wish to use a different server. On the first use of
the plugin, you will also need to enter your Speckle Token. Once this has been done once, this will be saved and will be
the default entry everytime you open the plugin again.

.. figure:: _static/staad_plugin_pic7.png
   :align: center

If any other programme other than "Speckle" is selected from the "Send model to" drop down, no other data will need to
be entered.

Once you are ready to send the STAAD file, press the "Generate" button. Updates will be provided on the "Python Console
Output". If you have sent your std file to any other programme than "Speckle", your new file can be then found in a
folder called "STAAD_Plugin_Output" in your Documents.

.. figure:: _static/staad_plugin_pic10.png
   :align: center

If for whatever reason you have errors that appear, they will be reported back in the "Python Console Output". If it is
not clear what the error is, please copy the output and send this to Evan Hitchen and he can assist further. To do this,
press the "Copy Console Output". This will copy all output directly to your clipboard.

.. figure:: _static/staad_plugin_pic9.png
   :align: center

If you are wanting to receive a STAAD model from speckle or another programme, you can use the second tab. Once again,
if "Speckle" is the chosen origin, the relevant input fields as mentioned above will need to be entered. If receiving a
model from any other programme, you will need to select the file in which you want to convert into a std file.

Once ready, press the generate button. Your new staad model can once again be found in a folder called
"STAAD_Plugin_Output" in your Documents.

.. figure:: _static/staad_plugin_pic10.png
   :align: center