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

import argparse

from rayvens.cli.build import build_integration, build_base_image
from rayvens.cli.run import run_integration
from rayvens.cli.rayvens_setup import rayvens_setup
from rayvens.cli.rayvens_print import rayvens_print
from rayvens.cli.delete import delete

parser = argparse.ArgumentParser(description='Rayvens command line tool.',
                                 prog="rayvens")

# Add sub-parsers
subparsers = parser.add_subparsers()

# =============================
# Build base image sub-command:
# =============================
parser_base = subparsers.add_parser(
    'base', help='Build base image used for all integrations.')
parser_base.add_argument('--dev',
                         action='store_true',
                         help='Use local registry localhost:5000.')
parser_base.add_argument('-r', '--registry', help='Image registry.')
parser_base.set_defaults(func=build_base_image)

# =============================
# Build image sub-command:
# =============================
parser_build = subparsers.add_parser('build',
                                     help='Build an integration image.')
parser_build.add_argument(
    '-k', '--kind', help='Integration predefined type (e.g. slack-sink).')
parser_build.add_argument('--generic-source',
                          help='Source integration generic endpoint.')
parser_build.add_argument('--generic-sink',
                          help='Sink integration generic endpoint.')
parser_build.add_argument(
    '-p',
    '--properties',
    nargs='*',
    help='Specify the name of a property or list of properties the '
    'integration should have. The properties are specified as '
    '`-p prop1=value1 prop2=value2`')

parser_build.add_argument(
    '-e',
    '--envvars',
    nargs='*',
    help='Specify the environment variable behind an integration property '
    'specified as '
    '`-e prop1=ENV_VARIABLE_1 prop2=ENV_VARIABLE_2`')

parser_build.add_argument('--dev',
                          action='store_true',
                          help='Use local registry localhost:5000.')
parser_build.add_argument('-r', '--registry', help='Image registry.')
parser_build.add_argument('-i', '--image', help='Image name.')
parser_build.add_argument(
    '-l',
    '--launch-image',
    help='Enable the launching of a job with the provided image each time '
    'an event is received. This option only makes sense for sources.')
parser_build.set_defaults(func=build_integration)

# =============================
# Run image sub-command:
# =============================
parser_run = subparsers.add_parser(
    'run', help='Run a previously built integration image.')
parser_run.add_argument(
    '-p',
    '--properties',
    nargs='*',
    help='Specify the name of a property or list of properties the '
    'integration should have. The properties are specified as '
    '`-p prop1=value1 prop2=value2`')
parser_run.add_argument(
    '-e',
    '--envvars',
    nargs='*',
    help='Specify the environment variable behind an integration property '
    'specified as '
    '`-e prop1=ENV_VARIABLE_1 prop2=ENV_VARIABLE_2`')

parser_run.add_argument('--dev',
                        action='store_true',
                        help='Use local registry localhost:5000.')
parser_run.add_argument('-r', '--registry', help='Image registry.')
parser_run.add_argument('-i', '--image', help='Image registry.')
parser_run.add_argument('-d',
                        '--deploy',
                        action='store_true',
                        help='Deploy integration on Kubernetes.')
parser_run.add_argument(
    '-n',
    '--namespace',
    help='Kubernetes namespace used for deploying the integration.')
parser_run.add_argument('--name',
                        help='Kubernetes name used for the integration.')
parser_run.add_argument('--handler-image',
                        help='Name of the job image used for handling events.')
parser_run.add_argument('--handler-name',
                        help='Name of the job used for handling events.')
parser_run.set_defaults(func=run_integration)

# =============================
# Setup sub-command:
# =============================
parser_setup = subparsers.add_parser('setup', help='Rayvens setup.')
parser_setup.add_argument('--dev', help='Setup Rayvens in dev mode.')
parser_setup.set_defaults(func=rayvens_setup)

# =============================
# Print sub-command:
# =============================
parser_print = subparsers.add_parser('print',
                                     help='List details about integrations.')
parser_print.add_argument('--all',
                          action='store_true',
                          help='List all predefind integration types.')
parser_print.add_argument('-k',
                          '--kind',
                          help='List requirements for this integration.')
parser_print.set_defaults(func=rayvens_print)

# =============================
# Delete sub-command:
# =============================
parser_delete = subparsers.add_parser('delete', help='Delete deployments.')
parser_delete.add_argument('--name', help='Integration name.')
parser_delete.add_argument('-n', '--namespace', help='Deployment namespace.')
parser_delete.add_argument('--all-jobs',
                           help="Delete all jobs with the provided base name.")
parser_delete.set_defaults(func=delete)

args = parser.parse_args()
args.func(args)
