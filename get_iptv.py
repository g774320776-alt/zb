import requests
import pandas as pd
import re
import os

# 源地址列表
urls = [
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')

# 广告/垃圾关键词过滤
ban_words = [
    "广告", "购物", "测试", "垃圾", "备用源", "vip", "付费",
    "游戏", "棋牌", "成人", "解密", "高清备用", "直播源分享"
]

def get_channel_group(name: str) -> str:
    """根据频道名判断分组，新增少儿频道"""
    name_upper = name.upper()
    name_low = name.lower()

    # 少儿频道优先匹配
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"

    # 央视频道
    if re.match(r'^CCTV[-‑]?\d+', name_upper) or "央视" in name:
        return "央视频道"

    # 卫视频道
    if "卫视" in name:
        return "卫视频道"

    # 地方台
    return "地方频道"

def clean_program_name(name: str) -> str:
    """清洗节目名称：去除多余符号、空格、后缀"""
    if not name:
        return ""
    name = re.sub(r'[★✨🔴💥🔥⚡]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'((高清)|(超清)|(标清)|(HD)|(SD)|(4K)|(2K)|‑\d+)$', '', name)
    name = name.strip()
    return name

def is_bad_name(name: str) -> bool:
    """判断是否垃圾节目"""
    name_low = name.lower()
    for w in ban_words:
        if w in name_low:
            return True
    return False

def fetch_streams_from_url(url, retries=2):
    print(f"正在爬取网站源: {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=12)
            response.encoding = 'utf-8'
            if response.status_code == 200:
                return response.text
            print(f"第{attempt+1}次请求 {url} 状态码:{response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"请求 {url} 异常: {e}")
    print(f"跳过来源: {url}")
    return None

def fetch_all_streams():
    all_streams = []
    for url in urls:
        content = fetch_streams_from_url(url)
        if content:
            all_streams.append(content)
    return "\n".join(all_streams)

def parse_m3u(content):
    streams = []
    current_program = None
    for line in content.splitlines():
        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            if match:
                current_program = clean_program_name(match.group(1).strip())
        elif line.startswith("http"):
            if current_program and not is_bad_name(current_program):
                streams.append({"program_name": current_program, "stream_url": line.strip()})
                current_program = None
    return streams

def parse_txt(content):
    streams = []
    for line in content.splitlines():
        match = re.match(r"(.+?),\s*(http.+)", line)
        if match:
            p_name = clean_program_name(match.group(1).strip())
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
    df = df.drop_duplicates(subset=['program_name', 'stream_url'], keep="first")
    df = df[df['program_name'].str.len() > 0]
    return df.groupby('program_name')['stream_url'].apply(list).reset_index()

def save_to_txt(grouped_streams, filename="iptv.txt"):
    ipv4 = []
    ipv6 = []
    for _, row in grouped_streams.iterrows():
        program = row['program_name']
        for url in row['stream_url']:
            if ipv4_pattern.match(url):
                ipv4.append(f"{program},{url}")
            elif ipv6_pattern.match(url):
                ipv6.append(f"{program},{url}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# IPv4 Streams\n")
        f.write("\n".join(ipv4))
        f.write("\n\n# IPv6 Streams\n")
        f.write("\n".join(ipv6))
    print(f"文本文件已保存: {os.path.abspath(filename)}")

def save_to_m3u(grouped_streams, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for _, row in grouped_streams.iterrows():
            program = row['program_name']
            group = get_channel_group(program)
            for url in row['stream_url']:
                f.write(f'#EXTINF:-1 tvg-name="{program}" tvg-group="{group}",{program}\n{url}\n')
    print(f"M3U文件已保存: {os.path.abspath(filename)}")

if __name__ == "__main__":
    print("开始抓取所有源...")
    content = fetch_all_streams()
    if content:
        print("整理源数据中...")
        organized = organize_streams(content)
        if not organized.empty:
            save_to_txt(organized)
            save_to_m3u(organized)
            print(f"✅完成！共处理 {len(organized)} 个节目")
        else:
            print("❌没有解析到有效节目")
    else:
        print("❌未能获取有效数据")
