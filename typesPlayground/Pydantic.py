import inspect
from typing import Dict, List, TypeVar

from pydantic import BaseModel, create_model


class C1(BaseModel):
	version: str


class C2(BaseModel):
	data: Dict[str, C1]


class C3(BaseModel):
	data1: List[C1]


class C2_C3(C2, C3):
	pass

A = TypeVar('A', bound=type[BaseModel])
B = TypeVar('B', bound=type[BaseModel])
C = TypeVar('C', bound=type[(BaseModel, A,B)])

def intersect(a: type[A], b: type[B]) -> type[C]:
	class C(BaseModel, a, b):
		pass

	return C


t: type = intersect(C2, C3)
t1: type[C2] = C2
DynamicModel = create_model("DynamicModel", __base__=(C2, C3))


# 	model_nam "DynamicModel",
# 	__base__=(C2, C3),
#
# )
# Concatenate
class CM:
	def __init__(self, arg1: C2, arg2: C3, arg3: C2 | C3, arg4: C2_C3, arg5: DynamicModel) -> None:
		print(arg1)
		print(arg2)
		print(arg3)
		print(arg4)
		print(arg5)



v2: C2 = C2(data={"service1": C1(version="1.0")})
v3: C3 = C3(data1=[C1(version="1.0"), C1(version="2.0")])
# v2_v3_1: C2_C3 = {
# 	"data": {"service2": {"version": "2.0"}},
# 	"data1": [{"version": "1.0"}, {"version": "2.0"}],
# }
# v2_v3_2: C2 | C3 = {
# 	"data": {"service2": {"version": "2.0"}},
# 	"data1": [{"version": "1.0"}, {"version": "2.0"}],
# }
v2_v3_3: C2 | C3 = v2
v2_v3_4: C2_C3 = C2_C3(**{**v2.model_dump(), **v3.model_dump()})
dynamic = DynamicModel(
	data={"service1": C1(version="1.0")},
	data1=[C1(version="1.0"), C1(version="2.0")],
)

v2 = dynamic
print(inspect.signature(C2_C3))
print(inspect.signature(DynamicModel))
CM(
	arg1=v2,
	arg2=v3,
	arg3=v2_v3_3,
	arg4=v2_v3_4,
	arg5=v2_v3_4
)
