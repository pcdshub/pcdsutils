import argparse
import logging
import pathlib
import re
import yaml


logger = logging.getLogger(__name__)


PIP_REQUIREMENT_FILES = {
    'requirements.txt': ('host', 'build', 'run'),
    'dev-requirements.txt': ('test', ),
    'docs-requirements.txt': ('docs', ),
}

RE_DEPENDENCY_NAME = re.compile(r'^([a-z0-9_-]+)\s*([><=]?.*)$', re.IGNORECASE)
CONDA_NAME_TO_PYPI_NAME = {'pyqt': 'pyqt5'}


def find_meta_yaml(repo_root):
    'Find conda meta.yaml in a repository'
    metayaml = repo_root / 'conda-recipe' / 'meta.yaml'
    if metayaml.exists():
        return metayaml

    matches = list(repo_root.glob('**/meta.yaml'))
    if len(matches) == 0:
        raise ValueError('meta.yaml not found in the repository')
    if len(matches) > 1:
        raise ValueError('Multiple meta.yaml files found in the repository')
    return matches[0]


def find_conda_deps(repo_root):
    'Get conda-recipe meta.yaml requirements as a dictionary from a repo'
    metayaml = find_meta_yaml(repo_root)
    with open(metayaml, 'rt') as f:
        text = f.read()

    # Remove conda-forge specific yaml syntax:
    text = re.sub(r'{%[^%]+%}', '', text)
    text = re.sub(r'{{[^}]+}}', 'FIXME', text)
    meta = yaml.load(text, Loader=yaml.FullLoader)

    requirements = meta.get('requirements', {})
    test = meta.get('test', {})

    return {
        'host': requirements.get('host', []),
        'build': requirements.get('build', []),
        'run': requirements.get('run', []),
        'docs': requirements.get('docs', []),
        'test': test.get('requires', []),
    }


def get_pip_requirements(repo_root):
    'Get pip requirements from a repo'
    requirements = {fn: [] for fn in PIP_REQUIREMENT_FILES}
    for filename, requirement_key in PIP_REQUIREMENT_FILES.items():
        req_file = repo_root / filename
        if req_file.exists():
            with open(req_file, 'rt') as f:
                requirements[filename] = [
                    req.strip() for req in f.read().splitlines()
                    if req.strip()
                ]
            logger.debug('Found pip requirements file: %s with deps: %s',
                         req_file, requirements[filename])

    return requirements


def get_dependency_name(dependency):
    '''
    Dependency line to dependency name

    Example::

        >>> print(get_dependency_name('python>=3.6'))
        python
    '''
    if dependency.lstrip() and dependency.lstrip()[0] == '#':
        # A comment
        return ''

    return RE_DEPENDENCY_NAME.match(dependency).groups()[0]


def requirements_from_conda(repo_root, ignore_deps=None):
    'Build pip-style requirements from conda-recipe meta.yaml'
    ignore_deps = ignore_deps or {'python', 'pip', 'setuptools'}
    requirements = find_conda_deps(repo_root)
    ret = {}
    for category_key, deps in requirements.items():
        ret[category_key] = [dep for dep in deps
                             if get_dependency_name(dep) not in ignore_deps
                             and get_dependency_name(dep).strip()
                             ]

    return ret


def _combine_conda_deps(deps, keys):
    'Combine conda dependencies from multiple keys'
    ret = set()
    for key in keys:
        for dep in deps.get(key, []):
            dep_name = get_dependency_name(dep)
            if not dep_name:
                continue
            if dep_name in CONDA_NAME_TO_PYPI_NAME:
                dep = dep.replace(dep_name, CONDA_NAME_TO_PYPI_NAME[dep_name])
            ret.add(dep)
    return ret


def write_requirements(repo_root, conda_deps, *, dry_run=True):
    'Write pip requirements to the repository root from conda requirements'
    for req_file, conda_keys in PIP_REQUIREMENT_FILES.items():
        deps_for_file = _combine_conda_deps(conda_deps, conda_keys)
        if deps_for_file:
            logger.info('Writing requirements file in repo %s: %s', repo_root,
                        req_file)

            if dry_run:
                logger.info('Dry-run mode. Write %s:', repo_root / req_file)
                for dep in deps_for_file:
                    logger.info('%s', dep)
            else:
                with open(repo_root / req_file, 'wt') as f:
                    for dep in deps_for_file:
                        print(dep, file=f)


def _requirements_from_conda(args=None):
    '(Console entry-point)'
    parser = argparse.ArgumentParser()
    parser.description = 'Build requirements.txt files from conda meta.yaml'
    parser.add_argument('REPO_ROOT', type=str, help='Repository root path')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not write the files')
    args = parser.parse_args(args=args)
    logging.basicConfig(level='DEBUG' if args.verbose else 'INFO',
                        format='%(message)s')

    repo_root = pathlib.Path(args.REPO_ROOT)
    conda_deps = requirements_from_conda(repo_root=repo_root)
    write_requirements(repo_root, conda_deps, dry_run=args.dry_run)


def compare_requirements(conda_deps, pip_deps):
    'Compare two lists of dependencies'
    conda_deps = set(dep.replace(' ', '') for dep in conda_deps)
    conda_deps_name = {get_dependency_name(dep): dep
                       for dep in conda_deps
                       }
    pip_deps = set(pip_deps)
    pip_deps_name = {get_dependency_name(dep): dep
                     for dep in pip_deps
                     if get_dependency_name(dep)
                     }

    logger.debug('Found conda deps: %s', list(sorted(set(conda_deps_name))))
    logger.debug('Found pip deps: %s', list(sorted(set(pip_deps_name))))
    missing_in_pip = set(conda_deps_name) - set(pip_deps_name)
    missing_in_conda = set(pip_deps_name) - set(conda_deps_name)
    version_mismatch = [
        dict(conda=conda_deps_name[dep], pip=pip_deps_name[dep])
        for dep in conda_deps_name
        if dep not in missing_in_pip
        and conda_deps_name[dep] != pip_deps_name[dep]
    ]

    return {
        'missing_in_pip': missing_in_pip,
        'missing_in_conda': missing_in_conda,
        'version_mismatch': version_mismatch,
    }


def _compare_requirements(args=None):
    '(Console entry-point)'
    parser = argparse.ArgumentParser()
    parser.description = 'Compare requirements.txt files with conda meta.yaml'
    parser.add_argument('REPO_ROOT', type=str, help='Repository root path')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Increase verbosity')
    parser.add_argument('--ignore-docs', action='store_true',
                        help='Ignore documentation differences')
    args = parser.parse_args(args=args)
    logging.basicConfig(level='DEBUG' if args.verbose else 'INFO',
                        format='%(message)s')

    repo_root = pathlib.Path(args.REPO_ROOT)
    conda_deps = requirements_from_conda(repo_root=repo_root)
    pip_deps = get_pip_requirements(repo_root=repo_root)
    has_diff = False
    for fn, conda_keys in PIP_REQUIREMENT_FILES.items():
        logger.info('--- %s: %s ---', fn, '/'.join(conda_keys))
        cdeps = _combine_conda_deps(conda_deps, conda_keys)
        pdeps = pip_deps[fn]
        logger.debug('Comparing dependencies. cdeps=%s pdeps=%s', cdeps, pdeps)
        for name, difference in compare_requirements(cdeps, pdeps).items():
            if difference:
                if not ('docs' in fn and args.ignore_docs):
                    has_diff = True
                display_name = name.replace('_', ' ').capitalize()
                logger.info('%s:', display_name)
                for item in sorted(difference):
                    if isinstance(item, dict):
                        pretty_diff = ' | '.join(f'{k}: {v}'
                                                 for k, v in item.items())
                        logger.info('- %s', pretty_diff)
                    else:
                        logger.info('- %s', item)
                logger.info('')
    return 1 if has_diff else 0
