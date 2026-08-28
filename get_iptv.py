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
            p_url = match.group(2).strip()
            if p_name and p_url.startswith("http") and not is_bad_name(p_name):
                streams.append({
                    "program_name": p_name,
                    "stream_url": p_url
                })
    return streams

def organize_streams(content):
    parser = parse_m3u if content.startswith("#EXTM3U") else parse_txt
    raw = parser(content)
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    # 联合去重
    df = df.drop_duplicates(subset=['program_name', 'stream_url'], keep="first")
    df = df[df['program_name'].str.len() > 0]
    # 计算分组字段
    df['group'] = df['program_name'].apply(get_channel_group)
    return df

def save_to_total_txt(df, filename="iptv.txt"):
    """保存总txt文件，区分IPv4/IPv6"""
    ipv4 = []
    ipv6 = []
    for _, row in df.iterrows():
        program = row['program_name']
        url = row['stream_url']
        if ipv4_pattern.match(url):
            ipv4.append(f"{program},{url}")
        elif ipv6_pattern.match(url):
            ipv6.append(f"{program},{url}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# IPv4 Streams\n")
        f.write("\n".join(ipv4))
        f.write("\n\n# IPv6 Streams\n")
        f.write("\n".join(ipv6))
    print(f"总文本文件已保存: {os.path.abspath(filename)}")

def save_split_txt(df):
    """按分组输出独立txt文件，每个文件内部分IPv4/IPv6"""
    group_list = ["央视频道", "卫视频道", "少儿频道", "地方频道", "其他频道"]
    for g_name in group_list:
        sub_df = df[df["group"] == g_name]
        if sub_df.empty:
            continue
        ipv4 = []
        ipv6 = []
        for _, row in sub_df.iterrows():
            line = f"{row['program_name']},{row['stream_url']}"
            if ipv4_pattern.match(row['stream_url']):
                ipv4.append(line)
            elif ipv6_pattern.match(row['stream_url']):
                ipv6.append(line)
        filename = f"{g_name}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# IPv4\n")
            f.write("\n".join(ipv4))
            f.write("\n\n# IPv6\n")
            f.write("\n".join(ipv6))
        print(f"分类文件已保存: {os.path.abspath(filename)}")

def save_to_m3u(df, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for _, row in df.iterrows():
            program = row['program_name']
            group = row['group']
            url = row['stream_url']
            f.write(f'#EXTINF:-1 tvg-name="{program}" group-title="{group}",{program}\n{url}\n')
    print(f"M3U文件已保存: {os.path.abspath(filename)}")

if __name__ == "__main__":
    print("开始抓取所有源...")
    content = fetch_all_streams()
    if content:
        print("整理源数据中...")
        df_result = organize_streams(content)
        if not df_result.empty:
            save_to_total_txt(df_result)
            save_split_txt(df_result)
            save_to_m3u(df_result)
            print(f"\n✅全部完成！共 {len(df_result)} 条直播流")
        else:
            print("❌没有解析到有效节目")
    else:
        print("❌未能获取有效数据")
