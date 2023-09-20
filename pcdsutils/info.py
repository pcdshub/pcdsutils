#!/usr/bin/env python

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import socket
import sys
from typing import Dict, List, Optional

import requests

WS_URL = "https://pswww.slac.stanford.edu/ws/lgbk"
DATA_PATH = "/cds/group/psdm/"
UNKNOWN_HUTCH = "unknown_hutch"

HUTCHES = [
    "tmo",
    "txi",
    "rix",
    "xpp",
    "xcs",
    "mfx",
    "cxi",
    "mec",
    "ued",
    "det",
    "lfe",
    "kfe",
    "tst",
    "las",
    "hpl",
]

# populate hutch-specific subnets here:
HUTCH_SUBNETS = {
    "tmo": ["28", "132", "133", "134", "135"],
    "txi": ["29", "136", "137", "138", "139"],
    "rix": ["31", "144", "145", "146", "147"],
    "xpp": ["22", "84", "85", "86", "87"],
    "xcs": ["25", "80", "81", "82", "83"],
    "cxi": ["26", "68", "69", "70", "71"],
    "mfx": ["24", "72", "73", "74", "75"],
    "mec": ["27", "76", "77", "78", "79"],
    "ued": ["36"],
    "det": ["58", "59"],
    "lfe": ["88", "89", "90", "91"],
    "kfe": ["92", "93", "94", "95"],
    "tst": ["23", "148", "149", "150", "151"],
    "las": ["35", "160", "161", "162", "163"],
    "hpl": ["64"],
}


@dataclasses.dataclass
class ProgramArguments:
    """Argparse arguments for get-info-json."""
    #: The hutch name.
    hutch: Optional[str] = None
    #: The station number.
    station: Optional[int] = None
    #: This is used when the user is asking for what the most recent run number
    #: is and they don't want to include the current run if it is still
    #: in-progress.
    ended: bool = False
    #: The user-provided experiment name.
    experiment: Optional[str] = None


@dataclasses.dataclass
class _LogbookInfo:
    """
    Base dataclass to help with retrieving logbook information and transforming
    it into a dataclass.

    Subclasses should add the required fields for deserializing the given
    request.
    """

    #: Is this valid information, according to the logbook API?
    valid: bool = False

    @classmethod
    def _response_to_instance(cls, response: Optional[dict]):
        if response is None:
            return cls()

        fields = dataclasses.fields(cls)
        info = response.get("value", {}) or {}
        kwargs = {field.name: info.get(field.name, "") for field in fields}
        kwargs["valid"] = response.get("success", False)
        return cls(**kwargs)


@dataclasses.dataclass
class Experiment(_LogbookInfo):
    """Experiment information."""
    #: The experiment name.
    name: str = ""
    #: The experiment description.
    description: str = ""
    #: The experiment start time.
    start_time: str = ""
    #: The experiment end time.
    end_time: str = ""
    #: The lead account information.
    leader_account: str = ""
    #: The lead contact information.
    contact_info: str = ""
    #: The posix group of the experiment.
    posix_group: str = ""
    #: Experiment parameter information.
    params: Dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_logbook(
        cls,
        instrument: Instrument,
        experiment_name: Optional[str] = None,
    ) -> Experiment:
        """
        Get Experiment information given an instrument/experiment name.

        Parameters
        ----------
        instrument : Instrument
            The instrument instance.

        experiment_name : str, optional
            Experiment name. Defaults to the active experiment.
        """
        # TODO: how do we get information about a given experiment?
        try:
            resp = requests.get(
                WS_URL + "/lgbk/ws/activeexperiment_for_instrument_station",
                dict(
                    instrument_name=instrument.hutch,
                    station=instrument.station
                ),
            ).json()
        except Exception:
            return cls()

        return cls._response_to_instance(resp)


@dataclasses.dataclass
class RunFiles(_LogbookInfo):
    """For a given run, information about the files generated."""
    files: List[str] = dataclasses.field(default_factory=list)
    num_files: int = 0

    @classmethod
    def from_logbook(cls, experiment: Experiment, run: Run) -> RunFiles:
        """
        Get RunFile information given an experiment/run, queried from the
        logbook.

        Parameters
        ----------
        experiment : Experiment
            The experiment instance.

        run : Run
            The Run instance.
        """
        try:
            resp = requests.get(
                f"{WS_URL}/lgbk/{experiment.name}"
                f"/ws/{run.num}/files_for_live_mode"
            )
            info = resp.json()
        except Exception:
            return RunFiles(valid=False)

        valid = info.get("success", False)
        files = [DATA_PATH + fn.lstrip("/") for fn in info.get("value", [])]
        run_files = RunFiles(valid=valid, files=files)
        run_files.num_files = cls._get_num_files(run_files.files)
        return run_files

    @staticmethod
    def _get_num_files(files: List[str]) -> int:
        """
        Get the number of files in this run.

        Some are filtered, as per Silke:
        > s0x are the nominal data streams (for LCLS1). They start counting at 0,
        > so you already have s00, up to however many dss-nodes you used. s8x
        > would be IOC recorders. c0x are chunks: we start writing the c00-files
        > and when the file gets too big, it will be closed and a new file will
        > be opened. This is done by the DAQ stopping triggers for a bit & then
        > restarting them. This tripped up a scan at some point if I remember
        > right. With the jungfrau4M, CXI is the hutch mostly likely to chunk and
        > MEC rarely ever does.
        """
        num_files = 0
        for fn in files:
            if "c00" in fn and "-s8" not in fn:
                num_files += 1
        return num_files


@dataclasses.dataclass
class Run(_LogbookInfo):
    """Run information."""
    #: An in-progress run.
    live: bool = False
    #: The run number.
    num: int = 0
    #: The run type.
    type: str = ""
    #: The run start time.
    begin_time: str = ""
    #: The run end time.
    end_time: str = ""
    #: Run parameter dictionary.
    params: Dict[str, str] = dataclasses.field(default_factory=dict)
    #: Editable run parameter dictionary.
    editable_params: Dict[str, str] = dataclasses.field(default_factory=dict)
    #: Files for this run.
    files: RunFiles = dataclasses.field(default_factory=RunFiles)

    @classmethod
    def from_logbook(cls, experiment: Experiment) -> Run:
        """
        Get Run information given an experiment, queried from the logbook.

        Parameters
        ----------
        experiment : Experiment
            The experiment instance.
        """
        try:
            resp = requests.get(
                f"{WS_URL}/lgbk/{experiment.name}/ws/current_run"
            ).json()
        except Exception:
            return cls(valid=False)

        run = cls._response_to_instance(resp)
        run.live = bool(run.end_time)
        run.files = RunFiles.from_logbook(experiment, run)
        return run


@dataclasses.dataclass
class Instrument:
    """Per-instrument information."""
    #: The hutch name.
    hutch: str
    #: The daq base.
    daq_base: str = ""
    #: The instrument name.
    instrument: str = ""
    #: The station number.
    station: int = 0
    #: The daq configuration file name.
    config_filename: str = ""
    #: The total number of stations.
    nstations: int = 0
    #: Whether the station number is valid or not.
    station_valid: bool = False
    #: Experiment-related information.
    experiment: Experiment = dataclasses.field(default_factory=Experiment)
    #: Run-related information.
    run: Run = dataclasses.field(default_factory=Run)

    def fix_parameters(self, ended: bool = False) -> None:
        """
        Based on user-provided experimental state information, adjust the
        instrument information.

        Parameters
        ----------
        ended : bool, optional
            Has the run ended?
        """
        if ended:
            if not self.run.valid or not self.run.end_time:
                # Really bogus way to determine this; but copying over from
                # previous code.
                self.run.num -= 1

    @classmethod
    def from_hutch(
        cls, hutch: str, station: Optional[int] = None
    ) -> Instrument:
        """
        Get Instrument information given a hutch and (optional) station number.

        Parameters
        ----------
        hutch : str
            The hutch name.

        station : int, optional
            The station number.
        """
        info = cls(hutch=fix_hutch_name(hutch))

        # if hutch.lower() in ['mfx','cxi']:
        if hutch.lower() in ["cxi"]:
            info.nstations = 2
            if station is not None:
                info.station = int(station)
            elif is_monitor_host(socket.gethostname()):
                info.station = 1
            else:
                info.station = 0
            info.daq_base = f"{hutch.lower()}_{info.station}"
            info.instrument = f"{hutch.upper()}:{info.station}"
        elif hutch.lower() in ["rix"]:
            info.station = 2
        else:
            info.daq_base = hutch.lower()
            info.instrument = hutch.upper()
            info.nstations = 1
            if station:
                info.station = int(station)
            else:
                info.station = 0

        info.station_valid = not info._is_station_invalid()
        if info.daq_base:
            info.config_filename = f"{info.daq_base}.cnf"
        return info

    def update_from_logbook(self, experiment_name: Optional[str] = None):
        """
        Update information by querying the logbook.

        Parameters
        ----------
        experiment_name : str, optional
            Experiment name. Defaults to the active experiment.
        """
        self.experiment = Experiment.from_logbook(
            self, experiment_name=experiment_name
        )
        if self.experiment.valid:
            self.run = Run.from_logbook(self.experiment)
        else:
            self.run.valid = False

    def _is_station_invalid(self):
        return self.hutch.lower() != "rix" and self.station >= self.nstations


def _create_arg_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the get-info-json CLI entrypoint."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--hutch", help="get experiment for hutch xxx")
    parser.add_argument(
        "--station",
        help="optional station for hutch with two daqs, e.g. cxi and mfx"
    )
    parser.add_argument("--ended", help="ended", action="store_true")
    parser.add_argument("--setExp", "--experiment", help="set experiment name")
    return parser


def get_hutch_by_hostname(hostname: Optional[str] = None) -> str:
    """
    Given a hostname, get a hutch name.

    Parameters
    ----------
    hostname : str, optional
        If not specified, ``socket.gethostname()`` will be used.

    Returns
    -------
    hutch_name : str
        The hutch name or ``UNKNOWN_HUTCH``.
    """
    if hostname is None:
        hostname = socket.gethostname()

    try:
        ip = socket.gethostbyname(hostname)
    except Exception:
        return UNKNOWN_HUTCH

    # A.B.**C**.D - the C octet
    subnet = ip.split(".")[2]

    # use the IP address to match the host to a hutch by subnet
    # NOTE: this may look odd but it aims to replicate the existing
    # functionality in get_info as-is.
    for ihutch in HUTCHES:
        if subnet in HUTCH_SUBNETS.get(ihutch, []):
            return ihutch.upper()

    for ihutch in HUTCHES:
        if ihutch in hostname:
            return ihutch.upper()

    if "psusr13" in hostname:
        return "XPP"
    if "psusr21" in hostname:
        return "XCS"
    if "psusr22" in hostname:
        return "CXI"
    if "psusr23" in hostname:
        return "MEC"
    if "psusr24" in hostname:
        return "MFX"

    # then check current path
    path = os.getcwd()
    for ihutch in HUTCHES:
        if path.find(ihutch) >= 0:
            return ihutch.upper()

    # because we have so many names for the same subnet.
    xrt = "xrt" in path and "xrt" in hostname
    xtod = "xtod" in path and "xtod" in hostname
    if xrt or xtod:
        return "LFE"

    return UNKNOWN_HUTCH


def is_monitor_host(hostname: str) -> bool:
    """Is ``hostname`` a monitor host?"""
    return "monitor" in hostname


def fix_hutch_name(hutch: str) -> str:
    """
    Fix a user-provided hutch name.

    Returns
    -------
    hutch_name : str
        The canonical hutch name or ``UNKNOWN_HUTCH``.
    """
    if hutch in HUTCHES:
        return hutch.upper()

    for ihutch in HUTCHES:
        if hutch.find(ihutch.upper()) >= 0:
            return ihutch.upper()

    return UNKNOWN_HUTCH


def get_info(args: ProgramArguments) -> Optional[Instrument]:
    """
    Get top-level Instrument information given ``args``.

    Parameters
    ----------
    args : ProgramArguments
        Argparse or user-created program arguments.

    Returns
    -------
    instrument : Instrument or None
        The instrument information, if available.
    """
    if args.hutch:
        hutch = fix_hutch_name(args.hutch)
    else:
        hutch = get_hutch_by_hostname()

    if hutch == UNKNOWN_HUTCH:
        return None

    instrument = Instrument.from_hutch(hutch, args.station)
    instrument.fix_parameters(ended=args.ended)
    return instrument


def main():
    """Main entrypoint for get-info-json."""
    parser = _create_arg_parser()
    args = parser.parse_args(namespace=ProgramArguments())
    info = get_info(args)
    if info is None:
        sys.exit(1)

    info.update_from_logbook(args.experiment)
    print(json.dumps(dataclasses.asdict(info), indent=4))


if __name__ == "__main__":
    main()
