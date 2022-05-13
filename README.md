# examples_of_work

Within this repository you will find a selection of examples of my work I have created over the past three or so years. The following contents gives an outline of what each folder contains. If you wish to see more from any of the following projects, do let me know.

## DataFusr
DataFusr is a interoperability platform for automated design. Although I cannot include the entire package for a number of reasons, I have included a selection of scripts to give a flavour of the package and how it is structured. The files I have include are a few of the sections of the package that I am primarily managing These include:

### DataFusr Files
* fem_STAADutils.py - series of functions that are used to convert to and from STAAD (A finite element analysis programme). Functions include creating a STAAD file and converting classes from the package, reading a STAAD file and converting it to the necessary python orientated objects, carrying out a remote analsysis and handling results plus more.
* fem_mesh.py - functions used to handle mesh objects which are the basis of any finite elment model
* mesh_classes folder - the folder includes a series of py files to show how objects are constructed within the fem_package

## STAAD Plugin
The STAAD Plugin is a tool that encorporates all functionality from DataFusr and places it in a GUI application so that non python users can use the benefits of DataFusr. The STAAD Plugin was developed using Tkinter and then packaged as an exe application using pyinstaller. The plugin was developed so that it also prints feedback directly from the python console to the user within the plugin so they can see what is occuring as a python user would. The files included are as follows:

### STAAD Plugin Files
* staad_plugin.py - The code used to create the application itself. 
* staad_plugin.spec - the spec file used by pyinstaller to package up the application
* use_STAAD_Plugin.rst - documentation file I created to assist users with installation into STAAD and how to use it

## SQL Example
SQL Example folder contains one file which is sql_app.py which provides an example of myself using SQL to create a database for an inspection database application as mentioned in my CV. Happy to present the application upon request

## Invoice Generator App
The invoive generator app folder contains the script that I wrote to develop an application for a team of colleagues who wanted to automate a process in which they recieve an invoice from the client and then need to adapt it into a different format. The application is written using tkinter and again is packaged using pyinstaller. The application can be fed multiple invoices at once and then will create an equal amount of the new formatted documents and pdf them.

## Django Inspection Hub
Within the Django Inspection Hub folder contains the majority of the files I wrote to create a django website used to host information for asset management purposes as mentioned within my CV. The files added were those used for the proof of concept. The site includes the following features:

* Dynamic map with pins showing all site locations included in the database
* Filterable data table that is linked to the backend SQL database
* Pages with forms to edit the SQL database
* Ability to upload existing reports and excel sheets to upload data into the SQL database
* Ability to generate reports from the site

Within the folder, there are also various examples of html files used to construct the pages too within dashboard -> templates. Bootstrap was used for the majority of the styling
