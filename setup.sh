
set -o errexit

if [ -d "./venv" ]; then
  echo "Virtual environment does already exist"
else
  echo "Create virtual environment"
  python -m venv --system-site-packages ./venv
fi

echo "Activate virtual environment"
if [ $OSTYPE == 'cygwin' ]; then
  source venv/Scripts/activate
else
  source venv/bin/activate
fi

echo "Update pip"
pip install --upgrade pip

echo "Install all requirements"
pip install -r requirements.txt