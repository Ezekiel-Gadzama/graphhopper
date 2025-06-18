from typing import List, Tuple

class Polyline:
    @staticmethod
    def decode(polyline: str, format: str = 'ffii', precision: int = 6) -> List[Tuple]:
        """Decode polyline string into coordinates"""
        if not polyline:
            return []
            
        # Check if it's old-style encoding
        if polyline[0].isdigit() or polyline[0] == '-':
            return Polyline._decode_old_format(polyline, format)
        else:
            return Polyline._decode_google_format(polyline, format, precision)

    @staticmethod
    def _decode_old_format(polyline: str, format: str) -> List[Tuple]:
        """Decode old-style polyline format (colon/semicolon separated)"""
        format_len = len(format)
        values = [float(x) if '.' in x else int(x) 
                 for x in polyline.replace(';', ':').split(':') 
                 if x]
        return [tuple(values[i:i+format_len]) 
                for i in range(0, len(values), format_len)]

    @staticmethod
    def _decode_google_format(polyline: str, format: str, precision: int) -> List[Tuple]:
        """Decode Google Maps polyline format"""
        format_len = len(format)
        index = i = 0
        previous = [0] * format_len
        points = []
        current_point = []
        
        while i < len(polyline):
            for f in range(format_len):
                shift = result = 0x00
                while True:
                    bit = ord(polyline[i]) - 63
                    i += 1
                    result |= (bit & 0x1f) << shift
                    shift += 5
                    if bit < 0x20:
                        break
                
                diff = ~(result >> 1) if (result & 1) else (result >> 1)
                number = previous[f] + diff
                previous[f] = number
                
                if format[f] == 'f':
                    current_point.append(number * (10 ** -precision))
                else:
                    current_point.append(number)
                
                if len(current_point) == format_len:
                    points.append(tuple(current_point))
                    current_point = []
        
        return points