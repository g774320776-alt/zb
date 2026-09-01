import concurrent.futures
import os
import re
import time
from urllib.parse import urlparse

import requests
import urllib3


# ============================================================
# 基础配置
# ============================================================

SOURCE_URLS = [
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

OUTPUT_DIR = "output"

# 获取 IPTV 列表超时时间
FETCH_TIMEOUT = 20

# 检测直播地址超时时间
CHECK_TIMEOUT = 10

# 并发检测数量
MAX_WORKERS = 30

# 获取列表失败重试次数
RETRIES = 2

# 是否检测直播地址
ENABLE_CHECK = True

# ------------------------------------------------------------
# 重要：
#
# False = 不因为 301/302/403 等状态简单粗暴删除
# 最终结合响应内容判断
# ------------------------------------------------------------

STRICT_HTTP_200 = False

# User-Agent
USER_AGENT = (
    "Mozilla/5.0 "
    "(Linux; Android 13) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/120.0.0.0 Mobile Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Connection": "keep-alive",
}

urllib3.disable_warnings(
    urllib3.exceptions.InsecureRequestWarning
)


# ============================================================
# 广告 / 垃圾关键词
# ============================================================

BAN_WORDS = [
    "广告",
    "购物",
    "测试",
    "垃圾",
    "备用源",
    "vip",
    "付费",
    "游戏",
    "棋牌",
    "成人",
    "解密",
    "高清备用",
    "直播源分享",
    "推广",
    "福利",
    "试看",
]


# ============================================================
# 少儿频道关键词
# ============================================================

KID_KEYWORDS = [
    "少儿",
    "动画",
    "卡通",
    "金鹰卡通",
    "卡酷少儿",
    "优漫卡通",
    "哈哈炫动",
    "炫动卡通",
    "幼儿",
    "儿童",
]


# ============================================================
# CCTV 判断
# ============================================================

CCTV_PATTERN = re.compile(
    r"^CCTV[--－]?\s*\d{1,2}([+＋]?)$",
    re.IGNORECASE
)


# ============================================================
# URL 判断
# ============================================================

def is_valid_url(url: str) -> bool:
    """检查 HTTP / HTTPS URL"""

    if not url:
        return False

    url = url.strip()

    if not re.match(
        r"^https?://",
        url,
        re.IGNORECASE
    ):
        return False

    try:

        parsed = urlparse(url)

        if not parsed.hostname:
            return False

        return True

    except Exception:

        return False


# ============================================================
# 频道名称清洗
# ============================================================

def clean_program_name(name: str) -> str:

    if not name:
        return ""

    name = name.strip()

    # 去掉常见图标
    name = re.sub(
        r"[★☆✨🔴💥🔥⚡️⭐️📺🎬]",
        "",
        name
    )

    # 删除 HTML
    name = re.sub(
        r"<[^>]+>",
        "",
        name
    )

    # 全角逗号
    name = name.replace(
        "，",
        ","
    )

    # 连续空白
    name = re.sub(
        r"\s+",
        " ",
        name
    )

    # 画质后缀
    name = re.sub(
        r"[\s_\-–—]*(高清|超清|标清|HD|SD|FHD|UHD|4K|8K|2K)$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    # 线路 / 备用 / 数字后缀
    name = re.sub(
        r"[\s_\-–—]+(?:备用|备份|线路\d+|\d+)$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    return name.strip(
        " ,，|"
    )


# ============================================================
# 垃圾频道判断
# ============================================================

def is_bad_name(name: str) -> bool:

    if not name:
        return True

    name_low = name.lower()

    for word in BAN_WORDS:

        if word.lower() in name_low:
            return True

    return False


# ============================================================
# 频道分类
#
# 分类保持原来的四类
# ============================================================

def get_channel_group(name: str) -> str:

    if not name:
        return "其他频道"

    upper_name = name.upper()

    # --------------------------------------------------------
    # 少儿频道优先
    # --------------------------------------------------------

    for keyword in KID_KEYWORDS:

        if keyword in name:

            return "少儿频道"

    # --------------------------------------------------------
    # CCTV
    # --------------------------------------------------------

    if CCTV_PATTERN.match(name):

        return "央视频道"

    if "央视" in name:

        return "央视频道"

    if "CCTV" in upper_name:

        return "央视频道"

    # --------------------------------------------------------
    # 卫视
    # --------------------------------------------------------

    if "卫视" in name:

        return "卫视频道"

    # --------------------------------------------------------
    # 其他
    # --------------------------------------------------------

    return "地方频道"


# ============================================================
# 获取 IPTV 源列表
# ============================================================

def fetch_source(url: str):

    print()
    print(f"正在获取源：{url}")

    for attempt in range(
        1,
        RETRIES + 2
    ):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=FETCH_TIMEOUT,
                verify=False,
                allow_redirects=True,
            )

            if response.status_code == 200:

                response.encoding = (
                    response.apparent_encoding
                    or response.encoding
                    or "utf-8"
                )

                print(
                    f"✓ 获取成功 "
                    f"HTTP {response.status_code} "
                    f"{len(response.text)} 字节"
                )

                return response.text

            print(
                f"× 第 {attempt} 次失败："
                f"HTTP {response.status_code}"
            )

        except requests.RequestException as e:

            print(
                f"× 第 {attempt} 次异常：{e}"
            )

        if attempt <= RETRIES:

            time.sleep(1)

    print(
        f"× 放弃源：{url}"
    )

    return None


# ============================================================
# TXT 解析
# ============================================================

def parse_txt(content: str):

    streams = []

    for raw_line in content.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        # 支持：
        #
        # CCTV1,http://xxx
        # CCTV1,https://xxx
        #

        match = re.match(
            r"^\s*(.+?)\s*,\s*(https?://\S+)\s*$",
            line,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        name = clean_program_name(
            match.group(1)
        )

        url = match.group(2).strip()

        if not name:
            continue

        if is_bad_name(name):
            continue

        if not is_valid_url(url):
            continue

        streams.append({
            "program_name": name,
            "stream_url": url,
        })

    return streams


# ============================================================
# M3U 解析
# ============================================================

def parse_m3u(content: str):

    streams = []

    current_name = None

    for raw_line in content.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # ----------------------------------------------------
        # EXTINF
        # ----------------------------------------------------

        if line.upper().startswith("#EXTINF"):

            current_name = None

            # 优先 tvg-name
            match = re.search(
                r'tvg-name\s*=\s*"([^"]+)"',
                line,
                flags=re.IGNORECASE,
            )

            if match:

                current_name = match.group(1)

            # 没有 tvg-name
            elif "," in line:

                current_name = (
                    line.rsplit(",", 1)[1]
                )

            if current_name:

                current_name = clean_program_name(
                    current_name
                )

            continue

        # ----------------------------------------------------
        # URL
        # ----------------------------------------------------

        if re.match(
            r"^https?://",
            line,
            re.IGNORECASE
        ):

            if (
                current_name
                and not is_bad_name(current_name)
                and is_valid_url(line)
            ):

                streams.append({
                    "program_name": current_name,
                    "stream_url": line,
                })

            current_name = None

    return streams


# ============================================================
# 自动识别 TXT / M3U
# ============================================================

def parse_source(content: str):

    stripped = content.lstrip()

    if stripped.upper().startswith("#EXTM3U"):

        return parse_m3u(content)

    if "#EXTINF" in content.upper():

        return parse_m3u(content)

    return parse_txt(content)


# ============================================================
# URL 规范化
# ============================================================

def normalize_url(url: str):

    return url.strip().rstrip()


# ============================================================
# 去重
#
# 重要：
# 不再单独根据 URL 去重。
#
# 例如：
#
# CCTV5,http://abc/live
# CCTV5+,http://abc/live
# CCTV文化精品,http://abc/live
#
# 三个频道都会保留。
# ============================================================

def deduplicate_streams(streams):

    result = []

    seen = set()

    for item in streams:

        name = item["program_name"].strip()

        url = normalize_url(
            item["stream_url"]
        )

        key = (
            name.lower(),
            url.lower()
        )

        if key in seen:
            continue

        seen.add(key)

        result.append({
            "program_name": name,
            "stream_url": url,
        })

    return result


# ============================================================
# 判断响应内容是否像真正的直播数据
# ============================================================

def is_live_content(
    content_type: str,
    data: bytes,
    url: str
) -> bool:

    content_type = (
        content_type or ""
    ).lower()

    url_low = url.lower()

    # --------------------------------------------------------
    # M3U8
    # --------------------------------------------------------

    if (
        "mpegurl" in content_type
        or "m3u8" in content_type
        or ".m3u8" in url_low
    ):

        try:

            text = data.decode(
                "utf-8",
                errors="ignore"
            ).lstrip()

            if (
                "#EXTM3U" in text
                or "#EXT-X-" in text
            ):

                return True

        except Exception:

            pass

    # --------------------------------------------------------
    # MPEG-TS
    #
    # TS 每 188 字节通常以 0x47 开始
    # --------------------------------------------------------

    if len(data) >= 188:

        if data[0] == 0x47:

            return True

        if len(data) >= 376:

            if (
                data[0] == 0x47
                and data[188] == 0x47
            ):

                return True

            if (
                data[0] == 0x47
                and data[376 - 1] == 0x47
            ):

                return True

    # --------------------------------------------------------
    # FLV
    # --------------------------------------------------------

    if data.startswith(
        b"FLV"
    ):

        return True

    # --------------------------------------------------------
    # 常见直播 Content-Type
    # --------------------------------------------------------

    live_types = [
        "video/",
        "audio/",
        "application/octet-stream",
        "application/vnd.apple.mpegurl",
        "application/x-mpegurl",
    ]

    for item in live_types:

        if item in content_type:

            return True

    # --------------------------------------------------------
    # 有些服务器 Content-Type 不规范：
    # 如果 URL 明确是 m3u8
    # --------------------------------------------------------

    if ".m3u8" in url_low:

        return True

    return False


# ============================================================
# 检测单个直播源
# ============================================================

def check_stream(item):

    name = item["program_name"]
    url = item["stream_url"]

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=CHECK_TIMEOUT,
            verify=False,
            allow_redirects=True,
            stream=True,
        )

        status = response.status_code

        # ----------------------------------------------------
        # 严格 HTTP 模式
        # ----------------------------------------------------

        if STRICT_HTTP_200:

            if status != 200:

                response.close()

                return (
                    item,
                    False,
                    status,
                    "HTTP"
                )

        else:

            # 允许所有 2xx
            if not (
                200 <= status < 300
            ):

                response.close()

                return (
                    item,
                    False,
                    status,
                    "HTTP"
                )

        # ----------------------------------------------------
        # 读取少量真实数据
        #
        # 不下载完整视频，只读取前 8KB
        # ----------------------------------------------------

        try:

            data = next(
                response.iter_content(
                    chunk_size=8192
                ),
                b""
            )

        except Exception:

            data = b""

        content_type = (
            response.headers.get(
                "Content-Type",
                ""
            )
        )

        response.close()

        # ----------------------------------------------------
        # 判断直播内容
        # ----------------------------------------------------

        if is_live_content(
            content_type,
            data,
            url
        ):

            return (
                item,
                True,
                status,
                "直播数据"
            )

        # ----------------------------------------------------
        # 对 HTTP 200 但无法识别内容的源
        #
        # CCTV / 央视源不要轻易删除。
        #
        # 这一步是为了避免 GitHub Actions 环境
        # 对部分 CDN / 防盗链源误判。
        # ----------------------------------------------------

        group = get_channel_group(
            name
        )

        if group == "央视频道":

            return (
                item,
                True,
                status,
                "央视保留"
            )

        # ----------------------------------------------------
        # 非央视源无法识别内容则删除
        # ----------------------------------------------------

        return (
            item,
            False,
            status,
            "非直播数据"
        )

    except requests.RequestException:

        return (
            item,
            False,
            0,
            "连接失败"
        )

    except Exception:

        return (
            item,
            False,
            0,
            "检测异常"
        )


# ============================================================
# 并发检测
# ============================================================

def check_all_streams(streams):

    if not streams:

        return []

    print()
    print("=" * 70)
    print(
        f"开始检测直播源："
        f"{len(streams)} 条"
    )
    print(
        f"并发数量："
        f"{MAX_WORKERS}"
    )
    print("=" * 70)

    alive = []

    success = 0
    failed = 0

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    ) as executor:

        futures = [
            executor.submit(
                check_stream,
                item
            )
            for item in streams
        ]

        total = len(futures)

        for index, future in enumerate(
            concurrent.futures.as_completed(
                futures
            ),
            1
        ):

            (
                item,
                ok,
                status,
                reason,
            ) = future.result()

            if ok:

                success += 1

                alive.append(item)

                print(
                    f"[{index}/{total}] ✓ "
                    f"{item['program_name']} "
                    f"HTTP {status} "
                    f"[{reason}]"
                )

            else:

                failed += 1

                status_text = (
                    str(status)
                    if status
                    else "-"
                )

                print(
                    f"[{index}/{total}] × "
                    f"{item['program_name']} "
                    f"HTTP {status_text} "
                    f"[{reason}]"
                )

    print()
    print(
        f"检测完成："
        f"有效 {success} 条，"
        f"失效 {failed} 条"
    )

    return alive


# ============================================================
# 添加分类
# ============================================================

def organize_streams(streams):

    for item in streams:

        item["group"] = (
            get_channel_group(
                item["program_name"]
            )
        )

    return streams


# ============================================================
# 央视优先排序
#
# 让 M3U 中央视频道排在前面，
# 但不改变 group-title 分类。
# ============================================================

def sort_streams(streams):

    group_order = {
        "央视频道": 0,
        "卫视频道": 1,
        "少儿频道": 2,
        "地方频道": 3,
        "其他频道": 4,
    }

    return sorted(
        streams,
        key=lambda item: (
            group_order.get(
                item["group"],
                99
            ),
            item["program_name"],
            item["stream_url"],
        )
    )


# ============================================================
# 保存 iptv.txt
# ============================================================

def save_total_txt(streams):

    path = os.path.join(
        OUTPUT_DIR,
        "iptv.txt"
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        for item in streams:

            f.write(
                f"{item['program_name']},"
                f"{item['stream_url']}\n"
            )

    print(
        f"✓ 已生成：{path}"
    )


# ============================================================
# 保存 iptv.m3u
# ============================================================

def save_m3u(streams):

    path = os.path.join(
        OUTPUT_DIR,
        "iptv.m3u"
    )

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "#EXTM3U\n"
        )

        for item in streams:

            name = item[
                "program_name"
            ]

            group = item[
                "group"
            ]

            url = item[
                "stream_url"
            ]

            # 防止双引号破坏 M3U
            safe_name = (
                name.replace(
                    '"',
                    "'"
                )
            )

            safe_group = (
                group.replace(
                    '"',
                    "'"
                )
            )

            f.write(
                f'#EXTINF:-1 '
                f'tvg-name="{safe_name}" '
                f'group-title="{safe_group}",'
                f'{safe_name}\n'
            )

            f.write(
                f"{url}\n"
            )

    print(
        f"✓ 已生成：{path}"
    )


# ============================================================
# 统计
# ============================================================

def print_statistics(streams):

    groups = {}

    for item in streams:

        group = item[
            "group"
        ]

        groups[group] = (
            groups.get(
                group,
                0
            ) + 1
        )

    print()
    print("=" * 70)
    print("最终频道统计")
    print("=" * 70)

    for group in [
        "央视频道",
        "卫视频道",
        "少儿频道",
        "地方频道",
        "其他频道",
    ]:

        count = groups.get(
            group,
            0
        )

        if count:

            print(
                f"{group}: "
                f"{count}"
            )

    print(
        f"总计："
        f"{len(streams)} 条"
    )


# ============================================================
# 清理旧文件
# ============================================================

def remove_old_output():

    for filename in [
        "iptv.txt",
        "iptv.m3u",
    ]:

        path = os.path.join(
            OUTPUT_DIR,
            filename
        )

        if os.path.exists(path):

            os.remove(path)

            print(
                f"已删除旧文件："
                f"{path}"
            )


# ============================================================
# 主程序
# ============================================================

def main():

    print("=" * 70)
    print("IPTV 自动抓取 / 清洗 / 检测")
    print("=" * 70)

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    all_streams = []

    # ========================================================
    # 分别抓取每一个源
    # ========================================================

    for source_url in SOURCE_URLS:

        content = fetch_source(
            source_url
        )

        if not content:

            continue

        try:

            streams = parse_source(
                content
            )

            print(
                f"→ 本源解析："
                f"{len(streams)} 条"
            )

            all_streams.extend(
                streams
            )

        except Exception as e:

            print(
                f"× 解析失败："
                f"{e}"
            )

    # ========================================================
    # 原始数量
    # ========================================================

    print()
    print(
        f"原始解析数量："
        f"{len(all_streams)}"
    )

    if not all_streams:

        print(
            "❌ 没有获取到有效 IPTV 源"
        )

        return

    # ========================================================
    # 去重
    # ========================================================

    all_streams = (
        deduplicate_streams(
            all_streams
        )
    )

    print(
        f"频道 + URL 去重后："
        f"{len(all_streams)} 条"
    )

    # ========================================================
    # 检测
    # ========================================================

    if ENABLE_CHECK:

        all_streams = (
            check_all_streams(
                all_streams
            )
        )

    # ========================================================
    # 检测后没有源
    # ========================================================

    if not all_streams:

        print(
            "❌ 检测后没有有效 IPTV 源"
        )

        remove_old_output()

        return

    # ========================================================
    # 添加分类
    # ========================================================

    all_streams = (
        organize_streams(
            all_streams
        )
    )

    # ========================================================
    # 排序
    # ========================================================

    all_streams = (
        sort_streams(
            all_streams
        )
    )

    # ========================================================
    # 只生成两个文件
    # ========================================================

    save_total_txt(
        all_streams
    )

    save_m3u(
        all_streams
    )

    # ========================================================
    # 统计
    # ========================================================

    print_statistics(
        all_streams
    )

    print()
    print("=" * 70)
    print("✅ IPTV 整理完成")
    print("=" * 70)
    print(
        "输出："
        "output/iptv.txt"
        " + "
        "output/iptv.m3u"
    )
    print("=" * 70)


if __name__ == "__main__":

    main()
