#!/usr/bin/env python2
# -*- encoding: utf8 -*-
#

import argparse
import shell
from bundle import Bundle, PATH

DEFAULT_VERBOSITY=shell.QUIET

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', dest='filename', default='site.yml',
                        help='YML file to be processed (default:site.yml)')
    parser.add_argument('--run', action='store_true', dest='run_playbook',
                        default=False,
                        help='Runs ansible-playbook with default params' +
                        ' after getting bundles')
    parser.add_argument('--args', dest='args', nargs='?',
                        help='ansible-playbook arguments, if needed. Must be' +
                        ' put into quotes')
    parser.add_argument('--clean', action='store_true', default=False,
                        help='clean roles and libraries directories')
    parser.add_argument('-v', '--verbose', action='count', default=DEFAULT_VERBOSITY,
                        help='Be verbose on tasks')

    return parser.parse_args()


def get_dependencies_tree(pathDir):
    deps = list()
    for (directory, _, filenames) in shell.walk(pathDir):
        for filename in filenames:
            path = shell.path(directory, filename)
            if 'meta/main.yml' in path:
                deps += get_bundles_from(shell.load(path))
    return list(set(deps))


def get_bundles_from(yml):
    bundles = list()
    for bundle in yml.get('roles', list()):
        b = Bundle('role', bundle)
        bundles.append(b)
    for bundle in yml.get('dependencies', list()):
        if bundle.get('role', None):
            b = Bundle('role', bundle)
            bundles.append(b)
    return bundles


def load_bundles(filename):
    if filename is None: return list()
    if not shell.isfile(filename):
        raise Exception('File %s not found' % filename)
    bundlelist=list()
    yml = shell.load(filename)
    for item in yml:
        bundlelist += load_bundles(item.get('include', None)) +\
                      get_bundles_from(item)
    return bundlelist

def purify(array):
    elements = list()
    pure = list()
    for item in array:
        element = (item.name, item.version)
        if element not in elements:
            pure.append(item)
            elements.append(element)
    return pure


def download(filename, verbose=DEFAULT_VERBOSITY):
    bundles = purify(load_bundles(filename))
    already_downloaded = list()
    while len(bundles) > 0:
        for bundle in bundles:
            bundles.remove(bundle)
            if bundle.download(verbose=verbose) is True:
                already_downloaded.append((bundle.name, bundle.version))
            else:
                return shell.ERROR
        dependencies = get_dependencies_tree(
            PATH['role']) + get_dependencies_tree(PATH['library'])
        bundles = [item for item in bundles if (item.name, item.version) not in already_downloaded] + \
            [item for item in dependencies if (item.name, item.version) not in already_downloaded]


def run_playbook(filename, args):
        ansiblecmd = ['ansible-playbook', filename] + args
        shell.echo('Running', typeOf='info', lr=False)
        shell.echo(shell.Color.text(' '.join(ansiblecmd), decoration='bold'))
        shell.call(ansiblecmd)


def clean_dirs(directories):
    for directory in directories:
        shell.echo('Cleaning %s directory...' %directory,
                   typeOf='info', lr=False)
        if shell.rmdir('roles') is True:
            shell.echo('OK', typeOf='ok')
        else:
            shell.echo('ERROR', typeOf='error')



def main():
    global VERBOSITY
    params = get_arguments()

    if params.clean is True:
        clean_dirs(['roles'])

    download(
            filename=params.filename, 
            verbose=params.verbose
            )

    # After getting bundles, run playbook if set to
    if params.run_playbook is True:
        run_playbook(params.filename,
                     params.args.split() if params.args else list()
                    )

########################################################
if __name__ == "__main__":
    shell.exit(main())
