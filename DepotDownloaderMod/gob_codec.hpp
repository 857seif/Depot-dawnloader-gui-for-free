#include <vector>
#include <string>
#include <cstdint>
#include <stdexcept>
#include <algorithm>
#include <complex>
#include <cstring>
#include <map>

// Constants for Predefined Gob Types
const int BOOL = 1;
const int INT = 2;
const int UINT = 3;
const int FLOAT = 4;
const int BYTE_SLICE = 5;
const int STRING = 6;
const int COMPLEX = 7;
const int INTERFACE = 8;
const int WIRE_TYPE = 16;
const int ARRAY_TYPE = 17;
const int COMMON_TYPE = 18;
const int SLICE_TYPE = 19;
const int STRUCT_TYPE = 20;
const int FIELD_TYPE = 21;
const int FIELD_TYPE_SLICE = 22;
const int MAP_TYPE = 23;
const int GOB_ENCODER_TYPE = -1;
const int BINARY_MARSHALER_TYPE = -2;
const int TEXT_MARSHALER_TYPE = -3;

class GoUint {
public:
    static std::pair<uint64_t, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        if (buf.empty()) throw std::runtime_error("Buffer empty");
        if (buf[0] < 128) {
            uint64_t val = buf[0];
            return {val, std::vector<uint8_t>(buf.begin() + 1, buf.end())};
        }
        int length = 256 - buf[0];
        uint64_t n = 0;
        for (int i = 1; i < length; ++i) {
            n = (n + buf[i]) << 8;
        }
        n += buf[length];
        return {n, std::vector<uint8_t>(buf.begin() + length + 1, buf.end())};
    }

    static std::vector<uint8_t> encode(uint64_t n) {
        if (n < 128) return {(uint8_t)n};
        std::vector<uint8_t> encoded;
        uint64_t temp = n;
        while (temp > 0) {
            encoded.push_back(temp & 0xFF);
            temp >>= 8;
        }
        uint8_t len_byte = (uint8_t)(256 - encoded.size());
        std::reverse(encoded.begin(), encoded.end());
        encoded.insert(encoded.begin(), len_byte);
        return encoded;
    }
};

class GoInt {
public:
    static std::pair<int64_t, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        auto res = GoUint::decode(buf);
        uint64_t u = res.first;
        int64_t i;
        if (u & 1) i = ~(u >> 1);
        else i = u >> 1;
        return {i, res.second};
    }

    static std::vector<uint8_t> encode(int64_t n) {
        uint64_t u;
        if (n < 0) u = (~(uint64_t)n << 1) | 1;
        else u = (uint64_t)n << 1;
        return GoUint::encode(u);
    }
};

class GoBool {
public:
    static std::pair<bool, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        auto res = GoUint::decode(buf);
        return {res.first == 1, res.second};
    }

    static std::vector<uint8_t> encode(bool b) {
        return GoUint::encode(b ? 1 : 0);
    }
};

class GoFloat {
public:
    static std::pair<double, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        auto res = GoUint::decode(buf);
        uint64_t u = res.first;
        uint64_t rev = 0;
        for(int i=0; i<8; ++i) rev = (rev << 8) | ((u >> (i*8)) & 0xFF);
        double f;
        std::memcpy(&f, &rev, 8);
        return {f, res.second};
    }

    static std::vector<uint8_t> encode(double f) {
        uint64_t u;
        std::memcpy(&u, &f, 8);
        uint64_t rev = 0;
        for(int i=0; i<8; ++i) rev = (rev << 8) | ((u >> (i*8)) & 0xFF);
        return GoUint::encode(rev);
    }
};

class GoByteSlice {
public:
    static std::pair<std::vector<uint8_t>, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        auto res = GoUint::decode(buf);
        uint64_t count = res.first;
        std::vector<uint8_t> data(res.second.begin(), res.second.begin() + count);
        return {data, std::vector<uint8_t>(res.second.begin() + count, res.second.end())};
    }

    static std::vector<uint8_t> encode(std::vector<uint8_t> data) {
        std::vector<uint8_t> res = GoUint::encode(data.size());
        res.insert(res.end(), data.begin(), data.end());
        return res;
    }
};

class GoString {
public:
    static std::pair<std::string, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        auto res = GoUint::decode(buf);
        uint64_t count = res.first;
        std::string s(res.second.begin(), res.second.begin() + count);
        return {s, std::vector<uint8_t>(res.second.begin() + count, res.second.end())};
    }

    static std::vector<uint8_t> encode(std::string s) {
        std::vector<uint8_t> res = GoUint::encode(s.length());
        res.insert(res.end(), s.begin(), s.end());
        return res;
    }
};

class GoComplex {
public:
    static std::pair<std::complex<double>, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        auto re_res = GoFloat::decode(buf);
        auto im_res = GoFloat::decode(re_res.second);
        return {{re_res.first, im_res.first}, im_res.second};
    }

    static std::vector<uint8_t> encode(std::complex<double> z) {
        auto re_enc = GoFloat::encode(z.real());
        auto im_enc = GoFloat::encode(z.imag());
        re_enc.insert(re_enc.end(), im_enc.begin(), im_enc.end());
        return re_enc;
    }
};

class GoMarshalerBase {
public:
    static std::pair<std::vector<uint8_t>, std::vector<uint8_t>> decode(std::vector<uint8_t> buf) {
        return GoByteSlice::decode(buf);
    }

    static std::vector<uint8_t> encode(std::vector<uint8_t> data) {
        return GoByteSlice::encode(data);
    }
};
