import json
from dataclasses import asdict
import os
from typing import Any


class DataclassJSONEncoder(json.JSONEncoder):
	def default(self, o: Any) -> Any:
		if hasattr(o, '__dataclass_fields__'):
			return asdict(o)
		if isinstance(o, BaseException):
			return str(o)
		try:
			return super().default(o)
		except TypeError:
			return str(o)


def custom_json_dumps(obj: Any) -> str:
	return json.dumps(obj, cls=DataclassJSONEncoder)

def sigchld_handler(signum: int, frame: Any) -> None:
	"""Reap zombie processes."""
	while True:
		try:
			pid, status = os.waitpid(-1, os.WNOHANG)
			if pid == 0:
				break
		except ChildProcessError:
			break

