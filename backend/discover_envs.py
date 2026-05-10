import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from enironment import Environment, SharedStateHolder
from steps.step import CachingStep

logger = logging.getLogger(__name__)

@dataclass
class ParsedEnvArgs:
	excludes: List[str] = field(default_factory=list)
	includes: Dict[str, Optional[str]] = field(default_factory=dict)


def parse_arguments(cli_env_ids_str: str) -> ParsedEnvArgs:
	logger.info(f"cli_env_ids {cli_env_ids_str}")
	if len(cli_env_ids_str) > 0 and cli_env_ids_str[0] == '-':
		excludes = [x for x in cli_env_ids_str[1:].split(',') if len(x) > 0]
		logger.info(f"cli_env_ids (minus) {excludes}")
		return ParsedEnvArgs(excludes=excludes)

	includes: Dict[str, Optional[str]] = {
		x[0]: x[1] if len(x) > 1 else None
		for x in [x.split(":") for x in cli_env_ids_str.split(',') if len(x) > 0]
	}
	logger.info(f"cli_env_ids {includes}")
	return ParsedEnvArgs(includes=includes)


def _discover_environments() -> Dict[str, Environment]:
	import configs
	found: Dict[str, Environment] = {}
	seen: set[int] = set()
	for module_info in pkgutil.iter_modules(configs.__path__, prefix=f"{configs.__name__}."):
		module = importlib.import_module(module_info.name)
		for value in vars(module).values():
			if isinstance(value, Environment) and id(value) not in seen:
				seen.add(id(value))
				found[value.id] = value
	return found


def build_environments(cli_env_ids_str: str) -> Dict[str, Environment]:
    environments: Dict[str, Environment] = _discover_environments()
    args: ParsedEnvArgs = parse_arguments(cli_env_ids_str)

    if args.excludes:
        environments = {k: e for k, e in environments.items() if k not in args.excludes}
    elif args.includes:
        environments = {k: e for k, e in environments.items() if k in args.includes}
        for k, v in args.includes.items():
            if v is None:
                logger.info(f"No branch override for environment {k}")
                continue
            if k not in environments:
                logger.warning(f"Environment {k} not found to override branches")
                continue
            env = environments[k]
            for step in env.pipeline:
                resolve_step = step
                if isinstance(step, CachingStep):
                    resolve_step = step._step
                if isinstance(resolve_step, SharedStateHolder):
                    resolve_step.set_branches([(v, 'HEAD')])
            logger.info(f"Overriding environment {k} branches to {(v, 'HEAD')}")

    logger.info(f"Resulting profiles {environments.keys()}")
    return environments
