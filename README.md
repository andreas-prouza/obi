
# ![logo](docs/img/Open%20Source%20Logo%20smaller.png)  Object Builder for i (OBI)

For detailed documentation see [OBI extension](https://github.com/andreas-prouza/obi-extension)

# Client

## Visual Studio Code (vscode)

There is a full integration (extension) for vscode.  
See [OBI extension](https://marketplace.visualstudio.com/items?itemName=andreas-prouza.obi).

In vscode the build commands will be handled by the extension.  
Only on IBM i you need the obi package to run the build.


## Eclipse, RDi, Notepad++, ...

All other IDEs can communicate with the OBI package in background

This has several advantages:  
* You can use the backend on IBM i or direct on your local PC for better performance
* It's independent to any IDE  
  You can use RDi or vscode or even notepad++.  

Check [ibm-i-build-obi](https://github.com/andreas-prouza/ibm-i-build-obi) to see, how to use it in your IDE.


# Server side

On you IBM i it's used to run the build.


# Prerequisites on IBM i

* Open Source Tools (YUM)
* Python 3.12 or higher
* I would also recommend to do the [ssh-setup](https://github.com/andreas-prouza/obi-extension/blob/main/asserts/docs/ssh.md) for your user profile.  
  It's much easier for the long term do it via SSH and Bash.


# Quick Setup

Open a console (QSH, SSH, ...)  
Make sure that the `PATH` env-var is set correctly: `export PATH="/QOpenSys/pkgs/bin:$PATH"`

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
```./setup3.13.sh```

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

# FAQ

### Python not found

Possible reasons:
* Python is not installed
* Your Python command needs a version number (e.g. python3.13)
* The `PATH` env-var is not set correctly: `export PATH="/QOpenSys/pkgs/bin:$PATH"`