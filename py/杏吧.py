-- coding: utf-8 --

"""
杏吧.py
Fongmi / Cat / TVBox Spider
杏吧资源 CMS JSON API 版本

数据接口：
JSON : https://xingba111.com/api.php/provide/vod/?ac=list
XML  : https://xingba111.com/api.php/provide/vod/at/xml

M3U8 解析接口（截图中提供）：
https://xbww888.com/?url=

功能：

1. 首页


2. 分类


3. 分类分页


4. 搜索


5. 详情


6. CMS JSON 播放源解析


7. m3u8 / mp4 直链识别


8. 非直链时尝试交给 M3U8 解析接口


9. 请求异常处理


10. 兼容常见 MacCMS / 苹果 CMS 字段


11. 不下载视频，只返回/转交站点提供的播放地址
"""



import json
import re
import urllib.parse
import requests

try:
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
pass

try:
from base.spider import Spider as BaseSpider
except ImportError:
class BaseSpider:
pass

class Spider(BaseSpider):

# ============================================================  
# CMS API  
# ============================================================  

API_URL = "https://xingba111.com/api.php/provide/vod/"  
API_XML = "https://xingba111.com/api.php/provide/vod/at/xml"  

# 截图中显示的 M3U8 解析接口。  
# 只有在 API 返回的地址不是 m3u8/mp4 直链时才使用。  
PARSE_URL = "https://xbww888.com/?url="  

PAGE_SIZE = 20  

HEADERS = {  
    "User-Agent": (  
        "Mozilla/5.0 (Linux; Android 13) "  
        "AppleWebKit/537.36 (KHTML, like Gecko) "  
        "Chrome/120.0.0.0 Mobile Safari/537.36"  
    ),  
    "Accept": "application/json,text/plain,*/*",  
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",  
    "Connection": "keep-alive",  
    "Referer": "https://xingba111.com/",  
}  

# ============================================================  
# 分类显示优化  
# ============================================================  
# 指定分类显示顺序。未写入这里的分类会自动排在后面。  
# 如果不需要自定义顺序，保持为空即可。  
TYPE_ORDER = []  

# 不想显示的分类名称。  
HIDE_TYPES = set()  

# 分类名称包含以下关键词时隐藏。  
# 例如站点 API 偶尔返回“公告 / 推荐 / 其他”之类的非视频分类，  
# 可以直接在这里过滤。  
HIDE_TYPE_KEYWORDS = set()  

# 自动清理分类名称中的多余空白。  
CLEAN_TYPE_NAME = True  

# 同名分类只保留第一次出现的项目。  
DEDUP_TYPES = True  

def __init__(self):  
    self.name = "老色p"  
    self.session = requests.Session()  
    self.session.headers.update(self.HEADERS)  
    self._class_cache = None  

# ============================================================  
# Fongmi 基础接口  
# ============================================================  

def getName(self):  
    return self.name  

def init(self, extend=""):  
    return None  

def getDependence(self):  
    return []  

def isVideoFormat(self, url):  
    """  
    判断是否为视频直链。  
    支持：  
    - .m3u8  
    - .mp4  
    - 带查询参数的 m3u8/mp4  
    """  
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

def manualVideoCheck(self):  
    return False  

# ============================================================  
# 网络请求  
# ============================================================  

def _get_json(self, url, params=None):  
    """  
    请求 JSON API。  

    所有异常均捕获，避免资源站暂时不可用时  
    直接让整个 Spider 崩溃。  
    """  
    try:  
        response = self.session.get(  
            url,  
            params=params,  
            timeout=15,  
            verify=False,  
        )  

        response.raise_for_status()  

        text = response.text.strip()  

        if not text:  
            return {}  

        try:  
            data = response.json()  
        except Exception:  
            data = json.loads(text)  

        return data if isinstance(data, dict) else {}  

    except Exception as e:  
        print("杏吧 API 请求异常:", str(e))  
        return {}  

def _request_api(  
    self,  
    page=1,  
    pagecount=20,  
    keyword="",  
    tid="",  
    detail=False,  
    vod_id="",  
):  
    """  
    统一请求苹果 CMS / MacCMS 风格 API。  

    列表：  
    ac=list  
    pg=页码  
    pagesize=每页数量  
    t=分类 ID  
    wd=搜索关键词  

    详情：  
    ac=detail  
    ids=视频 ID  
    """  

    params = {}  

    if detail:  
        params["ac"] = "detail"  
        if vod_id:  
            params["ids"] = str(vod_id)  
    else:  
        params["ac"] = "list"  
        params["pg"] = max(1, int(page))  
        params["pagesize"] = max(1, int(pagecount))  

        if tid not in ("", None):  
            params["t"] = str(tid)  

        if keyword:  
            params["wd"] = str(keyword)  

        if vod_id:  
            params["ids"] = str(vod_id)  

    return self._get_json(  
        self.API_URL,  
        params=params,  
    )  

# ============================================================  
# 首页  
# ============================================================  

def homeContent(self, filter):  
    data = self._request_api(  
        page=1,  
        pagecount=self.PAGE_SIZE,  
    )  

    classes = self._parse_classes(data)  

    if classes:  
        self._class_cache = classes  
    elif self._class_cache:  
        classes = self._class_cache  

    return {  
        "class": classes,  
        "filters": {},  
        "list": self._parse_videos(data),  
        "parse": 0,  
        "jx": 0,  
    }  

def homeVideoContent(self):  
    data = self._request_api(  
        page=1,  
        pagecount=self.PAGE_SIZE,  
    )  

    return {  
        "list": self._parse_videos(data)  
    }  

# ============================================================  
# 分类 + 分页  
# ============================================================  

def categoryContent(self, tid, pg, filter, extend):  
    try:  
        page = int(pg)  
    except Exception:  
        page = 1  

    if page < 1:  
        page = 1  

    data = self._request_api(  
        page=page,  
        pagecount=self.PAGE_SIZE,  
        tid=tid,  
    )  

    videos = self._parse_videos(data)  

    pagecount = self._get_int(  
        data,  
        "pagecount",  
        0,  
    )  

    total = self._get_int(  
        data,  
        "total",  
        0,  
    )  

    # API 没有 pagecount 时，根据本页是否满页进行保守判断。  
    if pagecount <= 0:  
        if len(videos) >= self.PAGE_SIZE:  
            pagecount = page + 1  
        else:  
            pagecount = page  

    if pagecount < page:  
        pagecount = page  

    if total <= 0:  
        total = len(videos)  

    return {  
        "list": videos,  
        "page": page,  
        "pagecount": pagecount,  
        "limit": self.PAGE_SIZE,  
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

    if page < 1:  
        page = 1  

    key = str(key or "").strip()  

    if not key:  
        return {  
            "list": [],  
            "page": page,  
            "pagecount": 1,  
            "limit": self.PAGE_SIZE,  
            "total": 0,  
        }  

    data = self._request_api(  
        page=page,  
        pagecount=self.PAGE_SIZE,  
        keyword=key,  
    )  

    videos = self._parse_videos(data)  

    pagecount = self._get_int(data, "pagecount", 0)  
    total = self._get_int(data, "total", 0)  

    if pagecount <= 0:  
        if len(videos) >= self.PAGE_SIZE:  
            pagecount = page + 1  
        else:  
            pagecount = page  

    if pagecount < page:  
        pagecount = page  

    if total <= 0:  
        total = len(videos)  

    return {  
        "list": videos,  
        "page": page,  
        "pagecount": pagecount,  
        "limit": self.PAGE_SIZE,  
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

    # 第一优先：ac=detail  
    data = self._request_api(  
        detail=True,  
        vod_id=vod_id,  
    )  

    vods = self._get_vod_list(data)  

    # 某些 CMS 对 ac=detail 支持不完整，  
    # 再尝试 ac=list + ids。  
    if not vods:  
        data = self._request_api(  
            page=1,  
            pagecount=1,  
            vod_id=vod_id,  
        )  
        vods = self._get_vod_list(data)  

    if not vods:  
        return {"list": []}  

    vod = vods[0]  

    real_id = self._first(  
        vod,  
        "vod_id",  
        "id",  
    ) or vod_id  

    title = self._clean(  
        self._first(  
            vod,  
            "vod_name",  
            "name",  
            "title",  
        )  
    )  

    pic = self._fix_pic_url(  
        self._first(  
            vod,  
            "vod_pic",  
            "vod_pic_thumb",  
            "vod_pic_slide",  
            "vod_pic_screenshot",  
            "pic",  
            "cover",  
            "image",  
        )  
    )  

    type_name = self._clean(  
        self._first(  
            vod,  
            "type_name",  
            "vod_type",  
            "category",  
        )  
    )  

    year = self._clean(  
        self._first(  
            vod,  
            "vod_year",  
            "year",  
        )  
    )  

    area = self._clean(  
        self._first(  
            vod,  
            "vod_area",  
            "area",  
        )  
    )  

    remarks = self._clean(  
        self._first(  
            vod,  
            "vod_remarks",  
            "vod_remark",  
            "vod_time",  
            "vod_duration",  
            "remarks",  
        )  
    )  

    actor = self._clean(  
        self._first(  
            vod,  
            "vod_actor",  
            "actor",  
        )  
    )  

    director = self._clean(  
        self._first(  
            vod,  
            "vod_director",  
            "director",  
        )  
    )  

    content = self._clean_html(  
        self._first(  
            vod,  
            "vod_content",  
            "vod_blurb",  
            "vod_desc",  
            "content",  
            "description",  
        )  
    )  

    play_from, play_url = self._parse_play_sources(vod)  

    return {  
        "list": [{  
            "vod_id": str(real_id),  
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
    """  
    播放逻辑：  

    1. m3u8 / mp4：  
       直接 parse=0 播放。  

    2. 其他 URL：  
       使用截图中提供的解析接口：  
       https://xbww888.com/?url=  

    注意：  
    Spider 不下载或保存视频文件。  
    """  

    url = str(id or "").strip()  

    if not url:  
        return {  
            "parse": 0,  
            "jx": 0,  
            "url": "",  
        }  

    # 已经是标准视频直链，直接播放。  
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

    # 非直链时，交给截图中的 M3U8 解析接口。  
    parse_url = self.PARSE_URL + urllib.parse.quote(  
        url,  
        safe="",  
    )  

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
    """  
    解析 CMS 分类，并做以下优化：  

    1. 兼容 class / type / types 三种常见字段。  
    2. 兼容 type_id / typeid / id。  
    3. 清理分类名称中的多余空白。  
    4. 按名称精确隐藏指定分类。  
    5. 按关键词隐藏指定分类。  
    6. 去除重复 type_id。  
    7. 支持 TYPE_ORDER 自定义排序。  
    8. 保持 API 原始分类 ID，不修改实际请求参数。  
    """  
    result = []  

    if not isinstance(data, dict):  
        return result  

    type_list = data.get("class")  

    if not isinstance(type_list, list):  
        type_list = data.get("type")  

    if not isinstance(type_list, list):  
        type_list = data.get("types")  

    if not isinstance(type_list, list):  
        return result  

    seen_id = set()  
    seen_name = set()  

    for item in type_list:  
        if not isinstance(item, dict):  
            continue  

        tid = self._first(  
            item,  
            "type_id",  
            "typeid",  
            "id",  
        )  

        name = self._first(  
            item,  
            "type_name",  
            "typename",  
            "name",  
        )  

        if tid is None or name is None:  
            continue  

        tid = str(tid).strip()  

        if self.CLEAN_TYPE_NAME:  
            name = re.sub(r"\\s+", " ", str(name)).strip()  
        else:  
            name = str(name).strip()  

        if not tid or not name:  
            continue  

        # 精确隐藏  
        if name in self.HIDE_TYPES:  
            continue  

        # 关键词隐藏  
        if any(keyword and keyword in name  
               for keyword in self.HIDE_TYPE_KEYWORDS):  
            continue  

        # ID 去重  
        if tid in seen_id:  
            continue  

        # 名称去重，避免同名分类重复显示  
        if self.DEDUP_TYPES and name in seen_name:  
            continue  

        seen_id.add(tid)  
        seen_name.add(name)  

        result.append({  
            "type_id": tid,  
            "type_name": name,  
        })  

    # 自定义分类顺序。  
    # TYPE_ORDER 中没有出现的分类保持原 API 顺序，  
    # 并自动排到自定义分类之后。  
    if self.TYPE_ORDER:  
        order_map = {  
            str(name).strip(): index  
            for index, name in enumerate(self.TYPE_ORDER)  
        }  

        result.sort(  
            key=lambda item: (  
                order_map.get(item["type_name"], 100000),  
                item["type_id"],  
            )  
        )  

    return result  

# ============================================================  
# 视频列表解析  
# ============================================================  

def _parse_videos(self, data):  
    result = []  

    if not isinstance(data, dict):  
        return result  

    vod_list = self._get_vod_list(data)  
    seen = set()  

    for vod in vod_list:  
        if not isinstance(vod, dict):  
            continue  

        vod_id = self._first(  
            vod,  
            "vod_id",  
            "id",  
        )  

        title = self._first(  
            vod,  
            "vod_name",  
            "name",  
            "title",  
        )  

        if vod_id is None or not title:  
            continue  

        vod_id = str(vod_id).strip()  
        title = self._clean(title)  

        if not vod_id or not title:  
            continue  

        if vod_id in seen:  
            continue  

        seen.add(vod_id)  

        pic = self._first(  
            vod,  
            "vod_pic",  
            "vod_pic_thumb",  
            "vod_pic_slide",  
            "vod_pic_screenshot",  
            "pic",  
            "cover",  
            "image",  
        )  

        pic = self._fix_pic_url(pic)  

        remarks = self._first(  
            vod,  
            "vod_remarks",  
            "vod_remark",  
            "vod_time",  
            "vod_duration",  
            "remarks",  
        )  

        result.append({  
            "vod_id": vod_id,  
            "vod_name": title,  
            "vod_pic": pic,  
            "vod_remarks": self._clean(remarks),  
        })  

    return result  

# ============================================================  
# 播放源解析  
# ============================================================  

def _parse_play_sources(self, vod):  
    """  
    兼容常见 MacCMS：  

    vod_play_from:  
        线路1$$$线路2  

    vod_play_url:  
        正片$https://xxx.m3u8#第二集$https://xxx.m3u8  
        $$$  
        正片$https://xxx.mp4  
    """  

    play_from = self._first(  
        vod,  
        "vod_play_from",  
        "play_from",  
        "source",  
    )  

    play_url = self._first(  
        vod,  
        "vod_play_url",  
        "vod_play_urls",  
        "play_url",  
        "play_urls",  
    )  

    play_from = self._normalize_play_value(play_from)  
    play_url = self._normalize_play_value(play_url)  

    if play_url:  
        if not play_from:  
            play_from = "API"  

        return play_from, play_url  

    # 部分 API 可能直接返回单个播放 URL。  
    direct_url = self._first(  
        vod,  
        "url",  
        "vod_url",  
        "video_url",  
        "play",  
    )  

    direct_url = self._normalize_play_value(direct_url)  

    if direct_url:  
        return "API", direct_url  

    return "API", ""  

# ============================================================  
# 获取 vod list  
# ============================================================  

def _get_vod_list(self, data):  
    if not isinstance(data, dict):  
        return []  

    vod_list = data.get("list")  

    if isinstance(vod_list, list):  
        return vod_list  

    # 兼容 data.list  
    nested = data.get("data")  

    if isinstance(nested, dict):  
        vod_list = nested.get("list")  
        if isinstance(vod_list, list):  
            return vod_list  

    return []  

# ============================================================  
# 图片 URL 修复  
# ============================================================  

def _fix_pic_url(self, value):  
    """  
    图片处理：  

    - 保留 API 实际返回的 http/https 协议  
    - 支持 //xxx.jpg  
    - 支持 /upload/xxx.jpg  
    - 去除图片 URL 后面意外混入的 HTML 属性  

    不强制把 http 改成 https，  
    避免图片服务器没有 HTTPS 时封面失效。  
    """  

    pic = self._clean(value)  

    if not pic:  
        return ""  

    # 提取 URL 的主体，避免类似：  
    # https://xxx/a.jpg" alt="xxx"  
    match = re.match(  
        r'^(https?:)?//[^"\'>\s]+',  
        pic,  
        re.I,  
    )  

    if match:  
        pic = match.group(0)  

    # 协议相对地址  
    if pic.startswith("//"):  
        return "https:" + pic  

    # 站内绝对路径  
    if pic.startswith("/"):  
        return urllib.parse.urljoin(  
            self.API_URL,  
            pic,  
        )  

    return pic  

# ============================================================  
# 通用工具  
# ============================================================  

def _first(self, data, *keys):  
    if not isinstance(data, dict):  
        return ""  

    for key in keys:  
        value = data.get(key)  

        if value is None:  
            continue  

        if isinstance(value, str):  
            if value.strip():  
                return value.strip()  
            continue  

        if value != "":  
            return value  

    return ""  

def _normalize_play_value(self, value):  
    """  
    把字符串、list、dict 形式的播放字段  
    统一为 Fongmi 常用的播放格式。  
    """  

    if value is None:  
        return ""  

    if isinstance(value, str):  
        return value.strip()  

    if isinstance(value, list):  
        values = []  

        for item in value:  
            if isinstance(item, dict):  
                name = self._clean(  
                    self._first(  
                        item,  
                        "name",  
                        "title",  
                        "play_name",  
                    )  
                )  

                url = self._clean(  
                    self._first(  
                        item,  
                        "url",  
                        "play_url",  
                        "video_url",  
                    )  
                )  

                if url:  
                    if name:  
                        values.append(  
                            name + "$" + url  
                        )  
                    else:  
                        values.append(url)  

            elif item:  
                values.append(  
                    str(item).strip()  
                )  

        # 列表内部的播放项用 # 分隔。  
        return "#".join(values)  

    if isinstance(value, dict):  
        name = self._clean(  
            self._first(  
                value,  
                "name",  
                "title",  
            )  
        )  

        url = self._clean(  
            self._first(  
                value,  
                "url",  
                "play_url",  
                "video_url",  
            )  
        )  

        if url:  
            return (  
                name + "$" + url  
                if name  
                else url  
            )  

        return ""  

    return str(value).strip()  

def _clean(self, value):  
    if value is None:  
        return ""  

    if isinstance(value, (dict, list)):  
        return str(value).strip()  

    return str(value).strip()  

def _clean_html(self, value):  
    value = self._clean(value)  

    if not value:  
        return ""  

    # 删除 script/style  
    value = re.sub(  
        r"<(script|style)[^>]*>.*?</\1>",  
        " ",  
        value,  
        flags=re.I | re.S,  
    )  

    # 删除 HTML 标签  
    value = re.sub(  
        r"<[^>]+>",  
        " ",  
        value,  
    )  

    # 常见 HTML 实体  
    value = (  
        value  
        .replace("&nbsp;", " ")  
        .replace("&amp;", "&")  
        .replace("&quot;", '"')  
        .replace("&#39;", "'")  
        .replace("&lt;", "<")  
        .replace("&gt;", ">")  
    )  

    # 合并连续空白  
    value = re.sub(  
        r"\s+",  
        " ",  
        value,  
    )  

    return value.strip()  

def _get_int(self, data, key, default=0):  
    try:  
        if not isinstance(data, dict):  
            return default  

        value = data.get(key, default)  

        if isinstance(value, str):  
            value = value.strip()  

        return int(value)  

    except Exception:  
        return default