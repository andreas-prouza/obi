
set -o errexit

if [ -d "./venv" ]; then
  echo "Virtual environment does already exist"
else
  echo "Create virtual environment"
  python -m venv --system-site-packages ./venv
fi

echo "Activate virtual environment"
if [ $OSTYPE == 'msys' ] || [ $OSTYPE == 'win32' ] || [ $OSTYPE == 'mingw' ] || [ $OSTYPE == 'mingw32' ]; then
  source venv\\Scripts\\activate
  PYTHON_PATH=venv\\Scripts\\python.exe
else
  source venv/bin/activate
  PYTHON_PATH=venv/bin/python
fi

echo "Update pip"
"$PYTHON_PATH" -m pip install --upgrade pip

echo "Install all requirements"
pip install -r requirements.txt