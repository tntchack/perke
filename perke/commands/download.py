from io import BytesIO
from os.path import dirname, join
from zipfile import ZipFile

import requests
import typer
from github import Github
from github.GitReleaseAsset import GitReleaseAsset

from perke.commands.base import app


def get_latest_resources_asset() -> GitReleaseAsset:
    """
    Searches through hazm releases and find latest release that contains
    resources.

    Returns
    -------
    asset: GitReleaseAsset
        The resources asset
    """
    g = Github()
    repo = g.get_repo('sobhe/hazm')
    for release in repo.get_releases():
        for asset in release.get_assets():
            if asset.name.startswith(f'resources-{release.tag_name[1:]}'):
                return asset


def download_and_extract_asset(asset: GitReleaseAsset,
                               extract_path: str,
                               ) -> None:
    """
    Downloads a github asset file and extract it.

    Parameters
    ----------
    asset: `GitReleaseAsset`
        The github asset to be downloaded

    extract_path: `str`
        The extract path for the downloaded file to be extracted
    """
    chunk_size = 1024*1024
    with typer.progressbar(length=asset.size,
                           label='Downloading resources ...') as progress:
        with requests.get(url=asset.browser_download_url,
                          stream=True) as r:
            with BytesIO() as io_file:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    io_file.write(chunk)
                    progress.update(chunk_size)
                with ZipFile(io_file) as zip_file:
                    zip_file.extractall(path=extract_path)
    typer.echo('Download completed.')


@app.command()
def download() -> None:
    """
    Download latest resources (tagger and parser models) that Perke
    needs.
    """
    asset = get_latest_resources_asset()
    extract_to = join(dirname(dirname(__file__)), 'resources')
    download_and_extract_asset(asset, extract_to)
