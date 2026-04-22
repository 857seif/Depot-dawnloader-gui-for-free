from .types import (BOOL, INT, UINT, FLOAT, BYTE_SLICE, STRING, COMPLEX,
                    WIRE_TYPE, ARRAY_TYPE, COMMON_TYPE, SLICE_TYPE,
                    STRUCT_TYPE, FIELD_TYPE, FIELD_TYPE_SLICE, MAP_TYPE,
                    GOB_ENCODER_TYPE, BINARY_MARSHALER_TYPE, TEXT_MARSHALER_TYPE)
from .types import (GoBool, GoUint, GoInt, GoFloat, GoByteSlice, GoString,
                    GoComplex, GoStruct, GoWireType, GoSlice)

class Encoder:
    def __init__(self, types):
        self.types = types

    def encode(self, typeid):
        return self._encode(typeid)

    def _encode(self, typeid):
        go_type = self.types.get(typeid)
        assert go_type != None, 'Invalid typeid %s' % typeid
        go_type.encode()
