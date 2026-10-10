# -*- coding: utf-8 -*-
"""
编码检测与安全读取。

本模块的核心目标是：**尽可能准确地判断文件编码，并保证读取永不失败**。

检测策略（按可靠性递减）：
    1. BOM 头（最可靠，但仅覆盖 UTF 系列）
    2. chardet 检测（置信度需 > 阈值）
    3. UTF-8 严格解码试探（能过就是 UTF-8）
    4. GB18030 严格解码试探（中文环境覆盖最广）
    5. 兜底 latin-1（1 字节 1 字符，永不失败）

为什么不能仅看 BOM：
    绝大多数中文文本文件（尤其老项目、Windows 生成的）**没有 BOM**，
    只凭前几个字节会把 GBK 文件误判为 UTF-8，导致解码乱码或报错。
    因此必须结合 chardet 采样检测 + 严格解码试探。
"""

import os
from merge_tool.constants import (
    CHARDET_SAMPLE_BYTES,
    CHARDET_MIN_CONFIDENCE,
    STRICT_DECODE_SAMPLE_BYTES,
    FALLBACK_ENCODINGS,
)

# chardet 为可选依赖，缺失时自动降级
try:
    import chardet
    _CHARDET_AVAILABLE = True
except ImportError:
    _CHARDET_AVAILABLE = False


def chardet_available():
    """返回 chardet 是否可用。"""
    return _CHARDET_AVAILABLE


def _read_head(file_path, n_bytes):
    """
    读取文件头部 n_bytes 字节。

    任何 IO 错误都返回空 bytes，调用方据此做保守处理。
    """
    try:
        with open(file_path, "rb") as f:
            return f.read(n_bytes)
    except OSError:
        return b""


def _detect_bom(head):
    """
    根据 BOM 判断编码。

    返回：
        编码名（如 'utf-8-sig'）或 None（无 BOM）
    """
    if head.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if head.startswith(b"\xff\xfe\x00\x00"):
        return "utf-32"
    if head.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32-be"
    if head.startswith(b"\xff\xfe"):
        return "utf-16"
    if head.startswith(b"\xfe\xff"):
        return "utf-16-be"
    return None


def _try_strict_decode(data, encoding):
    """
    尝试用指定编码严格解码。

    返回 True/False。
    对空数据返回 True（空文件任意编码都成立）。
    """
    if not data:
        return True
    try:
        data.decode(encoding, errors="strict")
        return True
    except (UnicodeDecodeError, LookupError):
        return False


def _chardet_detect(data):
    """
    使用 chardet 检测编码。

    返回：
        编码名或 None
    仅当置信度 > 阈值时返回结果。
    """
    if not _CHARDET_AVAILABLE or not data:
        return None
    try:
        result = chardet.detect(data)
    except Exception:
        return None
    enc = result.get("encoding")
    conf = result.get("confidence", 0) or 0
    if not enc or conf < CHARDET_MIN_CONFIDENCE:
        return None
    # chardet 对纯 ASCII 会返回 ascii，统一按 utf-8 处理更安全
    if enc.lower() in ("ascii",):
        return "utf-8"
    # chardet 有时返回 'GB2312'，但它实际是 GBK 子集，用 GB18030 更保险
    if enc.lower() in ("gb2312", "gbk"):
        return "gb18030"
    return enc


def detect_encoding(file_path, force_encoding=None):
    """
    严谨地检测文件编码。

    参数：
        file_path:       文件绝对路径
        force_encoding:  若指定，直接返回该编码（不做任何检测）

    返回：
        Python 编码名（如 'utf-8' / 'gb18030' / 'utf-16'）

    检测顺序：
        1. 强制编码优先
        2. 空文件 -> utf-8
        3. BOM 头
        4. chardet（高置信度）
        5. UTF-8 严格解码试探
        6. GB18030 严格解码试探
        7. 兜底 gbk
    """
    # 1. 强制编码
    if force_encoding:
        return force_encoding

    # 2. 空文件
    try:
        if os.path.getsize(file_path) == 0:
            return "utf-8"
    except OSError:
        return "utf-8"

    # 3. BOM
    head = _read_head(file_path, 4)
    bom_enc = _detect_bom(head)
    if bom_enc:
        return bom_enc

    # 4. chardet 采样检测
    sample = _read_head(file_path, CHARDET_SAMPLE_BYTES)
    chardet_enc = _chardet_detect(sample)
    if chardet_enc:
        # 用更长的样本再次严格验证，避免 chardet 误判
        verify_sample = _read_head(file_path, STRICT_DECODE_SAMPLE_BYTES * 4)
        if _try_strict_decode(verify_sample, chardet_enc):
            return chardet_enc

    # 5. UTF-8 严格解码试探（能过基本就是 UTF-8）
    strict_sample = _read_head(file_path, STRICT_DECODE_SAMPLE_BYTES)
    if _try_strict_decode(strict_sample, "utf-8"):
        return "utf-8"

    # 6. GB18030 严格解码试探
    #    GB18030 是 GBK/GB2312 的超集，对中文文本覆盖最广
    if _try_strict_decode(strict_sample, "gb18030"):
        return "gb18030"

    # 7. 兜底
    return "gbk"


def read_file_safely(file_path, force_encoding=None):
    """
    安全读取文件内容，多编码级联兜底。

    参数：
        file_path:       文件绝对路径
        force_encoding:  强制编码；None 表示自动检测

    返回：
        (内容字符串, 实际使用的编码名)

    异常：
        仅当文件本身不可读（权限/占用/不存在）时抛 OSError。
        编码相关的失败永远会被兜底 latin-1 消化。
    """
    enc = detect_encoding(file_path, force_encoding)

    # 构造候选编码列表
    candidates = [enc]
    if force_encoding is None:
        for fb in FALLBACK_ENCODINGS:
            if fb not in candidates:
                candidates.append(fb)
    else:
        # 强制模式下也提供 latin-1 兜底，防止完全读不出来
        if "latin-1" not in candidates:
            candidates.append("latin-1")

    last_err = None
    for c in candidates:
        try:
            with open(file_path, "r", encoding=c, errors="strict", newline="") as f:
                content = f.read()
            return content, c
        except (UnicodeDecodeError, LookupError) as e:
            last_err = e
            continue
        except OSError:
            # 文件系统错误（权限、被占用等）直接上抛
            raise

    # 理论上不会走到这里（latin-1 兜底永不失败），保险起见
    raise last_err if last_err else RuntimeError(f"无法读取文件: {file_path}")