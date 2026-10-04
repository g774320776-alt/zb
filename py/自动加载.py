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
        "parses": [
            {
                "name": "盘古",
                "type": 0,
                "url": "shturl.cc/buomqXDHfE3yFSg0d9dSaLHmq3RV",
                "ext": {
                    "header": {
                        "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
                    }
                }
            },
            {
                "name": "789解析1",
                "type": 0,
                "url": "shturl.cc/6WndJhRIcyv4tu25oS0u5xXMAew"
            },
            {
                "name": "789解析2",
                "type": 0,
                "url": "shturl.cc/VVGJR98ujiooxP03VfQXNP"
            },
            {
                "name": "虾米解析",
                "type": 0,
                "url": "https://jx.xmflv.com/?url="
            },
            {
                "name": "淘片解析",
                "type": 0,
                "url": "https://jx.yparse.com/index.php?url="
            },
            {
                "name": "解析1",
                "type": 0,
                "url": "https://huayong.net/999/?v="
            },
            {
                "name": "解析2",
                "type": 0,
                "url": "https://jx.m3u8.tv/jiexi/?url="
            },
            {
                "name": "解析3",
                "type": 0,
                "url": "https://t2.qlplayer.cyou/player/analysis.php?v="
            },
            {
                "name": "解析4",
                "type": 0,
                "url": "shturl.cc/W8LzEZIqr6Bumwr2J9w3lgUqZC"
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
                "name": "冰豆",
                "type": 0,
                "url": "shturl.cc/PpA385DKeJEN"
            },
            {
                "name": "爱酷",
                "type": 0,
                "url": "shturl.cc/m4LCKrehXPiMyUcjml40B"
            },
            {
                "name": "云解析",
                "type": 0,
                "url": "https://jx.yparse.com/index.php?url=",
                "ext": {
                    "header": {
                        "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
                    }
                }
            },
            {
                "name": "777",
                "type": 0,
                "url": "https://jx.jsonplayer.com/player/?url=",
                "ext": {
                    "header": {
                        "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
                    }
                }
            },
            {
                "name": "-剖云-",
                "type": 0,
                "url": "https://www.kkvip2022.com/vip/jiexi1/?url=",
                "ext": {
                    "header": {
                        "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
                    }
                }
            },
            {
                "name": "-全看-",
                "type": 0,
                "url": "https://jx.quankan.app/?url=",
                "ext": {
                    "header": {
                        "user-agent": "Mozilla/5.0 (Linux; Android 13; V2049A Build/TP1A.220624.014; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36"
                    }
                }
            }
        ],
        "doh": [
            {
                "name": "Google",
                "url": "https://dns.google/dns-query",
                "ips": [
                    "8.8.4.4",
                    "8.8.8.8"
                ]
            },
            {
                "name": "Cloudflare",
                "url": "https://cloudflare-dns.com/dns-query",
                "ips": [
                    "1.1.1.1",
                    "1.0.0.1",
                    "2606:4700:4700::1111",
                    "2606:4700:4700::1001"
                ]
            },
            {
                "name": "AdGuard",
                "url": "https://dns.adguard.com/dns-query",
                "ips": [
                    "94.140.14.140",
                    "94.140.14.141"
                ]
            },
            {
                "name": "DNSWatch",
                "url": "https://resolver2.dns.watch/dns-query",
                "ips": [
                    "84.200.69.80",
                    "84.200.70.40"
                ]
            },
            {
                "name": "Quad9",
                "url": "https://dns.quad9.net/dns-query",
                "ips": [
                    "9.9.9.9",
                    "149.112.112.112"
                ]
            }
        ],
        "ads": [
            "mozai.4gtv.tv",
            "static-mozai.4gtv.tv"
        ],
        "lives": [],
        "ijk": [
            {
                "group": "软解码",
                "options": [
                    {"category": 4, "name": "opensles", "value": "0"},
                    {"category": 4, "name": "overlay-format", "value": "842225234"},
                    {"category": 4, "name": "framedrop", "value": "1"},
                    {"category": 4, "name": "soundtouch", "value": "1"},
                    {"category": 4, "name": "start-on-prepared", "value": "1"},
                    {"category": 1, "name": "http-detect-range-support", "value": "0"},
                    {"category": 1, "name": "fflags", "value": "fastseek"},
                    {"category": 2, "name": "skip_loop_filter", "value": "48"},
                    {"category": 4, "name": "reconnect", "value": "1"},
                    {"category": 4, "name": "enable-accurate-seek", "value": "0"},
                    {"category": 4, "name": "mediacodec", "value": "0"},
                    {"category": 4, "name": "mediacodec-auto-rotate", "value": "0"},
                    {"category": 4, "name": "mediacodec-handle-resolution-change", "value": "0"},
                    {"category": 4, "name": "mediacodec-hevc", "value": "0"},
                    {"category": 1, "name": "dns_cache_timeout", "value": "600000000"}
                ]
            },
            {
                "group": "硬解码",
                "options": [
                    {"category": 4, "name": "opensles", "value": "0"},
                    {"category": 4, "name": "overlay-format", "value": "842225234"},
                    {"category": 4, "name": "framedrop", "value": "1"},
                    {"category": 4, "name": "soundtouch", "value": "1"},
                    {"category": 4, "name": "start-on-prepared", "value": "1"},
                    {"category": 1, "name": "http-detect-range-support", "value": "0"},
                    {"category": 1, "name": "fflags", "value": "fastseek"},
                    {"category": 2, "name": "skip_loop_filter", "value": "48"},
                    {"category": 4, "name": "reconnect", "value": "1"},
                    {"category": 4, "name": "enable-accurate-seek", "value": "0"},
                    {"category": 4, "name": "mediacodec", "value": "1"},
                    {"category": 4, "name": "mediacodec-auto-rotate", "value": "1"},
                    {"category": 4, "name": "mediacodec-handle-resolution-change", "value": "1"},
                    {"category": 4, "name": "mediacodec-hevc", "value": "1"},
                    {"category": 1, "name": "dns_cache_timeout", "value": "600000000"}
                ]
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
