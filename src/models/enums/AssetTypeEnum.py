from enum import Enum

class AssetTypeEnum(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    FILE = "file"