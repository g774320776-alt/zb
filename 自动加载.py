# -*- coding: utf-8 -*-

import os
import json
import base64
from base.spider import Spider


class Spider(Spider):

    # ============================================================
    # 配置
    # ============================================================

    PY_DIR = "/storage/emulated/0/TV/CustomCsp/py"
    SAVE_PATH = "/storage/emulated/0/TV/CustomCsp/zb.json"

    # ============================================================
    # 固定置顶：Nostr
    # ============================================================

    NOSTR = {
        "key": "Nostr",
        "name": "Nostr推荐 [影视]",
        "type": 3,
        "api": "csp_Nostr",
        "homePage": "https://www.252035.xyz/xs/tvbox/nostr.html"
    }

    # ===================== 额外全局配置 parses/doh/ads/lives/ijk =====================
    GLOBAL_EXTRA = {
  "lives": [
    {
      "name": "咪咕直播",
      "type": 0,
      "ua": "okhttp/5.3.2",
      "url": "http://www.52top.com.cn:678/downloads/migu.txt"
    }
  ],
  "parses": [
    {
      "name": "聚合",
      "type": 3,
      "url": "Web"
    },
    {
      "name": "盘古解析",
      "type": 0,
      "url": "shturl.cc/dMS3nvY3pDPlmR188WaoRDUYYBJY",
      "ext": {
        "header": {
          "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
        }
      }
    },
    {
      "name": "789解析1",
      "type": 0,
      "url": "shturl.cc/QIIsOIdELJ2a83ECKlTd2NJ5hNl"
    },
    {
      "name": "789解析2",
      "type": 0,
      "url": "shturl.cc/KV6itQnjRDZsink4c1g05I"
    },
    {
      "name": "虾米解析",
      "type": 0,
      "url": "shturl.cc/Q1gXkw4fywMlE1zV"
    },
    {
      "name": "淘片解析",
      "type": 0,
      "url": "shturl.cc/Py51otNiHUhmCSpmaecWLvRJQV"
    },
    {
      "name": "解析1",
      "type": 0,
      "url": "https://huayong.net/999/?v="
    },
    {
      "name": "解析2",
      "type": 0,
      "url": "shturl.cc/YxanJJasPZu6Ii1EPXaM"
    },
    {
      "name": "解析3",
      "type": 0,
      "url": "https://t2.qlplayer.cyou/player/analysis.php?v="
    },
    {
      "name": "解析4",
      "type": 0,
      "url": "shturl.cc/669b3z1qRQSBdTGW2W4WhlelTN"
    },
    {
      "name": "解析5",
      "type": 0,
      "url": "https://nm.xxxc137.top/static/player/artplayer.html?url="
    },
    {
      "name": "解析6",
      "type": 0,
      "url": "https://www.yemu.xyz/?url="
    },
    {
      "name": "解析7",
      "type": 0,
      "url": "http://rihou.cc:88/demo.php?url="
    },
    {
      "name": "冰豆",
      "type": 0,
      "url": "shturl.cc/CwKeK5WHV2ND",
      "ext": {
        "header": {
          "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
        }
      }
    },
    {
      "name": "七七",
      "type": 0,
      "url": "shturl.cc/3l2UGI0tsIVXO89",
      "ext": {
        "header": {
          "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
        }
      }
    },
    {
      "name": "夜幕",
      "type": 0,
      "url": "https://yemu.xyz/?url=",
      "ext": {
        "header": {
          "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
        }
      }
    }
  ]
}


    # ============================================================

    def __init__(self):
        super().__init__()
        self.inited = False
        self.file_index = {}
        self.categories = []

    # ============================================================
    # 名称
    # ============================================================

    def getName(self):
        return "本地PY聚合源"

    # ============================================================
    # 初始化
    # ============================================================

    def init(self, extend):
        if self.inited:
            return
        self.scan_all()
        self.save_config()
        self.inited = True

    # ============================================================
    # 递归扫描
    # ============================================================

    def scan_dir(self, directory, extension):
        result = []
        if not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception:
                return result
        if not os.path.isdir(directory):
            return result
        try:
            entries = sorted(
                os.listdir(directory),
                key=lambda x: x.lower()
            )
        except Exception:
            return result
        for name in entries:
            if name.startswith("."):
                continue
            path = os.path.join(directory, name)
            try:
                if os.path.isdir(path):
                    result.extend(
                        self.scan_dir(
                            path,
                            extension
                        )
                    )
                elif os.path.isfile(path):
                    if name.lower().endswith(extension):
                        filename = name[:-len(extension)]
                        result.append(
                            (
                                path,
                                filename,
                                extension[1:]
                            )
                        )
            except Exception:
                continue
        return result

    # ============================================================
    # 扫描 PY
    # ============================================================

    def scan_all(self):
        self.file_index = {}
        self.categories = []
        sites = []
        try:
            current_file = os.path.abspath(__file__)
        except Exception:
            current_file = ""
        # --------只扫描PY--------
        for path, name, ext in self.scan_dir(
            self.PY_DIR,
            ".py"
        ):
            try:
                if (
                    current_file
                    and os.path.abspath(path) == current_file
                ):
                    continue
            except Exception:
                pass
            tid = base64.b64encode(
                (
                    "PY|" + path
                ).encode("utf-8")
            ).decode("utf-8")
            self.file_index[tid] = {
                "path": path,
                "name": name,
                "ext": "py",
                "dir": self.PY_DIR
            }
            sites.append({
                "type_id": tid,
                "type_name": "【PY】" + name,
                "sort": (0, name.lower())
            })
        # --------排序--------
        sites.sort(
            key=lambda x: x["sort"]
        )
        self.categories = [
            {
                "type_id": x["type_id"],
                "type_name": x["type_name"]
            }
            for x in sites
        ]

    # ============================================================
    # API路径构建
    # ============================================================

    def build_api(self, info):
        try:
            relative = os.path.relpath(
                info["path"],
                info["dir"]
            )
        except Exception:
            relative = os.path.basename(
                info["path"]
            )
        relative = relative.replace(
            "\\",
            "/"
        )
        folder = os.path.basename(
            info["dir"]
        )
        return "./" + folder + "/" + relative

    # ============================================================
    # 生成站点
    # ============================================================

    def build_site(self, info):
        return {
            "key": info["name"] + "_" + info["ext"],
            "name": info["name"],
            "type": 3,
            "searchable": 1,
            "quickSearch": 1,
            "filterable": 1,
            "api": self.build_api(info)
        }

    # ============================================================
    # 保存 zb.json
    # ============================================================

    def save_config(self):
        config = {
            "sites": [
                self.NOSTR
            ]
        }
        config.update(self.GLOBAL_EXTRA)
        # 加入 PY
        for category in self.categories:
            info = self.file_index.get(
                category["type_id"]
            )
            if not info:
                continue
            if not os.path.isfile(
                info["path"]
            ):
                continue
            config["sites"].append(
                self.build_site(info)
            )
        # 创建目录
        save_dir = os.path.dirname(
            self.SAVE_PATH
        )
        if (
            save_dir
            and not os.path.exists(save_dir)
        ):
            try:
                os.makedirs(
                    save_dir,
                    exist_ok=True
                )
            except Exception:
                pass
        # 写入 JSON
        try:
            with open(
                self.SAVE_PATH,
                "w",
                encoding="utf-8"
            ) as f:
                json.dump(
                    config,
                    f,
                    ensure_ascii=False,
                    indent=2
                )
        except Exception:
            pass

    # ============================================================
    # 获取文件
    # ============================================================

    def get_file(self, tid):
        return self.file_index.get(tid)

    # ============================================================
    # 统计
    # ============================================================

    def count_files(self):
        py = 0
        for info in self.file_index.values():
            if info["ext"] == "py":
                py += 1
        return py, 0

    # ============================================================
    # 首页【每次进入首页自动扫描，增删py自动更新zb.json】
    # ============================================================

    def homeContent(self, filter):
        self.scan_all()
        self.save_config()
        return {
            "class": self.categories
        }

    # ============================================================
    # 首页
    # ============================================================

    def homeVod(self):
        py, js = self.count_files()
        return {
            "list": [{
                "vod_id": "__info__",
                "vod_name":
                    "PY: "
                    + str(py),
                "vod_pic": "",
                "vod_remarks": "扫描统计"
            }]
        }

    # ============================================================
    # 分类
    # ============================================================

    def categoryContent(
        self,
        tid,
        pg,
        filter,
        ext
    ):
        if str(pg) != "1":
            return {
                "list": []
            }
        info = self.get_file(tid)
        if not info:
            return {
                "list": []
            }
        if not os.path.isfile(
            info["path"]
        ):
            return {
                "list": []
            }
        vid = base64.b64encode(
            (
                info["ext"].upper()
                + "|"
                + info["path"]
            ).encode("utf-8")
        ).decode("utf-8")
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": info["name"],
                "vod_pic": "",
                "vod_remarks":
                    "["
                    + info["ext"].upper()
                    + "]"
            }]
        }

    # ============================================================
    # 详情
    # ============================================================

    def detailContent(self, array):
        try:
            vid = str(array[0])
            # ----------------------------------------------------
            # 扫描统计
            # ----------------------------------------------------
            if vid == "__info__":
                py, js = self.count_files()
                text = (
                    "PY目录:\n"
                    + self.PY_DIR
                    + "\n\n"
                    "配置文件:\n"
                    + self.SAVE_PATH
                    + "\n\n"
                    "PY数量: "
                    + str(py)
                )
                return {
                    "list": [{
                        "vod_name": "扫描统计",
                        "vod_pic": "",
                        "vod_content": text
                    }]
                }
            # ----------------------------------------------------
            # Base64
            # ----------------------------------------------------
            padded = (
                vid
                + "="
                * (
                    (4 - len(vid) % 4)
                    % 4
                )
            )
            raw = base64.b64decode(
                padded
            ).decode(
                "utf-8",
                errors="ignore"
            )
            if "|" in raw:
                ext, path = raw.split(
                    "|",
                    1
                )
            else:
                ext = "PY"
                path = raw
            # ----------------------------------------------------
            # 文件检查
            # ----------------------------------------------------
            if not os.path.isfile(path):
                return {
                    "list": [{
                        "vod_name": "文件不存在",
                        "vod_content": path
                    }]
                }
            filename = os.path.basename(path)
            if "." in filename:
                filename = filename.rsplit(
                    ".",
                    1
                )[0]
            # ----------------------------------------------------
            # API
            # ----------------------------------------------------
            api = path
            for info in self.file_index.values():
                if info["path"] == path:
                    api = self.build_api(info)
                    break
            # ----------------------------------------------------
            # 配置
            # ----------------------------------------------------
            site = {
                "key":
                    filename
                    + "_"
                    + ext.lower(),
                "name":
                    filename,
                "type": 3,
                "searchable": 1,
                "quickSearch": 1,
                "filterable": 1,
                "api":
                    api
            }
            self.save_config()
            text = json.dumps(
                site,
                ensure_ascii=False,
                indent=2
            )
            return {
                "list": [{
                    "vod_name":
                        "["
                        + ext.upper()
                        + "] "
                        + filename,
                    "vod_pic": "",
                    "vod_play_from":
                        "配置",
                    "vod_play_url":
                        "查看配置$"
                        + path,
                    "vod_content":
                        (
                            "已自动保存到:\n"
                            + self.SAVE_PATH
                            + "\n\n"
                            + "站点配置:\n"
                            + text
                        )
                }]
            }
        except Exception as e:
            return {
                "list": [{
                    "vod_name": "解析错误",
                    "vod_content": str(e)
                }]
            }

    # ============================================================
    # 搜索
    # ============================================================

    def searchContent(
        self,
        key,
        quick
    ):
        result = []
        keyword = str(key).lower()
        for info in self.file_index.values():
            if keyword not in info["name"].lower():
                continue
            vid = base64.b64encode(
                (
                    info["ext"].upper()
                    + "|"
                    + info["path"]
                ).encode("utf-8")
            ).decode("utf-8")
            result.append({
                "vod_id": vid,
                "vod_name":
                    "["
                    + info["ext"].upper()
                    + "] "
                    + info["name"],
                "vod_pic": "",
                "vod_remarks":
                    self.build_api(info)
            })
        return {
            "list": result
        }

    # ============================================================
    # 播放
    # ============================================================

    def playerContent(
        self,
        flag,
        id,
        vipFlags
    ):
        url = (
            id.split("$")[-1]
            if "$" in id
            else id
        )
        return {
            "url": url,
            "header": {},
            "parse": 0
        }

    # ============================================================
    # 销毁
    # ============================================================

    def destroy(self):
        return "destroy"
