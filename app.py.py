import csv
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="キクヤ堺本店 データ取得", layout="centered")

st.title("🎰 キクヤ堺本店 データ取得ツール")
st.write("みんレポから最新の差枚数・回転数データを自動収集します。")

BASE_URL = "https://min-repo.com"
TARGET_LIST_URL = "https://min-repo.com/tag/%E3%82%AD%E3%82%AF%E3%83%A4%E5%A0%BA%E6%9C%AC%E5%BA%97/"

# 本物のChromeブラウザと同等の通信ヘッダー情報
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://min-repo.com/",
    "Sec-Ch-Ua": (
        '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"'
    ),
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def get_soup(url):
  """Webページを取得して解析"""
  try:
    session = requests.Session()
    res = session.get(url, headers=HEADERS, timeout=15)
    res.encoding = res.apparent_encoding

    soup = BeautifulSoup(res.text, "html.parser")
    title = soup.find("title").text.strip() if soup.find("title") else "タイトルなし"

    # Cloudflareのアクセスブロック検知
    if "Just a moment..." in title or "Attention Required" in title:
      return (
          None,
          "CloudflareによるBotアクセス制限（セキュリティ認証）が発生しました。",
          title,
      )

    return soup, None, title
  except Exception as e:
    return None, f"通信エラー: {str(e)}", "エラー"


if st.button("🚀 データ取得を開始する"):
  status_text = st.empty()
  progress_bar = st.progress(0)

  status_text.info("レポート一覧を取得中...")
  soup, err_msg, page_title = get_soup(TARGET_LIST_URL)

  if err_msg:
    st.error(f"⚠️ {err_msg}")
    st.info(f"取得できたページタイトル: {page_title}")
    st.warning(
        "【対処法】クラウドサーバー（Streamlit Cloud）のIPアドレスがサイト側から制限されています。\n"
        "この制限を回避するには、パソコン上のローカル環境（Python/EXEアプリ）で実行するか、プロキシ経由でアクセスする必要があります。"
    )
  elif not soup:
    st.error("ページの読み込みに失敗しました。")
  else:
    report_links = []
    for a in soup.find_all("a", href=True):
      href = a["href"]
      full_url = urljoin(BASE_URL, href)
      clean_path = full_url.rstrip("/").split("/")[-1]

      if clean_path.isdigit() and full_url not in report_links:
        report_links.append(full_url)

    total = len(report_links)

    if total == 0:
      st.error("レポート記事のURLが見つかりませんでした。")
      st.info(f"アクセス成功ページタイトル: {page_title}")
    else:
      st.success(f"{total} 件のレポートを発見しました。データを順次取得します。")
      all_data = []

      for i, url in enumerate(report_links, 1):
        status_text.text(f"データ取得中... ({i}/{total} ページ)")
        progress_bar.progress(i / total)

        rep_soup, rep_err, _ = get_soup(url)
        if rep_soup:
          h1_tag = rep_soup.find("h1")
          title_text = h1_tag.text.strip() if h1_tag else "不明"

          for table in rep_soup.find_all("table"):
            for row in table.find_all("tr"):
              cols = [c.text.strip() for c in row.find_all(["td", "th"])]
              if len(cols) >= 4 and cols[0].isdigit():
                all_data.append({
                    "対象日・タイトル": title_text,
                    "台番号": cols[0],
                    "機種名": cols[1],
                    "差枚数": cols[2],
                    "回転数": cols[3],
                })
        time.sleep(1.5)

      status_text.success("データの取得が完了しました！")
      df = pd.DataFrame(all_data)

      st.subheader("📊 取得データ一覧")
      st.dataframe(df)

      csv_data = df.to_csv(index=False).encode("utf-8-sig")
      st.download_button(
          label="📥 CSVファイルをダウンロード",
          data=csv_data,
          file_name="kikuya_sakai_data.csv",
          mime="text/csv",
      )
