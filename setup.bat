
if exist "./venv" (
  echo "Virtual environment does already exist"
) else (
  echo "Create virtual environment"
  python -m venv --system-site-packages ./venv
)

echo "Activate virtual environment"

echo "Update pip"
venv\\Scripts\\python.exe -m pip install --upgrade pip

echo "Install all requirements"
venv\\Scripts\\python.exe -m pip install -r requirements.txt