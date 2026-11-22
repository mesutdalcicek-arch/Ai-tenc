from pythonforandroid.recipe import PythonRecipe

class HttpxRecipe(PythonRecipe):
    version = '0.27.0'
    url = 'https://files.pythonhosted.org/packages/source/h/httpx/httpx-{version}.tar.gz'
    depends = ['setuptools']
    call_hostpython_via_targetpython = False

recipe = HttpxRecipe()
