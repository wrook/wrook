import logging
import pickle
from google.appengine.api import memcache
from feathers import webapp

"""
Usage:
	@memoize('results:value=%s')
	def get_some_results(value):
		return some_operation_on_value(value)
"""

def memoize(keyformat, time=60):
    """Decorator to memoize functions using memcache."""
    def decorator(fxn):
        def wrapper(*args, **kwargs):
            key = keyformat % args[0:keyformat.count('%')]
            data = memcache.get(key)
            if data is not None:
                return data
            data = fxn(*args, **kwargs)
            memcache.set(key, data, time)
            return data
        return wrapper
    return decorator

def simple_memoize(key, time=60):
    """Decorator to memoize functions using memcache."""
    def decorator(fxn):
        def wrapper(*args, **kwargs):
            data = memcache.get(key)
            if data is not None:
                return data
            data = fxn(*args, **kwargs)
            memcache.set(key, data, time)
            return data
        return wrapper
    return decorator




"""
a decorator to use memcache on google appengine.
optional arguments:
  `key`: the key to use for the memcache store
  `time`: the time to expiry sent to memcache

if no key is given, the function name, args, and kwargs are
used to create a unique key so that the same function can return
different results when called with different arguments (as
expected).

usage:
NOTE: actual usage is simpler as:
@gaecache()
def some_function():
...

but doctest doesnt seem to like that.

    >>> import time

    >>> def slow_fn():
    ...    time.sleep(1.1)
    ...    return 2 * 2
    >>> slow_fn = gaecache()(slow_fn)

this run take over a second.
    >>> t = time.time()
    >>> slow_fn(), time.time() - t > 1
    (4, True)

this grab from cache in under .01 seconds
    >>> t = time.time()
    >>> slow_fn(), time.time() - t < .01
    (4, True)

modified from
http://code.activestate.com/recipes/466320/
and
http://code.activestate.com/recipes/325905/
"""


class gaecache(object):
    """
    memoize decorator to use memcache with a timeout and an optional key.
    if no key is given, the func_name, args, kwargs are used to create a key. 
    """
    def __init__(self, time=3600, key=None):
        self.time = time
        self.key  = key

    def __call__(self, f):
        def func(*args, **kwargs):
            if self.key is None:
                t = (f.func_name, args, kwargs.items())
                try:
                    hash(t)
                    key = t
                except TypeError:
                    try:
                        key = pickle.dumps(t)
                    except pickle.PicklingError:
                        logging.warn("cache FAIL:%s, %s", args, kwargs)
                        return f(*args, **kwargs)
            else:
                key = self.key

            data = memcache.get(key) 
            if data is not None: 
                logging.info("cache HIT: key:%s, args:%s, kwargs:%s", key, args, kwargs)
                return data

            logging.warn("cache MISS: key:%s, args:%s, kwargs:%s", key, args, kwargs)
            data = f(*args, **kwargs)
            memcache.set(key, data, self.time) 
            return data

        func.func_name = f.func_name
        return func