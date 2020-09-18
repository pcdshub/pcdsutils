"""
Release notes generation tool.

Create RST-compatible release notes from GitHub releases.
"""

import argparse
import re
import sys
from typing import Dict, List

import pypandoc
import requests

ISSUE_RE = re.compile(r'#(\d+)')
DESCRIPTION = __doc__


def generate_releases(organization: str,
                      repository: str,
                      releases: List[dict],
                      *, file=sys.stdout):
    """
    Generate the release notes.

    Parameters
    ----------
    organization : str
        The organization (e.g., pcdshub).

    repository : str
        The repository (e.g., lucid).

    releases : list of dict
        Releases from the GitHub API.

    file : file-like object, optional
        Where to write the release notes.
    """
    repo_url = f'https://github.com/{organization}/{repository}'
    print('''\
=================
 Release History
=================

''', file=file)

    for release in releases:
        release['created_at'] = str(release['created_at'])[:10]
        header = '{tag_name} ({created_at})'.format(**release)
        print(header, file=file)
        print('=' * len(header), file=file)
        print(file=file)
        body, _ = ISSUE_RE.subn(fr'[#\1]({repo_url}/issues/\1)',
                                release['body'])
        print(pypandoc.convert_text(body, to='rst', format='md',
                                    extra_args=[]),
              file=file)
        print(file=file)


def get_releases(organization: str, repository: str) -> List[Dict]:
    """
    Generate the release notes.

    Parameters
    ----------
    organization : str
        The organization (e.g., pcdshub).

    repository : str
        The repository (e.g., lucid).

    Returns
    -------
    releases : list of dict
        List of dictionaries with release information.
    """
    req = requests.get(
        f'https://api.github.com/repos/{organization}/{repository}/releases'
    )

    if req.status_code != 200:
        sys.exit(f'Request failed with error code: {req.status_code}')

    return req.json()


def create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('organization', type=str)
    parser.add_argument('repository', type=str)
    return parser


def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    releases = get_releases(args.organization, args.repository)
    generate_releases(args.organization, args.repository, releases)


if __name__ == '__main__':
    main()
