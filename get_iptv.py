import requests
import pandas as pd
import re
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    "少儿频道": 2,
    "地方频道": 3,
    "其他频道": 4
}

# =====================可调参数（Github Action适配）=====================
MAX_SOURCE_PER_CHANNEL = 3   # 每个频道最多保留3个源
SPEED_TEST_TIMEOUT = 4       # 测速超时，github网络差调大到4秒
MAX_WORKERS = 10             # 并发线程，github不要超过10，太高会大量超时
USE_HEAD_TEST = True         # 使用HEAD请求测速，速度更快
# ======================================================================


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
        return int(m.group(1))
    return 999


def get_channel_group(name: str) -> str:
    if not name:
        return "其他频道"
    kid_keywords = ["少儿", "动画", "卡通", "金鹰卡通", "卡酷少儿", "优漫卡通"]
    for k in kid_keywords:
        if k in name:
            return "少儿频道"
    name_upper = name.upper()
    if "CCTV" in name_upper or "央视" in name:
        return "央视频道"
    if "卫视" in name:
        return "卫视频道"
    return "地方频道"


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
    print(f"正在爬取网站源: {url}")
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
                streams.append({"program_name": p_name, "stream_url": p_url})
    return streams


def test_single_url(url):
    start = time.perf_counter()
    try:
        if USE_HEAD_TEST:
            resp = requests.head(url, headers=HEADERS, timeout=SPEED_TEST_TIMEOUT, allow_redirects=True)
        else:
            resp = requests.get(url, headers=HEADERS, timeout=SPEED_TEST_TIMEOUT, stream=True)
        resp.close()
        cost_ms = round((time.perf_counter() - start) * 1000, 0)
        return url, cost_ms, True
    except Exception:
        return url, 9999, False


def speed_test_df(df):
    print(f"\n🚀开始测速，共 {len(df)} 个链接，并发:{MAX_WORKERS}...")
    url_list = df["stream_url"].tolist()
    speed_map = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(test_single_url, u): u for u in url_list}
        for fut in as_completed(future_to_url):
            u, cost, alive = fut.result()
            speed_map[u] = {"cost_ms": cost, "alive": alive}

    df["cost_ms"] = df["stream_url"].apply(lambda x: speed_map[x]["cost_ms"])
    df["alive"] = df["stream_url"].apply(lambda x: speed_map[x]["alive"])

    alive_cnt = df["alive"].sum()
    print(f"✅测速完成：存活 {alive_cnt} / {len(df)}")
    df = df[df["alive"]].copy()
    return df


def organize_streams(content):
    parser = parse_m3u if content.lstrip().startswith("#EXTM3U") else parse_txt
    raw = parser(content)
    df = pd.DataFrame(raw)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=['program_name', 'stream_url'], keep="first")
    df = df[df['program_name'].str.len() > 0]
    df = df[df['stream_url'].str.len() > 0]
    df['group'] = df['program_name'].apply(get_channel_group)
    df["group_sort"] = df["group"].map(group_priority)
    df["cctv_num_sort"] = df["program_name"].apply(get_cctv_sort_key)
    df = df.sort_values(by=["group_sort", "cctv_num_sort", "program_name"], ascending=[True, True, True])
    df = df.reset_index(drop=True)

    df = speed_test_df(df)
    if df.empty:
        return df

    out_rows = []
    # 循环分组，彻底规避pandas低版本groupby.apply丢列bug
    for _, group in df.groupby("program_name"):
        group_sorted = group.sort_values("cost_ms", ascending=True)
        take = group_sorted.head(MAX_SOURCE_PER_CHANNEL)
        out_rows.extend(take.to_dict("records"))

    df = pd.DataFrame(out_rows)
    if df.empty:
        return df

    df = df.sort_values(by=["group_sort", "cctv_num_sort", "program_name"], ascending=[True, True, True])
    cctv_df = df[df['group'] == "央视频道"]
    print(f"\n🔍解析到央视频道数量：{len(cctv_df)}")
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
        f.write("\n".join(ipv6))
    print(f"总文本文件已保存: {os.path.abspath(filename)}")


def save_to_m3u(df, filename="iptv.m3u"):
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        f.write("#EXTM3U\n")
        for _, row in df.iterrows():
            program = row['program_name']
            group = row['group']
            url = row['stream_url']
            f.write(f'#EXTINF:-1 tvg-name="{program}" group-title="{group}",{program}\n{url}\n')
    print(f"M3U文件已保存: {os.path.abspath(filename)}")


if __name__ == "__main__":
    clean_old_files()
    print("开始抓取所有源...")
    content = fetch_all_streams()
    if content:
        print("整理源数据中...")
        df_result = organize_streams(content)
        if not df_result.empty:
            save_to_total_txt(df_result)
            save_to_m3u(df_result)
            print(f"\n✅全部完成！共 {len(df_result)} 条直播流")
        else:
            print("❌测速后没有存活有效节目")
    else:
        print("❌未能获取有效数据")
