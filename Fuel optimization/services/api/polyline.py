from typing import List


class Polyline:

    @staticmethod
    def decode(encoded: str, format: str = 'ffii', precision: int = 6) -> List[List[float]]:
        """Decode a polyline encoded with multiple types (e.g., ffii)"""
        result = []
        index = 0
        shift = 0
        result_item = []
        last_values = [0] * len(format)
        factor = 10 ** precision
        values = []

        while index < len(encoded):
            for i, fmt in enumerate(format):
                shift = 0
                result_item = 0
                byte = None
                while True:
                    byte = ord(encoded[index]) - 63
                    index += 1
                    result_item |= (byte & 0x1f) << shift
                    shift += 5
                    if byte < 0x20:
                        break
                delta = ~(result_item >> 1) if (result_item & 1) else (result_item >> 1)
                last_values[i] += delta
                if fmt == 'f':
                    values.append(last_values[i] / factor)
                elif fmt == 'i':
                    values.append(last_values[i])
            result.append(values)
            values = []

        return result
