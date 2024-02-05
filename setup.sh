
set -o errexit

if [ -d "./venv" ]; then
  echo "Virtual environment does already exist"
else
  echo "Create virtual environment"
  python -m venv --system-site-packages ./venv
fi

echo "Activate virtual environment"
source venv/bin/activate

echo "Update pip"
pip install --upgrade pip

echo "Install all requirements"
pip install -r requirements.txt