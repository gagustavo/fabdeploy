from setuptools import setup

setup(
    name='fabdeploy',
    version='0.1',
    description='Fabric deploy wrappers',
    url='https://git.sisqualis.com.br/sisqualis/fabdeploy',
    author='Tiago Ilieve',
    author_email='tiago.ilieve@sisqualis.com.br',
    license='Proprietary',
    packages=['fabdeploy'],
    install_requires=['Fabric'],
    zip_safe=False
)
