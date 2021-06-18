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

import re
from setuptools import setup

long_description = '''Rayvens augments [Ray](https://ray.io) with events. With
Rayvens, Ray applications can subscribe to event streams, process and produce
events. Rayvens leverages [Apache Camel](https://camel.apache.org) to make it
possible for data scientists to access hundreds of data services with little
effort.

For the full documentation see
[https://github.com/project-codeflare/rayvens](https://github.com/project-codeflare/rayvens).
'''

with open('scripts/rayvens-setup.sh') as f:
    version = re.findall('rayvens_version=([0-9.]+)', f.read())[0]

setup(
    name='rayvens',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=['rayvens', 'rayvens.core'],
    package_data={'rayvens.core': ['*.java']},
    install_requires=[
        'confluent-kafka>=1.6.1', 'ray[default,serve,k8s]>=1.3.0'
    ],
    scripts=['scripts/rayvens-setup.sh'],
    version=version,
    python_requires='>=3.6',
    description='Rayvens augments Ray with events.',
    license='Apache 2.0',
    author='Rayvens authors',
    author_email='tardieu@us.ibm.com, gheorghe-teod.bercea@ibm.com',
    keywords=("ray events kubernetes"),
    url='https://github.com/project-codeflare/rayvens',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Java',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: OS Independent',
        'Topic :: System :: Distributed Computing',
    ],
    project_urls={
        'Bug Reports': 'https://github.com/project-codeflare/rayvens/issues',
        'Source': 'https://github.com/project-codeflare/rayvens',
    },
)
