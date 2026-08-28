import requests
import pandas as pd
import re
import os

# 原有源 + 新增持续更新源 + 咪咕专用源
urls = [
    "https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
    "https://raw.githubusercontent.com/YueChan/Live/refs/heads/main/APTV.m3u",
    "https://raw.githubusercontent.com/Kimentanm/aptv/master/m3u/iptv.m3u",
    "https://raw.githubusercontent.com/BurningC4/Chinese-IPTV/master/TV-IPV4.m3u",
    "https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/IPV6.m3u",
    "https://raw.githubusercontent.com/yuanzl77/IPTV/main/live.m3u",
    "https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv6.m3u",
    "https://raw.githubusercontent.com/best-fan/iptv-sources/main/cn_all.m3u8",
    "https://iptv-org.github.io/iptv/countries/cn.m3u",
    # 咪咕独立更新源
    "https://raw.githubusercontent.com/YanG-1989/m3u/main/Migu.m3u"
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')

# 广告/垃圾关键词过滤
ban_words = [
    "广告", "购物", "测试", "垃圾", "备用源", "vip", "付费",
    "游戏", "棋牌", "成人", "解密", "高清备用", "直播源分享"
]

def get_channel_group(name: str) -> str:
    """分组规则：咪咕优先，再少儿、央视、卫视、地方、其他"""
    if not name:
        return "其他频道"

    # 咪咕直播分组 优先匹配
    if "咪咕" in name:
        return "咪咕直播"

    # 少儿频道
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"

    # 央视频道
    if re.match(r'^CCTV[-‑]?\d+', name.upper()) or "央视" in name:
        return "央视频道"

    # 卫视频道
    if "卫视" in name:
        return "卫视频道"

    # 地方频道
    return "地方频道"

def clean_program_name(name: str) -> str:
    """清洗节目名称：去除特殊符号、多余空格"""
    if not name:
        return ""
    name = re.sub(r'[★✨🔴💥●◆■]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def fetch_m3u(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"获取失败 {url}: {e}")
        return ""

def parse_m3u(content):
    channels = []
    lines = content.splitlines()
    name = ""
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            match = re.search(r',(.+)$', line)
            if match:
                name = clean_program_name(match.group(1))
        elif line.startswith("http") and name:
            # 过滤违禁关键词
            if any(b in name for b in ban_words):
                name = ""
                continue
            group = get_channel_group(name)
            channels.append({
                "name": name,
                "url": line,
                "group": group
            })
            name = ""
    return channels

def main():
    all_channels = []
    for u in urls:
        print(f"正在处理: {u}")
        txt = fetch_m3u(u)
        chs = parse_m3u(txt)
        all_channels.extend(chs)
    # 名称+链接双重去重
    df = pd.DataFrame(all_channels)
    df = df.drop_duplicates(subset=["name", "url"])
    # 按分组排序输出m3u
    output = "#EXTM3U\n"
    for _, row in df.iterrows():
        output += f'#EXTINF:-1 group-title="{row["group"]}",{row["name"]}\n{row["url"]}\n'
    with open("merged_iptv.m3u", "w", encoding="utf-8") as f:
        f.write(output)
    print("合并完成，已保存为 merged_iptv.m3u，咪咕频道已单独分组")

if __name__ == "__main__":
    main()
