
# ![logo](docs/img/Open%20Source%20Logo%20smaller.png)  Object Builder for i (OBI)

Check [ibm-i-build-obi](https://github.com/andreas-prouza/ibm-i-build-obi) to see, how to use it in your IDE.

## Quick Setup

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
