from setuptools import setup

with open('README.md') as f:
    readme = f.read()

with open('LICENSE.txt') as f:
    license = f.read()

setup(name='rayvens',
      packages=['rayvens'],
      version='0.1',
      description='Ray eventing',
      license=license,
      long_description=readme,
      author='Rayvens authors',
      author_email='tardieu@us.ibm.com;gheorghe-teod.bercea@ibm.com',
      url='https://github.ibm.com/solsa/rayvens')
