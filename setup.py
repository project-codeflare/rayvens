from setuptools import setup, find_packages

with open('README.rst') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()

setup(
    name='ray_events',
    version='0.1.0',
    description='Ray eventing',
    long_description=readme,
    author='Gheorghe-Teodor Bercea',
    author_email='gheorghe-teod.bercea@ibm.com',
    url='https://github.ibm.com/Gheorghe-Teod-Bercea/ray_events',
    license=license,
    # packages=find_packages(exclude=('tests', 'docs'))
    packages=find_packages()
)
