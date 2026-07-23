from __future__ import annotations

from typing import Any

import requests


class HuggingFaceClient:
    # BASE_URL = "https://huggingface.co"
    BASE_URL = "https://hf-mirror.com" 

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def get_model(self, model_id: str) -> dict[str, Any]:
        url = f"{self.BASE_URL}/api/models/{model_id}"
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return {
            "downloads": int(payload.get("downloads", 0) or 0),
            "likes": int(payload.get("likes", 0) or 0),
            "pipeline_tag": payload.get("pipeline_tag"),
            "tags": list(payload.get("tags", []) or []),
            "lastModified": payload.get("lastModified"),
        }
# from __future__ import annotations

# import os
# from typing import Any

# import requests
# from dotenv import load_dotenv
# load_dotenv()  # 自动读取 .env 并设置环境变量

# class HuggingFaceClient:
#     BASE_URL = "https://hf-mirror.com"

#     def __init__(self, session: requests.Session | None = None):
#         self.session = session or requests.Session()
        
#         # 从环境变量读取代理并设置到 session
#         proxy_map = {}
#         for key in ["HTTP_PROXY", "HTTPS_PROXY"]:
#             env_val = os.environ.get(key)
#             if env_val:
#                 # requests 使用小写键 'http' 和 'https'
#                 proxy_map[key.lower()] = env_val
        
#         if proxy_map:
#             self.session.proxies.update(proxy_map)
        
#         # 可选：显式启用从环境变量读取（默认就是 True，但写出来更明确）
#         self.session.trust_env = True

#     def get_model(self, model_id: str) -> dict[str, Any]:
#         url = f"{self.BASE_URL}/api/models/{model_id}"
#         response = self.session.get(url, timeout=30)
#         response.raise_for_status()
#         payload: dict[str, Any] = response.json()
#         return {
#             "downloads": int(payload.get("downloads", 0) or 0),
#             "likes": int(payload.get("likes", 0) or 0),
#             "pipeline_tag": payload.get("pipeline_tag"),
#             "tags": list(payload.get("tags", []) or []),
#             "lastModified": payload.get("lastModified"),
#         }