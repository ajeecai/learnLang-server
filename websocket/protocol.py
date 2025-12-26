import struct
import json
import io
import logging
from typing import Dict, Union, Optional

logger = logging.getLogger(__name__)


class WebSocketProtocol:
    # 消息类型
    TYPE_PING = 0x01
    TYPE_PONG = 0x02
    TYPE_DATA = 0x03
    TYPE_PUSH = 0x04
    TYPE_TIMEOUT = 0x05
    TYPE_TOKEN_EXPIRED = 0x06
    TYPE_ERROR = 0xFF

    @staticmethod
    def parse_message(data: bytes) -> Optional[Dict[str, Union[int, bytes, Dict]]]:
        """解析二进制消息 [direction: 1 byte][type: 1 byte][length: 4 bytes][data]"""
        if len(data) < 6:
            logger.warning("消息长度不足6字节")
            return None

        direction = data[0]
        type_ = data[1]
        length = struct.unpack("!I", data[2:6])[0]
        payload = data[6 : 6 + length]

        if len(payload) != length:
            logger.error(
                f"Payload length mismatch: expected {length}, got {len(payload)}"
            )
            return None

        return {
            "direction": direction,
            "type": type_,
            "length": length,
            "payload": payload,
        }

    @staticmethod
    def parse_data_payload(payload: bytes) -> Dict[str, Union[Dict, bytes]]:
        """解析 payload [length_json: 4 bytes][json][length_binary: 4 bytes][binary]"""
        if len(payload) < 8:
            return {"json_data": {}, "binary_data": b""}

        offset = 0
        json_length = struct.unpack("!I", payload[offset : offset + 4])[0]
        offset += 4

        json_str = payload[offset : offset + json_length].decode("utf-8")
        offset += json_length

        binary_length = struct.unpack("!I", payload[offset : offset + 4])[0]
        offset += 4

        binary_data = (
            payload[offset : offset + binary_length] if binary_length > 0 else b""
        )

        try:
            json_obj = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}, original string: {json_str}")
            json_obj = {}

        return {"json_data": json_obj, "binary_data": binary_data}

    @staticmethod
    def build_message(
        direction: int,
        type_: int,
        json_data: Optional[Dict] = None,
        binary_data: Optional[Union[bytes, io.BytesIO]] = None,
    ) -> bytes:
        """构造二进制消息"""
        json_bytes = json.dumps(json_data if json_data is not None else {}).encode(
            "utf-8"
        )
        binary_bytes = (
            binary_data.getvalue()
            if isinstance(binary_data, io.BytesIO)
            else binary_data if binary_data else b""
        )

        payload = (
            struct.pack("!I", len(json_bytes))
            + json_bytes
            + struct.pack("!I", len(binary_bytes))
            + binary_bytes
        )

        return struct.pack("!BBI", direction, type_, len(payload)) + payload
