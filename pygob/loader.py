from .types import (BOOL, INT, UINT, FLOAT, BYTE_SLICE, STRING, COMPLEX,
                    WIRE_TYPE, ARRAY_TYPE, COMMON_TYPE, SLICE_TYPE,
                    STRUCT_TYPE, FIELD_TYPE, FIELD_TYPE_SLICE, MAP_TYPE,
                    GOB_ENCODER_TYPE, BINARY_MARSHALER_TYPE, TEXT_MARSHALER_TYPE)
from .types import (GoBool, GoUint, GoInt, GoFloat, GoByteSlice, GoString,
                    GoComplex, GoStruct, GoWireType, GoSlice)
from .encoder import Encoder


class Loader:
    def __init__(self):
        # Compound types that depend on the basic types above.
        common_type = GoStruct(COMMON_TYPE, 'CommonType', self, [
            ('Name', STRING),
            ('Id', INT),
        ])
        array_type = GoStruct(ARRAY_TYPE, 'ArrayType', self, [
            ('CommonType', COMMON_TYPE),
            ('Elem', INT),
            ('Len', INT),
        ])
        slice_type = GoStruct(SLICE_TYPE, 'SliceType', self, [
            ('CommonType', COMMON_TYPE),
            ('Elem', INT),
        ])
        struct_type = GoStruct(STRUCT_TYPE, 'StructType', self, [
            ('CommonType', COMMON_TYPE),
            ('Field', FIELD_TYPE_SLICE),
        ])
        field_type = GoStruct(FIELD_TYPE, 'FieldType', self, [
            ('Name', STRING),
            ('Id', INT),
        ])
        field_type_slice = GoSlice(FIELD_TYPE_SLICE, self, FIELD_TYPE)
        map_type = GoStruct(MAP_TYPE, 'MapType', self, [
            ('CommonType', COMMON_TYPE),
            ('Key', INT),
            ('Elem', INT),
        ])
        wire_type = GoWireType(WIRE_TYPE, 'WireType', self, [
            ('ArrayT', ARRAY_TYPE),
            ('SliceT', SLICE_TYPE),
            ('StructT', STRUCT_TYPE),
            ('MapT', MAP_TYPE),
            ('GobEncoderT', GOB_ENCODER_TYPE),
            ('BinaryMarshalerT', BINARY_MARSHALER_TYPE),
            ('TextMarshalerT', TEXT_MARSHALER_TYPE),
        ])
        gob_encoder_type = GoStruct(GOB_ENCODER_TYPE, 'GobEncoderType', self, [
            ('CommonType', COMMON_TYPE),
        ])
        binary_marshaler_type = GoStruct(BINARY_MARSHALER_TYPE, 'BinaryMarshalerType', self, [
            ('CommonType', COMMON_TYPE),
        ])
        text_marshaler_type = GoStruct(TEXT_MARSHALER_TYPE, 'TextMarshalerType', self, [
            ('CommonType', COMMON_TYPE),
        ])

        # We can now register basic and compound types.
        self.types = {
            INT: GoInt,
            UINT: GoUint,
            BOOL: GoBool,
            FLOAT: GoFloat,
            BYTE_SLICE: GoByteSlice,
            STRING: GoString,
            COMPLEX: GoComplex,
            WIRE_TYPE: wire_type,
            ARRAY_TYPE: array_type,
            COMMON_TYPE: common_type,
            SLICE_TYPE: slice_type,
            STRUCT_TYPE: struct_type,
            FIELD_TYPE: field_type,
            FIELD_TYPE_SLICE: field_type_slice,
            MAP_TYPE: map_type,
            GOB_ENCODER_TYPE: gob_encoder_type,
            BINARY_MARSHALER_TYPE: binary_marshaler_type,
            TEXT_MARSHALER_TYPE: text_marshaler_type,
        }

        self.python_types = {
            bool: GoBool,
            int: GoInt,
            float: GoFloat,
            bytes: GoByteSlice,
            str: GoString,
            complex: GoComplex,
        }

        self.prelude = bytearray()

    def load(self, buf):
        value, buf = self._load(buf)
        return value

    def load_all(self, buf):
        while buf:
            value, buf = self._load(buf)
            yield value
        assert buf == b'', 'trailing data in buffer: %s' % list(buf)

    def _read_segment(self, buf):
        length, buf = GoUint.decode(buf)
        return buf[:length], buf[length:]

    def _load(self, buf):
        while True:
            segment, buf = self._read_segment(buf)
            typeid, segment = GoInt.decode(segment)
            if typeid > 0:
                break  # Found a value.

            # Decode wire type and register type for later.
            custom_type, segment = self.decode_value(WIRE_TYPE, segment)
            self.types[-typeid] = custom_type
            assert segment == b'', ('trailing data in segment: %s' %
                                    list(segment))

        # Top-level singletons are sent with an extra zero byte which
        # serves as a kind of field delta.
        go_type = self.types.get(typeid)
        if go_type is not None and not isinstance(go_type, GoStruct):
            assert segment[0] == 0, 'illegal delta for singleton: %s' % buf[0]
            segment = segment[1:]
        value, segment = self.decode_value(typeid, segment)
        assert segment == b'', 'trailing data in segment: %s' % list(segment)
        return value, buf

    def decode_value(self, typeid, buf):
        go_type = self.types.get(typeid)
        if go_type is None:
            raise NotImplementedError("cannot decode %s" % typeid)
        return go_type.decode(buf)

    def get_encoder(self, buf):
        while True:
            segment, buf = self._read_segment(buf)
            typeid, segment = GoInt.decode(segment)
            if typeid > 0:
                break  # Found a value.

            # Decode wire type and register type for later.
            custom_type, segment = self.decode_value(WIRE_TYPE, segment)
            self.types[-typeid] = custom_type
            assert segment == b'', ('trailing data in segment: %s' %
                                    list(segment))

        # Top-level singletons are sent with an extra zero byte which
        # serves as a kind of field delta.
        go_type = self.types.get(typeid)
        if go_type is not None and not isinstance(go_type, GoStruct):
            assert segment[0] == 0, 'illegal delta for singleton: %s' % buf[0]
            segment = segment[1:]
        value, segment = self.decode_value(typeid, segment)
        assert segment == b'', 'trailing data in segment: %s' % list(segment)
        return value, buf
        return Encoder(self.types)
