"""
This Module defines json method used to dump and load object types of the qao repository

    @author: tlausch
    created: 2014-06-23

"""
import base64
import json
import numpy as np

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        if input object is a ndarray it will be converted into a dict holding dtype, shape and the data base64 encoded
        """
        if isinstance(obj, np.ndarray):
            data_b64 = base64.b64encode(np.ascontiguousarray(obj).data)
            return dict(__ndarray__=data_b64,
                        dtype=str(obj.dtype),
                        shape=obj.shape)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder(self, obj)


def json_numpy_obj_hook(dct):
    """
    Decodes a previously encoded numpy ndarray
    with proper shape and dtype
    :param dct: (dict) json encoded ndarray
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(dct, dict) and '__ndarray__' in dct:
        data = base64.b64decode(dct['__ndarray__'])
        return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
    return dct

def loads(s):
    return json.loads(s, object_hook=json_numpy_obj_hook)

def dumps(obj, separators=(',', ':'), sort_keys=True):
    return json.dumps(obj, cls=NumpyEncoder, separators=separators, sort_keys=sort_keys)
