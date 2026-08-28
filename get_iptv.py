import requests
import pandas as pd
import re
import os
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# 源地址列表
urls = [
    "https://raw.githubusercontent.com/zwc456baby/iptv_alive/master/live.txt",
    "https://live.zbds.top/tv/iptv6.txt",
    "https://live.zbds.top/tv/iptv4.txt",
    "http://www.52top.com.cn:678/downloads/migu.txt"
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


def get_channel_group(name: str) -> str:
    """
    咪咕源分组优化，优先级从上到下
    4K超高清 > 体育频道 > 影视频道 > 少儿频道 > 央视频道 > 卫视频道 > 咪咕特色 > 地方频道 > 其他频道
    """
    if not name:
        return "其他频道"
    name_upper = name.upper()

    # 1.4K超高清
    if re.search(r"4K|超高清", name_upper):
        return "4K超高清"

    # 2.体育频道
    sport_key = ["体育", "赛事", "足球", "篮球", "竞技", "台球", "乒羽", "咪咕赛事", "睛彩竞技", "睛彩篮球"]
    for k in sport_key:
        if k in name:
            return "体育频道"

    # 3.影视频道
    movie_key = ["电影", "剧场", "院线", "剧集", "影视", "iHOT"]
    for k in movie_key:
        if k in name:
            return "影视频道"

    # 4.少儿频道
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"

    # 5.央视频道
    if re.match(r'^CCTV[-‑]?\d+', name_upper) or "央视" in name:
        return "央视频道"

    # 6.卫视频道
    if "卫视" in name:
        return "卫视频道"

    # 7.咪咕特色（咪咕直播、睛彩系列自有频道）
    migu_key = ["咪咕直播", "咪咕", "睛彩"]
    for k in migu_key:
        if k in name:
            return "咪咕特色"

    # 8.地方台
    return "地方频道"


def clean_program_name(name: str) -> str:
    if not name:
        return ""
    name = re.sub(r'[★✨🔴💥🔥⚡]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'((高清)|(超清)|(标清)|(HD)|(SD)|(2K)|‑\d+)$', '', name, flags=re.IGNORECASE)
    name = name.strip()
    return name


def is_bad_name(name: str) -> bool:
    name_low = name.lower()
    for w in ban_words:
        if w in name_low:
            return True
    return False


def fetch_streams_from_url(url, retries=2):
    print(f"正在爬取网站源: {url}")
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=12, headers=HEADERS, verify=False)
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
            if p_name and p_url.startswith("http") and len(p_url) > 10 and not is_bad_name(p_name):
                streams.append({
                    "program_name": p_name,
                    "stream_url": p_url
                })
    return streams


def organize_streams(content):
    if content.lstrip().startswith("#EXTM3U"):
        parser = parse_m3u
    else:
        parser = parse_txt
    raw = parser(content)
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    df = df.drop_duplicates(subset=['program_name', 'stream_url'], keep="first")
    df = df[df['program_name'].str.len() > 0]
    df['group'] = df['program_name'].apply(get_channel_group)
    return df


def save_to_total_txt(df, filename="iptv.txt"):
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
        f.write("# IPv6 Streams\n")
        f.write("\n".join(ipv6))
    print(f"总文本文件已保存: {os.path.abspath(filename)}")


def save_split_txt(df):
    group_list = ["4K超高清", "体育频道", "影视频道", "央视频道", "卫视频道", "少儿频道", "咪咕特色", "地方频道", "其他频道"]
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
    print("开始抓取所有源(含咪咕)...")
    content = fetch_all_streams()
    if content:
        print("整理源数据中...")
        df_result = organize_streams(content)
        if not df_result.empty:
            save_to_total_txt(df_result)
            save_split_txt(df_result)
            save_to_m3u(df_result)
            print(f"\n✅全部完成！共 {len(df_result)} 条直播流")
            print("\n📊分组统计：")
            print(df_result["group"].value_counts().to_string())
        else:
            print("❌没有解析到有效节目")
    else:
        print("❌未能获取有效数据")
