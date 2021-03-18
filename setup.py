#
# Copyright IBM Corporation 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from setuptools import setup

setup(name='rayvens',
      packages=[
          'rayvens', 'rayvens.core', 'rayvens.core.camel_anywhere',
          'rayvens.core.utils'
      ],
      version='0.1',
      description='Ray eventing',
      license='apache-2.0',
      author='Rayvens authors',
      author_email='tardieu@us.ibm.com;gheorghe-teod.bercea@ibm.com',
      url='https://github.ibm.com/solsa/rayvens')
