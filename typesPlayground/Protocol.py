from typing import Dict, List, runtime_checkable, Protocol


@runtime_checkable
class C1(Protocol):
	version: str


@runtime_checkable
class C2(Protocol):
	data: Dict[str, C1]


class C3(Protocol):
	data1: List[C1]


class C2_C3(C2, C3):
	pass


# Concatenate
class CM:
	def __init__(self, arg1: C2, arg2: C3, arg3: C2 | C3, arg4: C2_C3) -> None:
		pass


v2: C2 = {"data": {"service1": {"version": "1.0"}}}
v3: C3 = {"data1": [{"version": "1.0"}, {"version": "2.0"}]}
v2_v3_1: C2_C3 = {
	"data": {"service2": {"version": "2.0"}},
	"data1": [{"version": "1.0"}, {"version": "2.0"}],
}
# v2_v3_2: C2 | C3 = {
# 	"data": {"service2": {"version": "2.0"}},
# 	"data1": [{"version": "1.0"}, {"version": "2.0"}],
# }
v2_v3_3: C2 | C3 = v2
v2_v3_4: C2 | C3 = v3
CM(
	arg1=v2,
	arg2=v3,
	arg3=v2_v3_3,
	arg4=v2_v3_1,
)
