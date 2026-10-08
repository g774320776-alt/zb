# -*- coding: utf-8 -*-

import json
import time
import requests

from base.spider import Spider


class Spider(Spider):

    # =========================================================
    # 基础配置
    # =========================================================

    API_URL = "https://yuanlib.com/api.php/provide/vod/"
    SITE_URL = "https://yuanlib.com/"

    UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    TIMEOUT = 15
    RETRY_COUNT = 2

    # =========================================================
    # 需要过滤的分类
    # =========================================================

    REMOVE_TYPES = {
        "成人动漫",
        "另类口味",
        "另类口",
        "ai剧集",
        "欧美",
        "伦理三级",
        "国产专题",
        "日韩专题",
        "真实乱伦",
    }

    # =========================================================
    # 初始化
    # =========================================================

    def init(self, extend=""):

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": self.UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": self.SITE_URL,
        })

        self.timeout = self.TIMEOUT

    # =========================================================
    # 基础信息
    # =========================================================

    def getName(self):
        return "元力资源"

    def getDependence(self):
        return []

    # =========================================================
    # 判断是否为需要过滤的分类
    # =========================================================

    def _is_removed_type(self, type_name):

        type_name = self._str(type_name)

        if not type_name:
            return False

        return type_name.strip().lower() in {
            self._str(name).lower()
            for name in self.REMOVE_TYPES
        }

    # =========================================================
    # 视频格式判断
    # =========================================================

    def isVideoFormat(self, url):

        if not url:
            return False

        url = str(url).lower().strip()

        path = url.split("?", 1)[0]
        path = path.split("#", 1)[0]

        return (
            path.endswith(".m3u8")
            or path.endswith(".m3u")
            or path.endswith(".mp4")
            or path.endswith(".flv")
            or path.endswith(".ts")
            or ".m3u8?" in url
            or ".m3u?" in url
            or ".mp4?" in url
            or ".flv?" in url
            or ".ts?" in url
        )

    def manualVideoCheck(self):
        return False

    # =========================================================
    # 安全字符串
    # =========================================================

    def _str(self, value):

        if value is None:
            return ""

        try:
            return str(value).strip()
        except Exception:
            return ""

    # =========================================================
    # 安全整数
    # =========================================================

    def _int(self, value, default=0):

        try:

            if value is None:
                return default

            return int(value)

        except Exception:
            return default

    # =========================================================
    # HTTP 请求
    # =========================================================

    def _get_json(self, params=None):

        params = params or {}

        for attempt in range(self.RETRY_COUNT + 1):

            try:

                response = self.session.get(
                    self.API_URL,
                    params=params,
                    timeout=self.timeout
                )

                response.raise_for_status()

                try:

                    data = response.json()

                except Exception:

                    text = response.text.strip()

                    if not text:
                        return {}

                    data = json.loads(text)

                if isinstance(data, dict):
                    return data

                print(
                    "[yuanlib] invalid json type:",
                    type(data)
                )

                return {}

            except Exception as e:

                print(
                    "[yuanlib] API error:",
                    e,
                    "attempt:",
                    attempt + 1
                )

                if attempt < self.RETRY_COUNT:
                    time.sleep(0.5)

        return {}

    # =========================================================
    # 图片地址处理
    # =========================================================

    def _fix_pic(self, pic):

        pic = self._str(pic)

        if not pic:
            return ""

        # 完整 HTTP URL
        if pic.startswith("http://"):
            return pic

        if pic.startswith("https://"):
            return pic

        # 协议相对地址
        if pic.startswith("//"):
            return "https:" + pic

        # 根目录相对地址
        if pic.startswith("/"):
            return self.SITE_URL.rstrip("/") + pic

        # 普通相对地址
        return (
            self.SITE_URL.rstrip("/")
            + "/"
            + pic.lstrip("/")
        )

    # =========================================================
    # 播放地址清洗
    # =========================================================

    def _clean_url(self, url):

        url = self._str(url)

        if not url:
            return ""

        return url

    # =========================================================
    # VOD 列表转换
    # =========================================================

    def _make_vod_list(self, items):

        result = []

        if not isinstance(items, list):
            return result

        for vod in items:

            if not isinstance(vod, dict):
                continue

            vod_id = self._str(
                vod.get("vod_id")
            )

            vod_name = self._str(
                vod.get("vod_name")
            )

            if not vod_id:
                continue

            if not vod_name:
                continue

            # -------------------------------------------------
            # 根据视频所属分类过滤
            # -------------------------------------------------

            type_name = self._str(
                vod.get("type_name")
            )

            if self._is_removed_type(type_name):
                continue

            # 某些接口可能提供缩略图字段
            pic = vod.get("vod_pic")

            if not pic:
                pic = vod.get("vod_pic_thumb")

            item = {
                "vod_id": vod_id,

                "vod_name": vod_name,

                "vod_pic": self._fix_pic(pic),

                "vod_remarks": self._str(
                    vod.get("vod_remarks")
                ),

                "vod_year": self._str(
                    vod.get("vod_year")
                ),

                "vod_score": self._str(
                    vod.get("vod_score")
                ),

                "vod_sub": self._str(
                    vod.get("vod_sub")
                ),

                "vod_tag": self._str(
                    vod.get("vod_tag")
                ),
            }

            result.append(item)

        return result

    # =========================================================
    # 首页
    # =========================================================

    def homeContent(self, filter):

        result = {
            "class": [],
            "list": []
        }

        data = self._get_json({
            "ac": "list",
            "pg": 1
        })

        if not isinstance(data, dict):
            return result

        # -----------------------------------------------------
        # 分类
        # -----------------------------------------------------

        classes = data.get("class", [])

        if isinstance(classes, list):

            for item in classes:

                if not isinstance(item, dict):
                    continue

                type_id = item.get("type_id")

                type_name = self._str(
                    item.get("type_name")
                )

                if type_id is None:
                    continue

                if not type_name:
                    continue

                # 过滤指定分类
                if self._is_removed_type(type_name):
                    continue

                result["class"].append({
                    "type_id": self._str(type_id),
                    "type_name": type_name
                })

        # -----------------------------------------------------
        # 首页视频
        # -----------------------------------------------------

        result["list"] = self._make_vod_list(
            data.get("list", [])
        )

        return result

    # =========================================================
    # 分类
    # =========================================================

    def categoryContent(
        self,
        tid,
        pg,
        filter,
        extend
    ):

        page = self._int(pg, 1)

        if page < 1:
            page = 1

        tid = self._str(tid)

        # -----------------------------------------------------
        # 如果 tid 属于被过滤分类，则直接返回空
        # -----------------------------------------------------

        blocked_type_ids = set()

        # 尝试从扩展参数获取分类名称
        if isinstance(extend, dict):

            type_name = self._str(
                extend.get("type_name")
            )

            if self._is_removed_type(type_name):
                return {
                    "page": page,
                    "pagecount": 1,
                    "limit": 20,
                    "total": 0,
                    "list": []
                }

        params = {
            "ac": "list",
            "t": tid,
            "pg": page
        }

        data = self._get_json(params)

        if not isinstance(data, dict):
            return {
                "page": page,
                "pagecount": 1,
                "limit": 20,
                "total": 0,
                "list": []
            }

        # -----------------------------------------------------
        # 检查接口返回的分类信息
        # -----------------------------------------------------

        type_name = self._str(
            data.get("type_name")
        )

        if self._is_removed_type(type_name):
            return {
                "page": page,
                "pagecount": 1,
                "limit": 20,
                "total": 0,
                "list": []
            }

        pagecount = self._int(
            data.get("pagecount"),
            1
        )

        limit = self._int(
            data.get("limit"),
            20
        )

        total = self._int(
            data.get("total"),
            0
        )

        if pagecount < 1:
            pagecount = 1

        if limit < 1:
            limit = 20

        if total < 0:
            total = 0

        return {
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": total,
            "list": self._make_vod_list(
                data.get("list", [])
            )
        }

    # =========================================================
    # 搜索
    # =========================================================

    def searchContent(
        self,
        key,
        quick,
        pg="1"
    ):

        page = self._int(pg, 1)

        if page < 1:
            page = 1

        key = self._str(key)

        if not key:

            return {
                "page": 1,
                "pagecount": 1,
                "limit": 20,
                "total": 0,
                "list": []
            }

        data = self._get_json({
            "ac": "list",
            "wd": key,
            "pg": page
        })

        if not isinstance(data, dict):

            return {
                "page": page,
                "pagecount": 1,
                "limit": 20,
                "total": 0,
                "list": []
            }

        pagecount = self._int(
            data.get("pagecount"),
            1
        )

        limit = self._int(
            data.get("limit"),
            20
        )

        total = self._int(
            data.get("total"),
            0
        )

        if pagecount < 1:
            pagecount = 1

        if limit < 1:
            limit = 20

        if total < 0:
            total = 0

        return {
            "page": page,
            "pagecount": pagecount,
            "limit": limit,
            "total": total,
            "list": self._make_vod_list(
                data.get("list", [])
            )
        }

    # =========================================================
    # 播放地址解析
    #
    # vod_play_from:
    #   播放源1$$$播放源2
    #
    # vod_play_url:
    #   第1集$URL1#第2集$URL2$$$第1集$URL3
    #
    # =========================================================

    def _parse_play(self, vod):

        if not isinstance(vod, dict):
            return "", ""

        play_from = self._str(
            vod.get("vod_play_from")
        )

        play_url = self._str(
            vod.get("vod_play_url")
        )

        if not play_url:
            return "", ""

        from_list = []

        if play_from:
            from_list = play_from.split("$$$")

        url_list = play_url.split("$$$")

        final_from = []
        final_url = []

        for index, urls in enumerate(url_list):

            urls = self._str(urls)

            if not urls:
                continue

            # -------------------------------------------------
            # 播放源名称
            # -------------------------------------------------

            if index < len(from_list):

                source_name = self._str(
                    from_list[index]
                )

            else:

                source_name = ""

            if not source_name:

                source_name = "线路{}".format(
                    index + 1
                )

            # -------------------------------------------------
            # 集数
            # -------------------------------------------------

            episodes = []

            for episode in urls.split("#"):

                episode = episode.strip()

                if not episode:
                    continue

                name = ""
                url = ""

                # 标准格式：
                #
                # 第1集$https://xxx
                #

                if "$" in episode:

                    name, url = episode.split(
                        "$",
                        1
                    )

                    name = self._str(name)
                    url = self._clean_url(url)

                else:

                    name = "正片"

                    url = self._clean_url(
                        episode
                    )

                if not url:
                    continue

                if not name:
                    name = "正片"

                episodes.append(
                    "{}${}".format(
                        name,
                        url
                    )
                )

            if not episodes:
                continue

            final_from.append(
                source_name
            )

            final_url.append(
                "#".join(episodes)
            )

        return (
            "$$$".join(final_from),
            "$$$".join(final_url)
        )

    # =========================================================
    # 详情
    # =========================================================

    def detailContent(self, ids):

        if not ids:
            return {
                "list": []
            }

        # -----------------------------------------------------
        # 兼容 list / tuple
        # -----------------------------------------------------

        if isinstance(ids, (list, tuple)):

            if not ids:
                return {
                    "list": []
                }

            vod_id = ids[0]

        else:

            vod_id = ids

        vod_id = self._str(vod_id)

        if not vod_id:
            return {
                "list": []
            }

        # -----------------------------------------------------
        # 某些框架可能传：
        #
        # 123,456
        #
        # 当前 Spider 按单详情处理
        # -----------------------------------------------------

        if "," in vod_id:

            vod_id = vod_id.split(
                ",",
                1
            )[0].strip()

        if not vod_id:
            return {
                "list": []
            }

        # -----------------------------------------------------
        # 请求详情
        # -----------------------------------------------------

        data = self._get_json({
            "ac": "detail",
            "ids": vod_id
        })

        if not isinstance(data, dict):
            return {
                "list": []
            }

        items = data.get("list", [])

        if not isinstance(items, list):
            return {
                "list": []
            }

        if not items:
            return {
                "list": []
            }

        vod = items[0]

        if not isinstance(vod, dict):
            return {
                "list": []
            }

        # -----------------------------------------------------
        # 详情分类过滤
        # -----------------------------------------------------

        type_name = self._str(
            vod.get("type_name")
        )

        if self._is_removed_type(type_name):
            return {
                "list": []
            }

        vod_class = self._str(
            vod.get("vod_class")
        )

        # 某些接口可能没有 type_name，
        # 因此同时检查 vod_class
        if self._is_removed_type(vod_class):
            return {
                "list": []
            }

        # -----------------------------------------------------
        # 播放信息
        # -----------------------------------------------------

        play_from, play_url = self._parse_play(
            vod
        )

        # -----------------------------------------------------
        # 图片
        # -----------------------------------------------------

        pic = vod.get("vod_pic")

        if not pic:
            pic = vod.get("vod_pic_thumb")

        # -----------------------------------------------------
        # 详情
        # -----------------------------------------------------

        detail = {

            "vod_id": self._str(
                vod.get("vod_id")
            ),

            "vod_name": self._str(
                vod.get("vod_name")
            ),

            "vod_pic": self._fix_pic(
                pic
            ),

            "vod_year": self._str(
                vod.get("vod_year")
            ),

            "vod_area": self._str(
                vod.get("vod_area")
            ),

            "vod_lang": self._str(
                vod.get("vod_lang")
            ),

            "vod_remarks": self._str(
                vod.get("vod_remarks")
            ),

            "vod_actor": self._str(
                vod.get("vod_actor")
            ),

            "vod_director": self._str(
                vod.get("vod_director")
            ),

            "vod_writer": self._str(
                vod.get("vod_writer")
            ),

            "vod_duration": self._str(
                vod.get("vod_duration")
            ),

            "vod_content": self._str(
                vod.get("vod_content")
            ),

            "vod_blurb": self._str(
                vod.get("vod_blurb")
            ),

            "vod_class": vod_class,

            "type_name": type_name,

            "vod_score": self._str(
                vod.get("vod_score")
            ),

            "vod_play_from": play_from,

            "vod_play_url": play_url,
        }

        # -----------------------------------------------------
        # 简介为空时使用 blurb
        # -----------------------------------------------------

        if not detail["vod_content"]:

            detail["vod_content"] = (
                detail["vod_blurb"]
            )

        return {
            "list": [detail]
        }

    # =========================================================
    # 播放
    # =========================================================

    def playerContent(
        self,
        flag,
        id,
        vipFlags
    ):

        url = self._str(id)

        # -----------------------------------------------------
        # 空地址
        # -----------------------------------------------------

        if not url:

            return {
                "parse": 0,
                "url": "",
                "header": {
                    "User-Agent": self.UA,
                    "Referer": self.SITE_URL
                }
            }

        # -----------------------------------------------------
        # 当前 API 如果提供的是最终播放地址，
        # 直接交给播放器。
        # -----------------------------------------------------

        return {
            "parse": 0,
            "url": url,
            "header": {
                "User-Agent": self.UA,
                "Referer": self.SITE_URL
            }
        }

    # =========================================================
    # 本地代理
    # =========================================================

    def localProxy(self, param):

        return [
            200,
            "text/plain",
            b""
        ]