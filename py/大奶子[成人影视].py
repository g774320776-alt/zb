# -*- coding: utf-8 -*-

import json
import urllib.parse
import requests


try:
    from base.spider import Spider
except ImportError:
    class Spider:
        pass


class Spider(Spider):

    name = "大奶子资源站"

    # =========================
    # 基础配置
    # =========================

    BASE_URL = "https://www.danaizizy1-5.com"

    # 苹果CMS JSON接口（倒叙推荐）
    API_URL = "https://apidanaizi.com/api.php/providedao/vod/?ac=list"

    # M3U8解析接口
    PLAY_URL = "https://jiexidanaizi.com/?url="

    PLAY_FLAG = "dnzm3u8"


    HEADERS = {
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120 Safari/537.36",

        "Referer":
        "https://www.danaizizy1-5.com/"
    }


    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)


    # =========================
    # 初始化
    # =========================

    def init(self, extend=""):
        return None


    # =========================
    # 请求
    # =========================

    def _get(self, url):

        try:
            r = self.session.get(
                url,
                timeout=15
            )

            r.encoding = "utf-8"

            return r.text

        except Exception:
            return ""


    # =========================
    # 首页
    # =========================

    def homeContent(self, filter):

        try:

            data = self._get(self.API_URL)

            obj = json.loads(data)

            videos = obj.get("list", [])

            result = {
                "class": [],
                "list": []
            }


            # 分类
            types = {}

            for vod in videos:

                tid = vod.get("type_id")
                name = vod.get("type_name")

                if tid and tid not in types:

                    types[tid] = name

                    result["class"].append({
                        "type_id": str(tid),
                        "type_name": name
                    })


            # 推荐
            for vod in videos[:20]:

                result["list"].append(
                    self._vod(vod)
                )


            return result


        except Exception:

            return {
                "class": [],
                "list": []
            }


    # =========================
    # 分类
    # =========================

    def categoryContent(self, tid, pg, filter, extend):

        try:

            url = (
                self.API_URL
                + "&t="
                + str(tid)
                + "&pg="
                + str(pg)
            )


            data = self._get(url)

            obj = json.loads(data)


            videos = obj.get("list", [])


            return {

                "page": int(pg),

                "pagecount": 999,

                "limit": 20,

                "total": 99999,

                "list":
                [
                    self._vod(v)
                    for v in videos
                ]

            }


        except Exception:

            return {
                "page": pg,
                "pagecount": 1,
                "limit": 0,
                "total": 0,
                "list": []
            }



    # =========================
    # 搜索
    # =========================

    def searchContent(self, key, quick, pg="1"):

        try:

            wd = urllib.parse.quote(key)


            url = (
                self.API_URL
                + "&wd="
                + wd
                + "&pg="
                + str(pg)
            )


            data = self._get(url)

            obj = json.loads(data)


            return {
                "list":
                [
                    self._vod(v)
                    for v in obj.get("list", [])
                ]
            }


        except Exception:

            return {
                "list": []
            }



    # =========================
    # 详情
    # =========================

    def detailContent(self, ids):

        try:

            url = (
                self.API_URL
                + "&ids="
                + str(ids[0])
            )


            data = self._get(url)

            obj = json.loads(data)

            vod = obj.get("list", [])[0]


            play_url = vod.get(
                "vod_play_url",
                ""
            )


            return {

                "list":[{

                    "vod_id":
                    vod.get("vod_id"),

                    "vod_name":
                    vod.get("vod_name"),

                    "vod_pic":
                    vod.get("vod_pic"),

                    "type_name":
                    vod.get("type_name"),

                    "vod_year":
                    vod.get("vod_year"),

                    "vod_area":
                    vod.get("vod_area"),

                    "vod_actor":
                    vod.get("vod_actor"),

                    "vod_director":
                    vod.get("vod_director"),

                    "vod_content":
                    vod.get("vod_content"),

                    "vod_play_from":
                    self.PLAY_FLAG,

                    "vod_play_url":
                    play_url

                }]

            }


        except Exception:

            return {
                "list":[]
            }



    # =========================
    # 播放
    # =========================

    def playerContent(self, flag, id, vipFlags):


        url = id


        # m3u8直连

        if ".m3u8" in url:

            return {

                "parse": 0,

                "playUrl": "",

                "url": url,

                "header":
                self.HEADERS

            }


        # mp4直连

        if ".mp4" in url:

            return {

                "parse": 0,

                "playUrl": "",

                "url": url,

                "header":
                self.HEADERS

            }


        # 其他调用解析

        return {

            "parse": 1,

            "playUrl": "",

            "url":
            self.PLAY_URL
            +
            urllib.parse.quote(url),

            "header":
            self.HEADERS

        }



    # =========================
    # 数据转换
    # =========================

    def _vod(self, vod):

        return {

            "vod_id":
            str(vod.get("vod_id")),

            "vod_name":
            vod.get("vod_name",""),

            "vod_pic":
            vod.get("vod_pic",""),

            "vod_remarks":
            vod.get("vod_remarks","")

        }