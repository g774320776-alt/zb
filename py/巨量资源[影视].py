
# -*- coding: utf-8 -*-
# 巨量资源 Fongmi Spider
# 文件名：juliang.py

import re
import requests
from urllib.parse import urlparse

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass


class Spider(BaseSpider):

    API_URL = "https://api.juliang.live/api/provide/vod/"

    def init(self, extend=""):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://juliang.app/"
        })
        self.timeout = 15

    def getName(self):
        return "巨量资源"

    def getDependence(self):
        return []

    def isVideoFormat(self, url):
        return any(ext in str(url).lower() for ext in (
            ".m3u8", ".mp4", ".mpd"
        ))

    def manualVideoCheck(self):
        return False

    # API 请求
    def request_api(self, params=None):
        try:
            response = self.session.get(
                self.API_URL,
                params=params or {},
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as e:
            print("[巨量资源] 请求失败:", e)
            return {}

    # 分类数据
    def get_classes(self, data):
        classes = data.get("class") or []
        result = []

        for item in classes:
            type_id = item.get("type_id")
            type_name = item.get("type_name", "")
            if type_id is None or not type_name:
                continue

            result.append({
                "type_id": str(type_id),
                "type_name": str(type_name)
            })

        return result

    # 视频数据统一格式
    def make_vod(self, item):
        vod_id = item.get("vod_id")
        if vod_id is None:
            return None

        return {
            "vod_id": str(vod_id),
            "vod_name": item.get("vod_name", ""),
            "vod_pic": (
                item.get("vod_pic")
                or item.get("vod_pic_original", "")
            ),
            "vod_remarks": item.get("vod_remarks", ""),
            "vod_year": item.get("vod_year", ""),
            "vod_area": item.get("vod_area", ""),
            "vod_lang": item.get("vod_lang", ""),
            "vod_actor": item.get("vod_actor", ""),
            "vod_director": item.get("vod_director", ""),
            "vod_content": (
                item.get("vod_content")
                or item.get("vod_blurb", "")
            ),
            "type_id": str(item.get("type_id", "")),
            "type_name": item.get("type_name", "")
        }

    # 首页
    def homeContent(self, filter):
        data = self.request_api({
            "ac": "list",
            "pg": 1
        })

        result = []
        for item in data.get("list") or []:
            vod = self.make_vod(item)
            if vod:
                result.append(vod)

        return {
            "class": self.get_classes(data),
            "list": result
        }

    # 分类分页
    def categoryContent(self, tid, pg, filter, extend):
        try:
            page = max(1, int(pg))
        except (ValueError, TypeError):
            page = 1

        params = {
            "ac": "list",
            "t": str(tid),
            "pg": page
        }

        if isinstance(extend, dict):
            for key, value in extend.items():
                if value is not None and str(value).strip():
                    params[str(key)] = str(value)

        data = self.request_api(params)

        result = []
        for item in data.get("list") or []:
            vod = self.make_vod(item)
            if vod:
                result.append(vod)

        return {
            "list": result,
            "page": int(data.get("page") or page),
            "pagecount": int(data.get("pagecount") or 0),
            "limit": int(data.get("limit") or 20),
            "total": int(data.get("total") or 0)
        }

    # 搜索
    def searchContent(self, key, quick, page="1"):
        try:
            page = max(1, int(page))
        except (ValueError, TypeError):
            page = 1

        data = self.request_api({
            "ac": "list",
            "wd": key,
            "pg": page
        })

        result = []
        for item in data.get("list") or []:
            vod = self.make_vod(item)
            if vod:
                result.append(vod)

        return {
            "list": result
        }

    # 统一线路名称分隔符
    def split_sources(self, value):
        if not value:
            return []
        return [
            s.strip()
            for s in re.split(r"\$\$\$|,", str(value))
            if s.strip()
        ]

    # 详情
    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vod_id = str(ids[0]) if ids else ""
        else:
            vod_id = str(ids)

        if not vod_id:
            return {"list": []}

        data = self.request_api({
            "ac": "detail",
            "ids": vod_id
        })

        videos = data.get("list") or []
        if not videos:
            return {"list": []}

        item = videos[0]
        vod = self.make_vod(item)

        if not vod:
            return {"list": []}

        # 线路来源兼容逗号和 $$$
        sources = self.split_sources(
            item.get("vod_play_from", "")
        )

        # 每条线路的剧集列表通常以 $$$ 分隔
        play_groups = [
            group.strip()
            for group in str(
                item.get("vod_play_url", "")
            ).split("$$$")
        ]

        # 保证来源名称与播放列表对应
        if not sources and play_groups:
            sources = [
                "线路" + str(i + 1)
                for i in range(len(play_groups))
            ]

        if len(sources) < len(play_groups):
            for i in range(len(sources), len(play_groups)):
                sources.append("线路" + str(i + 1))

        count = min(len(sources), len(play_groups))
        vod["vod_play_from"] = "$$$".join(sources[:count])
        vod["vod_play_url"] = "$$$".join(
            play_groups[:count]
        )

        return {"list": [vod]}

    # 播放地址
    def playerContent(self, flag, id, vipFlags):
        url = str(id).strip()
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return {
                "parse": 0,
                "url": "",
                "header": {}
            }

        return {
            "parse": 0,
            "playUrl": "",
            "url": url,
            "header": {
                "User-Agent": self.session.headers.get(
                    "User-Agent", ""
                ),
                "Referer": "https://juliang.app/"
            }
        }

    # 关闭会话
    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass
