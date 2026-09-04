import requests
import pandas as pd
import re
import os

# ====================== 【自定义配置区，在这里修改】 ======================
# 优先频道顺序：支持完整名称或者关键词模糊匹配，越靠前输出越优先
PRIORITY_CHANNELS = [
    "CCTV‑1",
    "CCTV‑2",
    "CCTV‑3",
    "CCTV‑4",
    "CCTV‑5",
    "CCTV‑6",
    "CCTV‑7",
    "CCTV‑8",
    "CCTV‑9",
    "CCTV‑10",
    "CCTV‑11",
    "CCTV‑12",
    "CCTV‑13",
    "CCTV‑14",
    "CCTV‑15",
    "湖南卫视",
    "浙江卫视",
    "江苏卫视",
    "东方卫视",
    "广东卫视"
]

# 抓取源列表：【范明明源放在第一位，优先抓取】
urls = [
    "https://raw.githubusercontent.com/farmingming/live/main/tv/m3u/iov6.m3u",
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
]
# ========================================================================

pd.options.mode.chained_assignment = None

ipv4_pattern = re.compile(r'^http://(\d{1,3}\.){3}\d{1,3}')
ipv6_pattern = re.compile(r'^http://\[([a-fA-F0-9:]+)\]')
clean_char_pattern = re.compile(r'[^\x00-\x7E\u4e00-\u9fff]')

def clean_text(text: str) -> str:
    """清理文本中隐形特殊Unicode字符，修复\u2011报错"""
    return clean_char_pattern.sub('', text)

def natural_sort_str(s):
    """返回字符串版本自然排序key，不再返回list，解决不可哈希list报错"""
    parts = re.split(r'(\d+)', s)
    key_parts = []
    for p in parts:
        if p.isdigit():
            key_parts.append(f"{int(p):06d}")
        else:
            key_parts.append(p.lower())
    return "|".join(key_parts)

def get_priority_score(channel_name):
    """计算频道优先级分数，越小越靠前；模糊匹配PRIORITY_CHANNELS"""
    for idx, keyword in enumerate(PRIORITY_CHANNELS):
        if keyword in channel_name:
            return idx
    # 不在优先列表，放到后面
    return 9999

def fetch_streams_from_url(url):
    print(f"正在爬取网站源: {url}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            raw = response.text
            return clean_text(raw)
        print(f"从 {url} 获取数据失败，状态码: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"请求 {url} 时发生错误: {e}")
    return None

def fetch_all_streams():
    all_streams = []
    for url in urls:
        content = fetch_streams_from_url(url)
        if content and len(content.strip()) > 10:
            all_streams.append(content.strip())
        else:
            print(f"跳过来源: {url}")
    return "\n".join(all_streams)

def parse_content(content):
    """兼容混合 M3U + TXT 混合内容，逐行解析"""
    streams = []
    current_program = None

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            match = re.search(r'tvg-name="([^"]+)"', line)
            if match:
                current_program = match.group(1).strip()
            continue
        if ',' in line and not line.startswith(('http', 'https')):
            match = re.match(r"(.+?),\s*(http.+)", line)
            if match:
                p_name = match.group(1).strip()
                p_url = match.group(2).strip()
                if p_name and p_url:
                    streams.append({"program_name": p_name, "stream_url": p_url})
            continue
        if line.startswith(("http://", "https://")):
            if current_program:
                streams.append({"program_name": current_program, "stream_url": line})
                current_program = None
    return streams


def organize_streams(content):
    raw_list = parse_content(content)
    if not raw_list:
        print("警告：没有解析到任何频道数据！")
        return pd.DataFrame(columns=["program_name", "stream_url"])

    df = pd.DataFrame(raw_list)
    df = df[(df["program_name"] != "") & (df["stream_url"] != "")]
    df = df.drop_duplicates(subset=['program_name', 'stream_url'])
    print(f"去重后总频道链接数: {len(df)}")

    # 分组
    grouped = df.groupby('program_name')['stream_url'].apply(list).reset_index()

    # ====== 修复：全部使用字符串key，不存入list，解决TypeError:不可哈希类型:"list" ======
    grouped['priority'] = grouped['program_name'].apply(get_priority_score)
    grouped['sort_key'] = grouped['program_name'].apply(natural_sort_str)
    grouped = grouped.sort_values(by=["priority", "sort_key"], ascending=[True, True])
    grouped = grouped.drop(columns=["priority", "sort_key"]).reset_index(drop=True)
    print(f"✅完成自定义频道排序")
    return grouped


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
    print(f"✅文本文件已保存: {os.path.abspath(filename)}")
    print(f"  IPv4频道数量: {len(ipv4)}")
    print(f"  IPv6频道数量: {len(ipv6)}")


def save_to_m3u(grouped_streams, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U\n")
        for _, row in grouped_streams.iterrows():
            program = row['program_name']
            for url in row['stream_url']:
                f.write(f'#EXTINF:-1 tvg-name="{program}",{program}\n{url}\n')
    print(f"✅M3U文件已保存: {os.path.abspath(filename)}")


if __name__ == "__main__":
    print("===== IPTV源抓取开始 =====")
    full_content = fetch_all_streams()
    if full_content and len(full_content.strip()) > 20:
        print("整理源数据中...")
        organized_df = organize_streams(full_content)
        if len(organized_df) >0:
            save_to_txt(organized_df)
            save_to_m3u(organized_df)
        else:
            print("解析后无频道数据，输出文件跳过")
    else:
        print("❌未能获取有效数据，全部源抓取失败")
