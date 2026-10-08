# -*- coding: utf-8 -*-

"""
xjzy.py
Fongmi / TVBox Spider

苹果CMS JSON接口:
https://api.xjzyapi.com/provide/vod

XML接口:
https://api.xjzyapi.com/provide/vod?at=xml&ac=list

M3U8解析:
https://api.xjzyapi.com/aplayer/player.html?autoplay=1&movurl=
"""

import json
import requests
import urllib.parse


try:
    from base.spider import Spider
except:
    class Spider:
        pass


class Spider(Spider):

    def __init__(self):
        self.name = "迅捷资源"

        self.API = (
            "https://api.xjzyapi.com/provide/vod"
        )

        self.PARSE = (
            "https://api.xjzyapi.com/aplayer/player.html?autoplay=1&movurl="
        )

        self.UA = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )

        self.REFERER = (
            "https://api.xjzyapi.com/"
        )


    def getName(self):
        return self.name


    def init(self, extend=""):
        pass


    # 首页
    def homeContent(self, filter):

        data = self._request(
            {
                "ac": "list",
                "pg": 1
            }
        )

        return {
            "class": self._classes(data),
            "list": self._videos(data)
        }


    # 分类
    def categoryContent(
            self,
            tid,
            pg,
            filter,
            extend):

        data = self._request(
            {
                "ac": "list",
                "t": tid,
                "pg": pg
            }
        )

        return {
            "page": pg,
            "pagecount": 999,
            "limit": 20,
            "total": 99999,
            "list": self._videos(data)
        }



    # 搜索
    def searchContent(
            self,
            key,
            quick,
            pg="1"):

        data = self._request(
            {
                "ac": "list",
                "wd": key,
                "pg": pg
            }
        )

        return {
            "list": self._videos(data)
        }



    # 详情
    def detailContent(self, ids):

        data = self._request(
            {
                "ac": "detail",
                "ids": ids[0]
            }
        )

        vod = data.get("list", [{}])[0]

        play = vod.get(
            "vod_play_url",
            ""
        )

        return {
            "list": [
                {
                    "vod_id": vod.get("vod_id"),
                    "vod_name": vod.get("vod_name"),
                    "vod_pic": vod.get("vod_pic"),
                    "type_name": vod.get("type_name"),
                    "vod_content": vod.get("vod_content"),
                    "vod_play_from": "迅捷资源",
                    "vod_play_url": play
                }
            ]
        }



    # 播放
    def playerContent(
            self,
            flag,
            id,
            vipFlags):

        url = id.strip()

        headers = {
            "User-Agent": self.UA,
            "Referer": self.REFERER
        }


        # m3u8直接播放
        if ".m3u8" in url.lower():

            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": headers
            }


        # mp4直接播放
        if ".mp4" in url.lower():

            return {
                "parse": 0,
                "playUrl": "",
                "url": url,
                "header": headers
            }


        # 其它走解析
        return {
            "parse": 1,
            "playUrl": "",
            "url": (
                self.PARSE +
                urllib.parse.quote(url)
            ),
            "header": headers
        }



    # 请求接口
    def _request(self, params):

        try:

            r = requests.get(
                self.API,
                params=params,
                headers={
                    "User-Agent": self.UA
                },
                timeout=15
            )

            r.encoding = "utf-8"

            return r.json()

        except Exception:

            return {}



    # 分类
    def _classes(self, data):

        result = []

        for item in data.get("class", []):

            result.append(
                {
                    "type_id":
                    str(item.get("type_id")),

                    "type_name":
                    item.get("type_name")
                }
            )

        return result



    # 视频列表
    def _videos(self, data):

        videos = []

        for v in data.get("list", []):

            videos.append(
                {
                    "vod_id":
                    str(v.get("vod_id")),

                    "vod_name":
                    v.get("vod_name"),

                    "vod_pic":
                    v.get("vod_pic"),

                    "vod_remarks":
                    v.get("vod_remarks","")
                }
            )

        return videos