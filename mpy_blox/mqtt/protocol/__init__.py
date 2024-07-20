import micropython

# MQTT Variable Byte Integer data type
@micropython.viper
def calc_VBI_size(value: int) -> int:
    """Calculate how large a Variable Byte Integer (VBI) would be in bytes
    using Viper optimizations.

    :param value: The integer that would be represented in the VBI.
    :return: The number of bytes that would be needed for the VBI buffer.
    """

    size: int = 0
    while True:
        size += 1
        value >>= 7
        if value == 0:
            break
    return size


@micropython.viper
def decode_VBI(input_bytes: ptr8) -> int:
    """Decode a Variable Byte Integer (VBI) from the given buffer.

    :param input_bytes: Pointer to the buffer containing the VBI.
    :return: The decoded integer value.
    """
    result: int = 0
    multiplier: int = 1
    idx: int = 0
    max_bytes: int = 4  # MQTT limits to at most 4 bytes
    while idx < max_bytes:
        encoded_byte: int = input_bytes[idx]
        idx += 1
        result += (encoded_byte & 127) * multiplier
        if (encoded_byte & 128) == 0:
            break
        multiplier *= 128
        if multiplier > (128**3):
            raise OverflowError("Malformed Variable Byte Integer")

    return result


@micropython.viper
def encode_VBI(value: int, output_buf: ptr8) -> int:
    """Encode a Variable Byte Integer (VBI) using Viper optimizations.

    :param value: The integer value to be encoded.
    :param output_buf: Pointer to a buffer to store the encoded bytes.
    :return: The number of bytes written to the output buffer.
    """
    idx = 0
    while True:
        encoded_byte = value & 127
        value >>= 7
        if value:
            encoded_byte |= 128  # Set the continuation bit
        output_buf[idx] = encoded_byte
        idx += 1
        if not value:
            break

    return idx

# MQTT String data type
def encode_string(str_to_encode):
    string_bytes = str_to_encode.encode()
    return len(string_bytes).to_bytes(2, 'big') + string_bytes


def decode_string(mv_to_decode) -> tuple[int, str]:
    str_len = int.from_bytes(mv_to_decode[:2], 'big')
    return (str_len, str(mv_to_decode[2:2+str_len], 'utf8'))


# MQTT Control packet fixed header
@micropython.viper
def encode_control_packet_type(control_packet_type: int) -> int:
    return control_packet_type << 4


def encode_control_packet_fixed_header(type_id, remaining_length):
    # Translate remaining length
    remaining_length_buf = bytearray(4)  # MQTT limits VBI to at most 4 bytes
    max_idx = encode_VBI(remaining_length, remaining_length_buf)

    # Return fixed header = encoded packet type + remaining length VBI
    return (bytes((encode_control_packet_type(type_id),))
            + remaining_length_buf[:max_idx])


#@micropython.viper
#def decode_control_packet_type(encoded_control_packet_type: ptr8) -> int:
#    return encoded_control_packet_type[0] >> 4
@micropython.viper
def decode_control_packet_type(encoded_control_packet_type: int) -> int:
    return encoded_control_packet_type >> 4
