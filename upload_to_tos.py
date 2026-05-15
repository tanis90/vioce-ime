"""
火山引擎 TOS 文件上传助手（官方 SDK 版）
==========================================
将本地音频文件上传到 TOS，获取公网 URL 供 Seed-ASR 调用。

依赖:
    pip install tos

环境变量 (写入 voice-ime/.env):
    TOS_ACCESS_KEY=你的AK
    TOS_SECRET_KEY=你的SK
    TOS_ENDPOINT=tos-cn-shanghai.volces.com
    TOS_BUCKET=dm-agent-voice
"""

import os

import tos
from dotenv import load_dotenv

load_dotenv()


def get_tos_client():
    """初始化 TOS 官方客户端。"""
    ak = os.environ.get("TOS_ACCESS_KEY")
    sk = os.environ.get("TOS_SECRET_KEY")
    endpoint = os.environ.get("TOS_ENDPOINT", "tos-cn-shanghai.volces.com")
    region = endpoint.split(".")[0].replace("tos-", "")  # e.g. tos-cn-shanghai -> cn-shanghai

    if not ak or not sk:
        raise RuntimeError(
            "TOS AK/SK 未配置。请在 .env 中设置:\n"
            "  TOS_ACCESS_KEY=你的AK\n"
            "  TOS_SECRET_KEY=你的SK"
        )

    return tos.TosClientV2(ak, sk, endpoint, region)


def upload_file(local_path: str, object_key: str | None = None) -> str:
    """
    上传本地文件到 TOS。

    Args:
        local_path: 本地文件路径
        object_key: TOS 上的对象名（默认使用本地文件名）

    Returns:
        公网可访问的 URL
    """
    bucket = os.environ.get("TOS_BUCKET", "dm-agent-voice")
    if not bucket:
        raise RuntimeError("TOS_BUCKET 未配置")

    if not os.path.exists(local_path):
        raise FileNotFoundError(f"文件不存在: {local_path}")

    key = object_key or os.path.basename(local_path)
    client = get_tos_client()

    print(f"[TOS] 上传 {local_path} → {bucket}/{key} ...")
    try:
        resp = client.put_object_from_file(bucket, key, local_path)
        print(f"[TOS] 上传成功, ETag={resp.etag}")
    except tos.exceptions.TosServerError as e:
        print(f"[TOS] 服务端错误: {e.code} - {e.message}")
        print(f"      RequestID: {e.request_id}")
        raise
    except Exception as e:
        print(f"[TOS] 上传异常: {e}")
        raise

    endpoint = os.environ.get("TOS_ENDPOINT", "tos-cn-shanghai.volces.com")
    url = f"https://{bucket}.{endpoint}/{key}"
    print(f"[TOS] 访问 URL: {url}")
    return url


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python upload_to_tos.py <文件路径>")
        sys.exit(1)

    url = upload_file(sys.argv[1])
    print(f"\nURL: {url}")
