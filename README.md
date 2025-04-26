
# ![logo](docs/img/Open%20Source%20Logo%20smaller.png)  Object Builder for i (OBI)

# 2 Parts

## Client

The client communicates with the back end to get the job done.  
This has several advantages:  
* You can use the backend on your local PC for better performance
* It's independent to any IDE
  You can use RDi or vscode or even notepad++.  
  There is a full integration (extension) for [vscode](https://marketplace.visualstudio.com/items?itemName=andreas-prouza.obi).
* It's easier to maintain, implement new features or customise it

Check [ibm-i-build-obi](https://github.com/andreas-prouza/ibm-i-build-obi) to see, how to use it in your IDE.


## Backend

This project is part of the backend.

### Server side

On you IBM i it's used to run the build.

### Client side

On your local PC it's used to generate the build list.  
(List of compile commands for all necessary sources.)

You can also use OBI on your IBM i to do job.  
But this comes with some overhead (additional network traffic, IFS operations to generate the build list).  

It's highly recommended to also use the OBI backend also on your local PC to get the best performance out of it.


# Prerequisites

* Python 3.9 or higher
* git
* On IBM i
  * Open Source Tools (YUM)
  * I would also recommend to do the [ssh-setup](https://github.com/andreas-prouza/ibm-i-build/blob/main/docs/pages/SSH.md) for your user profile.  
    It's much easier for the long term do it via SSH and Bash.
  * If you have not done the ssh-setup you need to add the open source package path to your session
    1. Open QSH
    2. Execute: `export PATH="/QOpenSys/pkgs/bin:$PATH"`


# Quick Setup

The setup is the same for your IBM i and your local PC.

Open a console.
* IBM i: QSH  
  Make sure that the `PATH` env-var is set correctly: `export PATH="/QOpenSys/pkgs/bin:$PATH"`
* Windows: cmd
* Linux/Mac: terminal

```sh
-bash-5.2$ git clone https://github.com/andreas-prouza/obi.git
  Cloning into 'obi'...
  remote: Enumerating objects: 322, done.
  remote: Counting objects: 100% (322/322), done.
  remote: Compressing objects: 100% (228/228), done.
  remote: Total 322 (delta 147), reused 236 (delta 69), pack-reused 0
  Receiving objects: 100% (322/322), 515.89 KiB | 4.69 MiB/s, done.
  Resolving deltas: 100% (147/147), done.
```

Jump into the directory:
```cd obi```

Run the setup script 
* Linux/Mac/IBM i:  
  ```./setup.sh```
* Windows:  
  ```setup.bat```

The script will ...

* Create a virtual environment for Python
* Update PIP
* Install all necessary modules from ```requirements.txt```

```sh
-bash-5.2$ cd obi
-bash-5.2$ ./setup.sh
  Create virtual environment
  Activate virtual environment
  Update pip
  Requirement already satisfied: pip in ./venv/lib/python3.9/site-packages (23.0.1)
  Collecting pip
    Downloading pip-24.0-py3-none-any.whl (2.1 MB)
       ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2.1/2.1 MB 4.7 MB/s eta 0:00:00
  Installing collected packages: pip
    Attempting uninstall: pip
      Found existing installation: pip 23.0.1
      Uninstalling pip-23.0.1:
        Successfully uninstalled pip-23.0.1
  Successfully installed pip-24.0
  Install all requirements
  Collecting toml (from -r requirements.txt (line 1))
    Downloading toml-0.10.2-py2.py3-none-any.whl (16 kB)
  Installing collected packages: toml
  Successfully installed toml-0.10.2
```

After install, it's ready to use.  
Nothing more needs to be done.  
All the configuration will be used from your project folder.

# FAQ

### Python not found

Possible reasons:
* Python is not installed
* Your Python command needs a version number (e.g. python3)