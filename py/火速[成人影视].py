# -*- coding: utf-8 -*-
"""
Fongmi Spider - 按截图 Demo 的 API 结构重写

截图中可见的接口：
1. JSON 采集：
   https://api.huosuapi.cc/api.php/provide/vod/
2. XML 采集：
   https://api.huosuapi.cc/api.php/provide/vod/at/xml
3. 备用 JSON：
   https://api.huosuapi.cc/api.php/provide/vod/
4. 备用 XML：
   https://api.huosuapi.cc/api.php/provide/vod/at/xml
5. 小说/文章：
   https://sex8zy1.com/api.php/provide/art/?ac=list
6. M3U8 解析：
   https://xbww888.com/?url=

说明：
- 仅调用站点公开 API，并把返回的播放地址交给 Fongmi。
- 不在 Spider 内下载视频文件。
- 兼容常见 MacCMS / 苹果 CMS 的 vod JSON 格式。
"""

import json
import re
import urllib.parse
import requests


try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass


class Spider(BaseSpider):
    # 主接口：截图 Demo 中显示的 JSON 接口
    API_URL = "https://api.huosuapi.cc/api.php/provide/vod/"
    API_XML = "https://api.huosuapi.cc/api.php/provide/vod/at/xml"

    # 备用接口
    BACKUP_API_URL = "https://api.huosuapi.cc/api.php/provide/vod/"
    BACKUP_API_XML = "https://api.huosuapi.cc/api.php/provide/vod/at/xml"

    # 文章/小说接口
    ART_URL = "https://sex8zy1.com/api.php/provide/art/"

    # 截图 Demo 中的 M3U8 解析接口
    PARSE_URL = "https://api.huosuapi.cc/?url="

    # 如需隐藏分类，在这里填写分类名称
    HIDE_TYPES = set()  # 按截图保留全部分类

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13; Mobile) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Referer": "https://api.huosuapi.cc/",
    }

    def __init__(self):
        self.name = "火速X站资源"
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self._class_cache = None

    # ============================================================
    # 基础方法
    # ============================================================

    def getName(self):
        return self.name

    def init(self, extend=""):
        return None

    def getDependence(self):
        return []

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        if not url:
            return False

        text = str(url).strip().lower()
        clean_url = text.split("#", 1)[0].split("?", 1)[0]

        return (
            clean_url.endswith(".m3u8")
            or clean_url.endswith(".mp4")
            or ".m3u8/" in clean_url
            or ".mp4/" in clean_url
        )

    # ============================================================
    # HTTP
    # ============================================================

    def _get_json(self, url):
        try:
            response = self.session.get(
                url,
                timeout=15,
                verify=False,
            )
            response.raise_for_status()

            text = response.text.strip()
            if not text:
                return {}

            return json.loads(text)

        except Exception:
            return {}

    def _request_api(
        self,
        page=1,
        pagecount=20,
        keyword="",
        type_id=None,
        use_backup=False,
    ):
        base = self.BACKUP_API_URL if use_backup else self.API_URL

        params = {
            "ac": "list",
            "pg": page,
            "pagesize": pagecount,
        }

        if keyword:
            params["wd"] = keyword

        if type_id not in (None, ""):
            params["t"] = type_id

        url = base + "?" + urllib.parse.urlencode(params)
        return self._get_json(url)

    def _request_with_backup(
        self,
        page=1,
        pagecount=20,
        keyword="",
        type_id=None,
    ):
        # 先请求截图中的主 JSON 接口
        data = self._request_api(
            page=page,
            pagecount=pagecount,
            keyword=keyword,
            type_id=type_id,
            use_backup=False,
        )

        if self._has_valid_data(data):
            return data

        # 主接口失败，再请求备用 JSON
        return self._request_api(
            page=page,
            pagecount=pagecount,
            keyword=keyword,
            type_id=type_id,
            use_backup=True,
        )

    def _has_valid_data(self, data):
        return isinstance(data, dict) and (
            isinstance(data.get("list"), list)
            or isinstance(data.get("class"), list)
        )

    # ============================================================
    # 首页
    # ============================================================

    def homeContent(self, filter):
        data = self._request_with_backup(
            page=1,
            pagecount=20,
        )

        classes = self._parse_classes(data)
        videos = self._parse_videos(data)

        return {
            "class": classes,
            "filters": {},
            "list": videos,
            "parse": 0,
            "jx": 0,
        }

    def homeVideoContent(self):
        data = self._request_with_backup(
            page=1,
            pagecount=20,
        )

        return {
            "list": self._parse_videos(data)
        }

    # ============================================================
    # 分类
    # ============================================================

    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = int(pg)
        except Exception:
            page = 1

        data = self._request_with_backup(
            page=page,
            pagecount=20,
            type_id=tid,
        )

        videos = self._parse_videos(data)

        pagecount = self._get_int(data, "pagecount", 0)
        total = self._get_int(data, "total", len(videos))

        if pagecount <= 0:
            pagecount = page + 1 if len(videos) >= 20 else page

        if pagecount < page:
            pagecount = page

        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": total,
        }

    # ============================================================
    # 搜索
    # ============================================================

    def searchContent(self, key, quick, pg=1):
        try:
            page = int(pg)
        except Exception:
            page = 1

        data = self._request_with_backup(
            page=page,
            pagecount=20,
            keyword=key,
        )

        videos = self._parse_videos(data)

        pagecount = self._get_int(data, "pagecount", 0)
        total = self._get_int(data, "total", len(videos))

        if pagecount <= 0:
            pagecount = page + 1 if len(videos) >= 20 else page

        if pagecount < page:
            pagecount = page

        return {
            "list": videos,
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": total,
        }

    # ============================================================
    # 详情
    # ============================================================

    def detailContent(self, ids):
        if not ids:
            return {"list": []}

        vod_id = str(ids[0]).strip()
        if not vod_id:
            return {"list": []}

        # 主接口尝试 detail
        data = self._get_json(
            self.API_URL
            + "?"
            + urllib.parse.urlencode({
                "ac": "detail",
                "ids": vod_id,
            })
        )

        vods = data.get("list", []) if isinstance(data, dict) else []

        # detail 不支持时，回退到 list + ids
        if not isinstance(vods, list) or not vods:
            data = self._get_json(
                self.API_URL
                + "?"
                + urllib.parse.urlencode({
                    "ac": "list",
                    "ids": vod_id,
                })
            )
            vods = data.get("list", []) if isinstance(data, dict) else []

        # 主接口没有结果时，尝试备用接口
        if not isinstance(vods, list) or not vods:
            data = self._get_json(
                self.BACKUP_API_URL
                + "?"
                + urllib.parse.urlencode({
                    "ac": "detail",
                    "ids": vod_id,
                })
            )
            vods = data.get("list", []) if isinstance(data, dict) else []

        if not isinstance(vods, list) or not vods:
            return {"list": []}

        vod = vods[0]
        if not isinstance(vod, dict):
            return {"list": []}

        title = self._clean(vod.get("vod_name", ""))

        pic = self._fix_pic_url(
            vod.get("vod_pic")
            or vod.get("vod_pic_thumb")
            or vod.get("vod_pic_slide")
            or vod.get("vod_pic_screenshot")
            or vod.get("pic")
            or vod.get("cover")
            or ""
        )

        year = self._clean(vod.get("vod_year", ""))
        area = self._clean(vod.get("vod_area", ""))
        type_name = self._clean(vod.get("type_name", ""))
        remarks = self._clean(vod.get("vod_remarks", ""))
        actor = self._clean(vod.get("vod_actor", ""))
        director = self._clean(vod.get("vod_director", ""))
        content = self._clean_html(vod.get("vod_content", ""))

        play_from, play_url = self._parse_play_sources(vod)

        return {
            "list": [{
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "type_name": type_name,
                "vod_year": year,
                "vod_area": area,
                "vod_remarks": remarks,
                "vod_actor": actor,
                "vod_director": director,
                "vod_content": content,
                "vod_play_from": play_from,
                "vod_play_url": play_url,
            }]
        }

    # ============================================================
    # 播放
    # ============================================================

    def playerContent(self, flag, id, vipFlags):
        url = str(id or "").strip()

        if not url:
            return {
                "parse": 0,
                "jx": 0,
                "url": "",
            }

        # m3u8 / mp4 直链直接播放
        if self.isVideoFormat(url):
            return {
                "parse": 0,
                "jx": 0,
                "url": url,
                "header": {
                    "User-Agent": self.HEADERS["User-Agent"],
                    "Referer": self.HEADERS["Referer"],
                },
            }

        # 非直链交给截图 Demo 中的解析接口
        parse_url = self.PARSE_URL + urllib.parse.quote(url, safe="")

        return {
            "parse": 0,
            "jx": 0,
            "url": parse_url,
            "header": {
                "User-Agent": self.HEADERS["User-Agent"],
                "Referer": self.HEADERS["Referer"],
            },
        }

    # ============================================================
    # 分类解析
    # ============================================================

    def _parse_classes(self, data):
        result = []

        if not isinstance(data, dict):
            return result

        type_list = data.get("class", [])

        if not isinstance(type_list, list):
            return result

        for item in type_list:
            if not isinstance(item, dict):
                continue

            tid = (
                item.get("type_id")
                if item.get("type_id") is not None
                else item.get("id")
            )

            name = (
                item.get("type_name")
                or item.get("name")
                or ""
            )

            if tid is None or not name:
                continue

            name = self._clean(name)

            if name in self.HIDE_TYPES:
                continue

            result.append({
                "type_id": str(tid),
                "type_name": name,
            })

        return result

    # ============================================================
    # 视频列表解析
    # ============================================================

    def _parse_videos(self, data):
        result = []

        if not isinstance(data, dict):
            return result

        vod_list = data.get("list", [])

        if not isinstance(vod_list, list):
            return result

        for vod in vod_list:
            if not isinstance(vod, dict):
                continue

            vod_id = vod.get("vod_id")
            title = vod.get("vod_name", "")

            if vod_id is None or not title:
                continue

            pic = (
                vod.get("vod_pic")
                or vod.get("vod_pic_thumb")
                or vod.get("vod_pic_slide")
                or vod.get("vod_pic_screenshot")
                or vod.get("pic")
                or vod.get("cover")
                or ""
            )

            pic = self._fix_pic_url(pic)

            remarks = (
                vod.get("vod_remarks")
                or vod.get("vod_time")
                or vod.get("vod_duration")
                or ""
            )

            result.append({
                "vod_id": str(vod_id),
                "vod_name": self._clean(title),
                "vod_pic": self._clean(pic),
                "vod_remarks": self._clean(remarks),
            })

        return result

    # ============================================================
    # 播放源解析
    # ============================================================

    def _parse_play_sources(self, vod):
        play_from = self._clean(vod.get("vod_play_from", ""))
        play_url = self._clean(vod.get("vod_play_url", ""))

        if play_from and play_url:
            return play_from, play_url

        # 兼容部分 CMS 的其他字段
        candidates = [
            "vod_play_url",
            "vod_play_urls",
            "play_url",
            "play_urls",
        ]

        for key in candidates:
            value = vod.get(key)

            if not value:
                continue

            if isinstance(value, list):
                value = "$$$".join(
                    str(x) for x in value if x
                )

            value = self._clean(value)

            if value:
                return "API", value

        return "API", ""

    # ============================================================
    # 工具函数
    # ============================================================

    def _fix_pic_url(self, value):
        pic = self._clean(value)

        if not pic:
            return ""

        # 去掉 URL 后面误混入的引号/HTML 属性
        match = re.match(
            r"^(https?:)?//[^\s'\">]+",
            pic,
            re.I,
        )

        if match:
            pic = match.group(0)

        # //example.com/a.jpg
        if pic.startswith("//"):
            return "http:" + pic

        # /upload/a.jpg
        if pic.startswith("/"):
            return urllib.parse.urljoin(
                "https://xingba222.com/",
                pic,
            )

        return pic

    def _clean(self, value):
        if value is None:
            return ""

        if isinstance(value, (dict, list)):
            return str(value)

        return str(value).strip()

    def _clean_html(self, value):
        value = self._clean(value)

        # 删除 HTML 标签
        value = re.sub(r"<[^>]+>", " ", value)

        # 合并空白
        value = re.sub(r"\s+", " ", value)

        return value.strip()

    def _get_int(self, data, key, default=0):
        try:
            value = data.get(key, default)

            if isinstance(value, str):
                value = value.strip()

            return int(value)

        except Exception:
            return default
