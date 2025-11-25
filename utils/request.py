# Some utils for processing request

import os
import struct


def generate_radom_nonce_str(length: int) -> str:

    """
    Generate a random nonce string
    """
    random_bytes = os.urandom(length)
    return ''.join(f"{struct.unpack('>I', random_bytes[i:i+4])[0]:08X}" for i in range(0, length, 4))

