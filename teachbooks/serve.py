import pickle
import sys
import os
import socket
import platform
from subprocess import DEVNULL
from pathlib import Path
from typing import TypeVar
from time import sleep

import psutil

STATUS = {
    "Linux": "sleeping",
    "Darwin": "running",
    "Windows": "running"
}

Server_t = TypeVar("Server_t", bound="Server")


class ServerError(Exception):
    """Server exception class"""
    pass


class Server:
    """Class for managing a Python webserver in the background."""
    statefile = "state.pickle"

    def __init__(self, servedir: Path | str, workdir: Path | str, port: int | None = None) -> None:
        """Construct Server object

        Parameters
        ----------
        servedir : Path | str
            Directory to serve.
        workdir : Path | str
            Directory for temporary files.
        port : int | None, optional
            Port for server, by default None. If left empty, a free port will be
            chosen automatically.
        """
        self.servedir = Path(servedir)
        self.workdir = Path(workdir)
        self.port = port

        self._pid = None
        self._statepath = self.workdir / self.statefile

        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)


    def start(self) -> None:
        """Start server.

        Raises
        ------
        RuntimeError
            If server could not be started
        """
        if self.port is None:
            self.port = self._find_port()
        
        proc = psutil.Popen([sys.executable, "-u", "-m", "http.server", str(self.port)],
                            cwd=self.servedir,
                            stderr=DEVNULL,
                            stdout=DEVNULL)

        sleep(0.1)

        # Check if the subprocess is still running
        if proc.status() != STATUS[platform.system()]:
            proc.terminate()
            raise RuntimeError("Error launching the server. Perhaps a server is already running on the selected port?")
        else:
            self._pid = proc.pid
            self._save()


    def stop(self) -> None:
        """Stop server and clean up.
        """
        try:
            psutil.Process(pid=self._pid).terminate()
        except psutil.NoSuchProcess:
            pass

        if os.path.exists(self._statepath):
            os.remove(self._statepath)

        self._pid = None


    def _save(self) -> None:
        """Save current Server object as a pickle file.
        """
        with open(self._statepath, "wb") as f:
            pickle.dump(self, f)


    @property
    def url(self) -> str:
        """Get URL of running server.

        Returns
        -------
        str
            URL of the server.
        """
        return f"http://localhost:{self.port}"


    @staticmethod
    def _find_port() -> int:
        """Find open port.

        Returns
        -------
        int
            Port number.
        """
        # https://stackoverflow.com/a/1365284
        sock = socket.socket()
        sock.bind(('', 0))
        return sock.getsockname()[1]


    @classmethod
    def load(cls, workdir: Path | str) -> Server_t:
        """Construct a Server object from an existing pickle file.

        Parameters
        ----------
        workdir : Path | str
            Directory containing the pickle file.

        Returns
        -------
        Server
            Server object reconstructed from pickle file.

        Raises
        ------
        ServerError
            If pickle file cannot be found.
        """
        try:
            with open(workdir / cls.statefile, "rb") as f:
                server = pickle.load(f)
        except FileNotFoundError as exc:
            raise ServerError("Server information not found.") from exc
        return server
