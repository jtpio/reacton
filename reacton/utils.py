import functools
import inspect
import sys
import types
from typing import Callable, TypeVar, cast

import ipywidgets as widgets
import typing_extensions

P = typing_extensions.ParamSpec("P")
T = TypeVar("T")


def without_default(func: Callable, kwargs):
    sig = inspect.signature(func)
    {name: param.default for name, param in sig.parameters.items()}
    non_default_kwargs = {name: kwargs[name] for name, param in sig.parameters.items() if kwargs[name] is not param.default}
    return non_default_kwargs


def implements(f: Callable[P, T]):
    def caster(fimpl: Callable) -> Callable[P, T]:
        # wraps gives us the right signature at runtime (such as Jupyter)
        return cast(Callable[P, T], functools.wraps(f)(fimpl))

    return caster


def wrap(mod, globals):
    from .core import component

    for cls_name in dir(mod):
        cls = getattr(mod, cls_name)
        if inspect.isclass(cls) and issubclass(cls, widgets.Widget):
            globals[cls_name] = component(cls)


def equals(a, b):
    from reacton.core import Element, same_component

    if a is b:
        return True
    if type(a) != type(b):  # is this always true? after a == b failed?
        return False
    if isinstance(a, Element):
        return same_component(a.component, b.component) and equals(a.args, b.args) and equals(a.kwargs, b.kwargs)
    elif isinstance(a, types.FunctionType):
        return a.__code__ == b.__code__ and (
            (equals(a.__closure__, b.__closure__)) or equals([c.cell_contents for c in a.__closure__ or ()], [c.cell_contents for c in b.__closure__ or ()])
        )
    elif isinstance(a, dict) and isinstance(b, dict):
        if len(a) != len(b):
            return False
        for key in a:
            if key not in b:
                return False
            if not equals(a[key], b[key]):
                return False
        return True
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if not equals(a[i], b[i]):
                return False
        return True
    try:
        return bool(a == b)
    except Exception:
        pass
    return False


def import_item(name: str):
    """Import an object by name like pandas.DataFrame if the module is imported, else return None"""
    parts = name.rsplit(".", 1)
    if len(parts) == 1:
        return sys.modules.get(name)
    else:
        module = sys.modules.get(parts[0])
        if module is None:
            return None
        return getattr(module, parts[-1])


def isinstance_lazy(value, types):
    if not isinstance(types, (list, tuple)):
        types = [types]
    types = [import_item(t) if isinstance(t, str) else t for t in types]
    for type in types:
        if type is not None and isinstance(value, type):
            return True
    return False


def dataframe_fingerprint(df):
    return {"index": id(df.index), **{column: id(df[column]) for column in df.columns}}


def not_equals(a, b):
    return a != b
    if a is None and b is not None:
        return True
    if a is not None and b is None:
        return True
    if a is b:
        return False

    def numpyish(obj):
        import sys

        if "pandas" in sys.modules:
            import pandas as pd

            if isinstance(obj, pd.Series):
                return True
        if "numpy" in sys.modules:
            import numpy as np

            if isinstance(obj, np.ndarray):
                return True
        return False

    if numpyish(a) or numpyish(b):
        return (a != b).any()
    else:
        return a != b


def environment() -> str:
    try:
        module = get_ipython().__module__  # type: ignore
        shell = get_ipython().__class__.__name__  # type: ignore
    except NameError:
        return "python"  # Probably standard Python interpreter
    else:
        if module == "google.colab._shell":
            return "colab"
        elif shell == "ZMQInteractiveShell":
            return "jupyter"  # Jupyter notebook, lab or qtconsole
        elif shell == "TerminalInteractiveShell":
            return "ipython"  # Terminal running IPython
        else:
            return "unknown"  # Other type
