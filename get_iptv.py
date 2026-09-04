import requests
import re
import os

# 源列表，顺序就是写入M3U的顺序：范明明 → iptv6 → iptv4
urls = [
    "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt"
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')

ban_words = [
    "广告", "购物", "测试", "垃圾", "备用源", "vip", "付费",
    "游戏", "棋牌", "成人", "解密", "高清备用", "直播源分享"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

old_output_files = [
    "iptv.txt",
    "iptv.m3u"
]

group_priority = {
    "央视频道": 0,
    "卫视频道": 1,
    "少儿频道": 2
}


def clean_old_files():
    print("\n🧹正在清理旧输出文件...")
    for fpath in old_output_files:
        if os.path.exists(fpath):
            try:
                os.remove(fpath)
                print(f"已删除旧文件: {fpath}")
            except Exception as e:
                print(f"删除文件 {fpath} 失败: {e}")
    print()


def get_cctv_sort_key(name: str):
    m = re.search(r"CCTV[-‑]?(\d+)", name.upper())
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            pass
    return 999


def get_channel_group(name: str):
    if not name:
        return None
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"
    name_upper = name.upper()
    if "CCTV" in name_upper or "央视" in name:
        return "央视频道"
    if "卫视" in name:
        return "卫视频道"
    return None


def clean_program_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'[★✨🔴💥🔥⚡]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'\s*(高清|超清|标清|HD|SD|4K|2K)$', '', name, flags=re.IGNORECASE)
    name = name.strip()
    return name


def is_bad_name(name: str) -> bool:
    name_low = name.lower()
    for w in ban_words:
        if w in name_low:
            return True
    return False


def fetch_streams_from_url(url, retries=2):
    print(f"\n正在抓取源: {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            print(f"第{attempt+1}次请求 {url} 状态码:{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"请求 {url} 异常: {e}")
    print(f"跳过来源: {url}")
    return None


def parse_m3u(content):
    streams = []
    current_program = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            if match:
                current_program = clean_program_name(match.group(1).strip())
        elif line.startswith("http"):
            if current_program and not is_bad_name(current_program):
                streams.append({"program_name": current_program, "stream_url": line})
            current_program = None
    return streams


def parse_txt(content):
    streams = []
    for line in content.splitlines():
        match = re.match(r"\s*(.+?),\s*(http.+)", line)
        if match:
            p_name = clean_program_name(match.group(1).strip())
            p_url = match.group(2).strip()
            if p_name and p_url.startswith("http") and not is_bad_name(p_name):
                streams.append({
                    "program_name": p_name,
                    "stream_url": p_url
                })
    return streams


def parse_single_source(content):
    """解析单个源内容，返回过滤后的流列表"""
    parser = parse_m3u if content.lstrip().startswith("#EXTM3U") else parse_txt
    raw = parser(content)
    valid = []
    for item in raw:
        name = item["program_name"]
        url = item["stream_url"]
        group = get_channel_group(name)
        if group is not None and url.startswith("http"):
            valid.append({"program_name": name, "stream_url": url, "group": group})
    return valid


def main():
    clean_old_files()
    all_items = []

    # 逐个抓取每个url，解析后直接收集，顺序保持：范明明 → iptv6 → iptv4
    for url in urls:
        text = fetch_streams_from_url(url)
        if not text:
            continue
        items = parse_single_source(text)
        print(f"本来源有效流数量：{len(items)}")
        all_items.extend(items)

    # 写入M3U
    with open("iptv.m3u", 'w', encoding='utf-8', newline='') as f:
        f.write("#EXTM3U\n")
        for item in all_items:
            prog = item["program_name"]
            grp = item["group"]
            url = item["stream_url"]
            f.write(f'#EXTINF:-1 tvg-name="{prog}" group-title="{grp}",{prog}\n{url}\n')

    # 同时输出iptv.txt
    ipv4 = []
    ipv6 = []
    for item in all_items:
        p = item["program_name"]
        u = item["stream_url"]
        if ipv4_pattern.match(u):
            ipv4.append(f"{p},{u}")
        elif ipv6_pattern.match(u):
            ipv6.append(f"{p},{u}")
        else:
            ipv4.append(f"{p},{u}")

    with open("iptv.txt", 'w', encoding='utf-8') as f:
        f.write("# IPv4 Streams\n")
        f.write("\n".join(ipv4))
        f.write("\n\n# IPv6 Streams\n")
        f.write("\n".join(ipv6))

    print(f"\n✅完成！总流数量：{len(all_items)}")
    print(f"m3u路径：{os.path.abspath('iptv.m3u')}")
    print(f"txt路径：{os.path.abspath('iptv.txt')}")


if __name__ == "__main__":
    main()
