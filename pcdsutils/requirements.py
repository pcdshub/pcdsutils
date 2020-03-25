import argparse
import logging
import pathlib
import re
import yaml


logger = logging.getLogger(__name__)


PIP_REQUIREMENT_FILES = {
    'requirements.txt': ('host', 'build', 'run'),
    'dev-requirements.txt': ('test', ),
    # 'docs-requirements.txt': 'build',  # ?
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
        'test': test.get('requires', []),
    }


def get_pip_requirements(repo_root):
    requirements = {}
    for filename, requirement_key in PIP_REQUIREMENT_FILES.items():
        req_file = repo_root / filename
        if req_file.exists():
            with open(req_file, 'rt') as f:
                requirements[requirement_key] = [
                    req.strip() for req in f.read().splitlines()
                    if req.strip()
                ]

    return requirements


def get_dependency_name(dependency):
    return RE_DEPENDENCY_NAME.match(dependency).groups()[0]


def requirements_from_conda(repo_root, ignore_deps=None):
    ignore_deps = ignore_deps or {'python', 'pip', 'setuptools'}
    requirements = find_conda_deps(repo_root)
    ret = {}
    for category_key, deps in requirements.items():
        ret[category_key] = [dep for dep in deps
                             if get_dependency_name(dep) not in ignore_deps
                             ]

    return ret


def write_requirements(repo_root, conda_deps):
    for req_file, conda_keys in PIP_REQUIREMENT_FILES.items():
        deps_for_file = set()
        for key in conda_keys:
            for dep in conda_deps.get(key, []):
                dep_name = get_dependency_name(dep)
                if dep_name in CONDA_NAME_TO_PYPI_NAME:
                    dep = dep.replace(dep_name,
                                      CONDA_NAME_TO_PYPI_NAME[dep_name])
                deps_for_file.add(dep)

        if deps_for_file:
            logger.info('Writing requirements file in repo %s: %s', repo_root,
                        req_file)
            with open(repo_root / req_file, 'wt') as f:
                for dep in deps_for_file:
                    print(dep, file=f)


def _requirements_from_conda():
    logging.basicConfig()
    parser = argparse.ArgumentParser()
    parser.description = 'Build requirements.txt files from conda meta.yaml'

    parser.add_argument(
        'REPO_ROOT',
        type=str,
        help='Repository root path',
    )

    args = parser.parse_args()
    repo_root = pathlib.Path(args.REPO_ROOT)
    conda_deps = requirements_from_conda(repo_root=repo_root)
    write_requirements(repo_root, conda_deps)
