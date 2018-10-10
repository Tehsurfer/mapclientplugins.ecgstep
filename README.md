ECG step (with Scaffoldmaker Branch)
======
This Branch is kept around in case a need for scaffoldmaker becomes apparent.
-------

The ecg step is a plugin for the MAP Client application that registers ECG data to 3D models. The ECG data is sourced from a [Blackfynn](https://www.blackfynn.com "Blackfynn Homepage") acount (a cloud storage platform) and linked to the model to view and export to the webGL viewer (the in-broswer version).

Installation
------
1. *Mapclient installation*: If you have a current version of mapclient running, skip this step. Otherwise follow the instructions 
[here](https://docs.google.com/document/d/1GbZKzIK-kX86eAWQ0W9t-NmP8woLhHMNZCNhLRES_uE/edit?usp=sharing). The plugins mentioned in the instructions can be ignored but all other elements of the installation will be needed.

2. *ecgstep plugin installation*: Navigate to the 'plugins' folder created during the mapclient installation.
3. Use `git clone https://github.com/Tehsurfer/mapclientplugins.ecgstep.git`
4. Install requirements with  `pip install -r requirements.txt`
  
5. *Adding plugin to Mapclient*: if the plugin does not show up in Mapclient, add the directory 'mapclientplugins.ecgstep' to the plugin directories list 


Usage
------
The Step requires an input in the from of a list of 3D coordinates for the step as an input to render, while the output of the step is optional.

![image](https://user-images.githubusercontent.com/37255664/45839099-43191b00-bcc8-11e8-89f5-021043179cfb.png)


Input Step
------
The input step will need to output a list of 3D coordinates for the step to render. An example of how such coordinates would look is below: 

`coordinate_list = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.1], [0.0, 0.0, 0.2],...]`

Alternatively: You can download the [dummy data step](https://github.com/Tehsurfer/mapclientplugins.dummydatastep) I have created.








