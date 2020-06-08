import pathlib
import pytest
import pcdsutils.requirements


PCDSUTILS_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(params=[str(PCDSUTILS_ROOT)])
def repo_root(request):
    return request.param


def test_compare_requirements(repo_root):
    pcdsutils.requirements._compare_requirements(
        args=['-v', repo_root]
    )


def test_compare_requirements_ignore_docs(repo_root):
    pcdsutils.requirements._compare_requirements(
        args=['--ignore-docs', repo_root]
    )


def test_requirements_from_conda(repo_root):
    pcdsutils.requirements._requirements_from_conda(
        args=['-v', '--dry-run', repo_root]
    )
