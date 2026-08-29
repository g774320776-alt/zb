# -*- coding: utf-8 -*-
"""
auto_load.py 自动加载本仓库 py 和 js 文件夹全部爬虫
仓库: g774320776-alt / zb
存放位置：仓库【根目录】，禁止放到 py/js 子文件夹
"""
import json
import base64
import os
import time
from base.spider import Spider


class AutoSpider(Spider):
    GH_USER = "g774320776-alt"
    GH_REPO = "zb"
    GH_BRANCH = "main"
    GH_FAST = "https://ghfast.top/https://raw.githubusercontent.com"

    # 手机本地缓存文件，规避github api限流，缓存有效期3600秒=1小时
    CACHE_PATH = "/storage/emulated/0/海豚影视/海豚/gh_auto_cache.json"
    CACHE_EXPIRE = 3600

    # 需要扫描的子目录及对应爬虫类型
    # js 爬虫 type=2，py/csp 爬虫 type=3
    SCAN_DIRS = [
        {"path": "py", "ext": ".py", "type": 3, "prefix": "【PY】"},
        {"path": "js", "ext": ".js", "type": 2, "prefix": "【JS】"},
    ]

    # 固定前置锁定源（已删除第三方自动加载678.py，只保留弹幕）
    _LOCKED_SITES = [
        {
            "name": "🐬弹幕",
            "key": "弹幕豆瓣",
            "type": 3,
            "api": "csp_SecureDanmu",
            "searchable": 1,
            "jar": "https://ghfast.top/https://raw.githubusercontent.com/goodcommunication/mydm/main/danmu-spider-native.jar",
            "ext": {
                "apiUrls": [
                    "https://danmu.iyo.us.ci/theft-dastardly-prognosis-hula-agenda2-dropkick|公益源",
                    "https://logo.saodu.work:8888/87654321|公益源1",
                    "https://dm.ljiaovm.com/luosen|公益源2"
                ],
                "titleMappingsUrl": "https://ghfast.top/https://raw.githubusercontent.com/goodcommunication/mydm/main/yins.json",
                "filter": "./lib/douban.json"
            }
        }
    ]

    def __init__(self):
        super().__init__()
        self.inited = False
        self.file_map = {}
        self.class_list = []

    def getName(self):
        return "仓库Py/Js自动加载"

    def init(self, extend=None):
        if self.inited:
            return
        try:
            use_ok = self.load_cache()
            if not use_ok:
                for cfg in self.SCAN_DIRS:
                    self.scan_github_dir(cfg["path"], cfg)
                self.save_cache()
        except Exception:
            pass
        self.inited = True

    def load_cache(self):
        if not os.path.exists(self.CACHE_PATH):
            return False
        try:
            with open(self.CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            now = int(time.time())
            if now < data.get("expire", 0):
                self.file_map = data.get("file_map", {})
                self.class_list = data.get("class_list", [])
                return True
        except Exception:
            pass
        return False

    def save_cache(self):
        out = {
            "expire": int(time.time()) + self.CACHE_EXPIRE,
            "file_map": self.file_map,
            "class_list": self.class_list
        }
        try:
            folder = os.path.dirname(self.CACHE_PATH)
            if not os.path.exists(folder):
                os.makedirs(folder)
            with open(self.CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False)
        except Exception:
            pass

    def gh_api(self, path):
        url = f"https://api.github.com/repos/{self.GH_USER}/{self.GH_REPO}/contents/{path}?ref={self.GH_BRANCH}"
        try:
            resp = self.fetch(url)
            if not resp or resp.code != 200:
                return None
            return json.loads(resp.text)
        except Exception:
            return None

    def scan_github_dir(self, repo_path, cfg):
        items = self.gh_api(repo_path)
        if not isinstance(items, list):
            return
        target_ext = cfg["ext"].lower()
        for it in items:
            if it["type"] == "dir":
                self.scan_github_dir(it["path"], cfg)
            elif it["type"] == "file":
                fname = it["name"]
                full_path = it["path"]
                if not fname.lower().endswith(target_ext):
                    continue
                name_no_ext = os.path.splitext(fname)[0]
                raw_url = f"{self.GH_FAST}/{self.GH_USER}/{self.GH_REPO}/{self.GH_BRANCH}/{full_path}"
                tid = base64.b64encode(full_path.encode("utf-8")).decode("utf-8")
                self.file_map[tid] = {
                    "name": name_no_ext,
                    "api": raw_url,
                    "type": cfg["type"]
                }
                self.class_list.append({
                    "type_id": tid,
                    "type_name": f"{cfg['prefix']}{name_no_ext}"
                })

    def getConfigJson(self):
        sites = list(self._LOCKED_SITES)
        for tid, info in self.file_map.items():
            sites.append({
                "name": info["name"],
                "key": info["name"],
                "type": info["type"],
                "api": info["api"],
                "searchable": 1,
                "filterable": 1
            })
        return {"sites": sites}

    def homeContent(self, filter):
        return {"class": self.class_list, "list": []}
    def homeVideoContent(self): return {"list": []}
    def categoryContent(self, tid, pg, filter, extend): return {"list": []}
    def detailContent(self, ids): return {}
    def searchContent(self, key, quick): return {"list": []}
    def playerContent(self, flag, id, vipFlags): return {}
    def localProxy(self, param): return None
    def setMode(self, mode): pass
