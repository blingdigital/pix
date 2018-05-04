"""
PIX class factory module.
"""
from typing import *


if TYPE_CHECKING:
    import pix.api
    import pix.model


T = TypeVar('T')


class Factory(object):
    """
    A Factory is repsonsible for dynamically building dict-like objects from
    the data returned from the PIX endpoints. Additionally these dynamically
    built objects can have base class(es) registered for them that can supply
    additional helper methods or behaviors. This allows for a more
    object-oriented interface and reduces the complexity of the large data
    structures returned from PIX.

    A base class for a given PIX class can be registered via the `register`
    method given the PIX class name. Any structure returned from a PIX request
    that contains dictionaries with a key 'class' is premoted to an object
    using any registered base classes (or ``pix.model.PIXObject`` if there are
    none registered).
    """
    # registered bases
    _registered = {}  # type: Dict[str, pix.model.PIXObject]

    def __init__(self, session):
        # type: (pix.api.Session) -> None
        """
        Parameters
        ----------
        session : pix.api.Session
        """
        self.session = session

    @classmethod
    def register(cls, name):
        # type: (str) -> Callable
        """
        Decorator for registering an new PIX base class.

        Parameters
        ----------
        name : str
            PIX class name. e.g. 'PIXImage'

        Returns
        -------
        Callable
        """
        def _deco(klass):
            bases = cls._registered.get(name, [])
            bases.append(klass)
            cls._registered[name] = bases
            return klass

        return _deco

    @classmethod
    def build(cls, name):
        # type: (str) -> type
        """
        Build a pix object class with the given name. Any registered bases
        keyed for `name` will be used or the base ``pix.model.PIXObject``
        class.

        Parameters
        ----------
        name : str
            PIX class name. e.g. 'PIXImage'

        Returns
        -------
        type
            Type[pix.model.PIXObject]
        """
        # this import here avoids circular import errors
        import pix.model
        # look for registered base classes and if none use the base object
        bases = cls._registered.get(str(name), [pix.model.PIXObject])
        obj = type(str(name), tuple(bases), {})
        obj.__name__ = str(name)
        return obj

    @classmethod
    def iter_contents(cls, data):
        # type: (Dict) -> Iterator[Dict]
        """
        Iter the immediate contents of `data` and yield any dictionaries.
        Does not recurse.

        Parameters
        ----------
        data : Dict

        Returns
        -------
        Iterator[Dict]
        """
        for k, v in data.items():
            if isinstance(v, dict):
                yield v
            elif isinstance(v, (set, list, tuple)):
                for l in v:
                    if isinstance(l, dict):
                        yield l

    def iter_children(self, data, recursive=True):
        # type: (Dict, bool) -> Iterator[pix.model.PIXObject]
        """
        Iterate over the children objects of `data`.

        Parameters
        ----------
        data : Dict
        recursive : bool
            Recursively look into generated objects and include their children
            too.

        Returns
        -------
        Iterator[pix.model.PIXObject]
        """
        name = data.get('class')
        if name:
            obj = self.build(name)
            yield obj(self, data)
        if recursive:
            for x in self.iter_contents(data):
                for obj in self.iter_children(x):
                    yield obj

    def objectfy(self, data):
        # type: (Union[Dict, T]) -> Union[pix.model.PIXObject, Dict, T]
        """
        Replace any viable structures with `pix.model.PIXObject`.

        Parameters
        ----------
        data : Union[Dict, T]

        Returns
        -------
        Union[pix.model.PIXObject, Dict, T]
        """
        if isinstance(data, dict):
            name = data.get('class')
            if name:
                obj = self.build(name)
                return obj(self, data)
            else:
                return {k: self.objectfy(v) for k, v in data.items()}
        elif isinstance(data, (tuple, list, set)):
            results = [self.objectfy(x) for x in data]
            if isinstance(data, tuple):
                results = tuple(results)
            elif isinstance(data, set):
                results = set(results)
            return results
        else:
            return data


# expose to make registration easier
# from pix.factory import register
register = Factory.register
