ECG step
======
The ecg step is a plugin for the MAP Client application that registers ECG data to 3D models. The ECG data is sourced from a [Blackfynn](https://www.blackfynn.com "Blackfynn Homepage") acount (a cloud storage platform) and linked to the model to view and export to the webGL viewer (the in-broswer version).

Installation
------
1. *Mapclient installation*: If you have a current version of mapclient running, skip this step. Otherwise follow the instructions 
[here](https://docs.google.com/document/d/1GbZKzIK-kX86eAWQ0W9t-NmP8woLhHMNZCNhLRES_uE/edit?usp=sharing). The plugins mentioned in the instructions can be ignored but follow everything else

2. *ecgstep plugin installation*: Navigate to the 'plugins' folder created during the mapclient installation.

  a. use `git clone https://github.com/Tehsurfer/mapclientplugins.ecgstep.git`
  b. install requirements  `pip install -r requirements.txt`
  
3. *Adding plugin to Mapclient*: if the plugin does not show up in Mapclient, add the directory 'mapclientplugins.ecgstep' to the plugin directories list 


Usage
------
The Step requires an 






