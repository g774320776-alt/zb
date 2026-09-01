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

# 输出目录
OUTPUT_DIR = "output"

# 获取源列表超时时间
FETCH_TIMEOUT = 20

# 检测单个直播源超时时间
CHECK_TIMEOUT = 8

# 并发检测数量
MAX_WORKERS = 30

# 获取源失败后的重试次数
RETRIES = 2

# 是否检测每一个直播地址
ENABLE_CHECK = True

# True：只保留最终 HTTP 200
# False：允许 2xx / 3xx
ONLY_STATUS_200 = True

# User-Agent
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 13) "
    "AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "*/*",
    "Connection": "keep-alive",
}

# 关闭 SSL 警告
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
# 频道分类
#
# 保持原来的四种分类：
# 央视频道
# 卫视频道
# 少儿频道
# 地方频道
# ============================================================

CCTV_PATTERN = re.compile(
    r"^CCTV[--－]?\s*\d{1,2}([+＋]?)$",
    re.IGNORECASE
)

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

SATELLITE_KEYWORDS = [
    "卫视",
]

CCTV_KEYWORDS = [
    "央视",
    "CCTV",
]


# ============================================================
# URL 判断
# ============================================================

def is_valid_url(url: str) -> bool:
    """判断 URL 是否为有效 HTTP/HTTPS 地址"""

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
# 清洗频道名称
# ============================================================

def clean_program_name(name: str) -> str:
    """清洗频道名称"""

    if not name:
        return ""

    name = name.strip()

    # 去掉常见图标
    name = re.sub(
        r"[★☆✨🔴💥🔥⚡️⭐️📺🎬]",
        "",
        name
    )

    # 去掉 HTML 标签
    name = re.sub(
        r"<[^>]+>",
        "",
        name
    )

    # 全角逗号统一
    name = name.replace("，", ",")

    # 多余空格
    name = re.sub(
        r"\s+",
        " ",
        name
    )

    # 去掉常见画质后缀
    name = re.sub(
        r"[\s_\--–—]*(高清|超清|标清|HD|SD|FHD|UHD|4K|2K)$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    # 去掉备用 / 线路 / 数字后缀
    name = re.sub(
        r"[\s_\--–—]+(?:备用|备份|线路\d+|\d+)$",
        "",
        name,
        flags=re.IGNORECASE,
    )

    return name.strip(" ,，|")


# ============================================================
# 垃圾名称判断
# ============================================================

def is_bad_name(name: str) -> bool:
    """判断是否属于广告/垃圾频道"""

    if not name:
        return True

    name_low = name.lower()

    for word in BAN_WORDS:
        if word.lower() in name_low:
            return True

    return False


# ============================================================
# 频道分类
# ============================================================

def get_channel_group(name: str) -> str:
    """
    保持原始代码分类逻辑：

    少儿频道
    央视频道
    卫视频道
    地方频道
    """

    if not name:
        return "其他频道"

    # --------------------------------------------------------
    # 少儿频道优先
    # --------------------------------------------------------

    for keyword in KID_KEYWORDS:
        if keyword in name:
            return "少儿频道"

    # --------------------------------------------------------
    # 央视频道
    # --------------------------------------------------------

    if CCTV_PATTERN.match(name):
        return "央视频道"

    if "央视" in name:
        return "央视频道"

    if "CCTV" in name.upper():
        return "央视频道"

    # --------------------------------------------------------
    # 卫视频道
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
    """下载 IPTV 源列表"""

    print(f"\n正在获取源：{url}")

    for attempt in range(1, RETRIES + 2):

        try:

            response = requests.get(
                url,
                headers=HEADERS,
                timeout=FETCH_TIMEOUT,
                verify=False,
                allow_redirects=True,
            )

            if response.status_code == 200:

                # 自动识别编码
                if response.encoding is None:
                    response.encoding = (
                        response.apparent_encoding
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

    print(f"× 放弃源：{url}")

    return None


# ============================================================
# TXT 解析
# ============================================================

def parse_txt(content: str):
    """
    支持：

    CCTV1,http://xxx
    CCTV2,https://xxx
    """

    streams = []

    for raw_line in content.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # 忽略注释
        if line.startswith("#"):
            continue

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
    """兼容标准 M3U / EXTINF"""

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

            # 优先读取 tvg-name
            match = re.search(
                r'tvg-name\s*=\s*"([^"]+)"',
                line,
                flags=re.IGNORECASE,
            )

            if match:

                current_name = (
                    match.group(1).strip()
                )

            # 没有 tvg-name 时，读取逗号后的名称
            elif "," in line:

                current_name = (
                    line.rsplit(",", 1)[1].strip()
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

    # 标准 M3U
    if stripped.upper().startswith("#EXTM3U"):
        return parse_m3u(content)

    # 没有 EXT M3U 头但存在 EXTINF
    if "#EXTINF" in content.upper():
        return parse_m3u(content)

    # 默认 TXT
    return parse_txt(content)


# ============================================================
# URL 规范化
# ============================================================

def normalize_url(url: str) -> str:

    return url.strip().rstrip()


# ============================================================
# 去重
# ============================================================

def deduplicate_streams(streams):
    """
    同时进行：

    1. 频道名 + URL 去重
    2. URL 去重
    """

    result = []

    seen = set()
    seen_url = set()

    for item in streams:

        name = item["program_name"]
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

        # 同一 URL 只保留一次
        if url.lower() in seen_url:
            continue

        seen_url.add(
            url.lower()
        )

        result.append({
            "program_name": name,
            "stream_url": url,
        })

    return result


# ============================================================
# 检测单个直播源
# ============================================================

def check_stream(item):

    try:

        response = requests.get(
            item["stream_url"],
            headers=HEADERS,
            timeout=CHECK_TIMEOUT,
            verify=False,
            allow_redirects=True,
            stream=True,
        )

        status = response.status_code

        response.close()

        # 严格模式
        if ONLY_STATUS_200:

            if status == 200:
                return item, True, status

            return item, False, status

        # 宽松模式
        if 200 <= status < 400:
            return item, True, status

        return item, False, status

    except requests.RequestException:

        return item, False, 0

    except Exception:

        return item, False, 0


# ============================================================
# 并发检测
# ============================================================

def check_all_streams(streams):

    if not streams:
        return []

    print()
    print("=" * 60)
    print(
        f"开始检测直播源：{len(streams)} 条"
    )
    print(
        f"并发数量：{MAX_WORKERS}"
    )
    print("=" * 60)

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

            item, ok, status = (
                future.result()
            )

            if ok:

                success += 1

                alive.append(item)

                print(
                    f"[{index}/{total}] ✓ "
                    f"{item['program_name']} "
                    f"HTTP {status}"
                )

            else:

                failed += 1

                status_text = (
                    str(status)
                    if status
                    else "连接失败"
                )

                print(
                    f"[{index}/{total}] × "
                    f"{item['program_name']} "
                    f"HTTP {status_text}"
                )

    print()
    print(
        f"检测完成：有效 {success} 条，"
        f"失效 {failed} 条"
    )

    return alive


# ============================================================
# 添加分类字段
# ============================================================

def organize_streams(streams):

    for item in streams:

        item["group"] = get_channel_group(
            item["program_name"]
        )

    return streams


# ============================================================
# 保存 IPTV TXT
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

    print(f"✓ 已生成：{path}")


# ============================================================
# 保存 IPTV M3U
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

        f.write("#EXTM3U\n")

        for item in streams:

            name = item["program_name"]
            group = item["group"]
            url = item["stream_url"]

            # 防止双引号破坏 M3U
            safe_name = name.replace(
                '"',
                "'"
            )

            safe_group = group.replace(
                '"',
                "'"
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

    print(f"✓ 已生成：{path}")


# ============================================================
# 统计
# ============================================================

def print_statistics(streams):

    groups = {}

    for item in streams:

        group = item["group"]

        groups[group] = (
            groups.get(group, 0) + 1
        )

    print()
    print("=" * 60)
    print("频道统计")
    print("=" * 60)

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
                f"{group}: {count}"
            )

    print(
        f"总计：{len(streams)} 条"
    )


# ============================================================
# 主程序
# ============================================================

def main():

    print("=" * 60)
    print("IPTV 自动抓取 / 清洗 / 检测程序")
    print("=" * 60)

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    all_streams = []

    # --------------------------------------------------------
    # 分别获取并解析源
    # --------------------------------------------------------

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
                f"→ 本源解析得到："
                f"{len(streams)} 条"
            )

            all_streams.extend(
                streams
            )

        except Exception as e:

            print(
                f"× 解析失败：{e}"
            )

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

    # --------------------------------------------------------
    # 去重
    # --------------------------------------------------------

    all_streams = deduplicate_streams(
        all_streams
    )

    print(
        f"去重后："
        f"{len(all_streams)} 条"
    )

    # --------------------------------------------------------
    # HTTP 检测
    # --------------------------------------------------------

    if ENABLE_CHECK:

        all_streams = check_all_streams(
            all_streams
        )

    # --------------------------------------------------------
    # 检测后为空
    # --------------------------------------------------------

    if not all_streams:

        print(
            "❌ 检测后没有有效直播源"
        )

        # 清理旧输出，避免 GitHub 仓库
        # 继续保留上一次的失效数据
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

        return

    # --------------------------------------------------------
    # 分类
    # --------------------------------------------------------

    all_streams = organize_streams(
        all_streams
    )

    # --------------------------------------------------------
    # 只生成两个文件
    # --------------------------------------------------------

    save_total_txt(
        all_streams
    )

    save_m3u(
        all_streams
    )

    # --------------------------------------------------------
    # 统计
    # --------------------------------------------------------

    print_statistics(
        all_streams
    )

    print()
    print("=" * 60)
    print("✅ 全部完成")
    print(
        "输出文件："
        "output/iptv.txt"
        "、"
        "output/iptv.m3u"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
