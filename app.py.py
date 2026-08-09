import csv
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import cloudscraper
import pandas as pd
import streamlit as st

st.set_page_config(page_title="キクヤ堺本店 データ取得", layout="centered")

st.title("🎰 キクヤ堺本店 データ取得ツール")
st.write("みんレポから最新の差枚数・回転数データを自動収集します。")

BASE_URL = "https://min-repo.com"
# 「キクヤ堺本店」の正しいURL（エンコード版）
TARGET_LIST_URL = "https://min-repo.com/tag/%E3%82%AD%E3%82%AF%E3%83%A4%E5%A0%BA%E6%9C%AC%E5%BA%97/"


def get_soup(url):
  """cloudscraperを使用してHTMLを取得"""
  try:
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "desktop": True}
    )
    res = scraper.get(url, timeout=15)
    if res.status_code == 200:
      res.encoding = res.apparent_encoding
      return BeautifulSoup(res.text, "html.parser"), None
    else:
      return (
          None,
          (
              f"HTTPエラー {res.status_code}:"
              " サイトからアクセスが制限されている可能性があります。"
          ),
      )
  except Exception as e:
    return None, f"通信エラー: {str(e)}"


if st.button("🚀 データ取得を開始する"):
  status_text = st.empty()
  progress_bar = st.progress(0)

  status_text.info("レポート一覧を取得中...")
  soup, err_msg = get_soup(TARGET_LIST_URL)

  if err_msg:
    st.error(f"接続エラー:\n{err_msg}")
  elif not soup:
    st.error("ページの読み込みに失敗しました。")
  else:
    report_links = []
    for a in soup.find_all("a", href=True):
      href = a["href"]
      # 絶対パスに変換
      full_url = urljoin(BASE_URL, href)

      # 末尾が数字（記事ID）のURLを判定
      clean_path = full_url.rstrip("/").split("/")[-1]
      if clean_path.isdigit():
        if full_url not in report_links:
          report_links.append(full_url)

    total = len(report_links)

    if total == 0:
      st.error(
          "記事リンクが見つかりませんでした。"
          " 該当のタグページにレポートが存在しないか、URLの構造が異なっています。"
      )
      # デバッグ用：取得したタイトルの表示
      page_title = (
          soup.find("title").text.strip() if soup.find("title") else "タイトルなし"
      )
      st.info(f"アクセス先ページタイトル: {page_title}")
    else:
      st.success(f"{total} 件のレポートページを発見しました。順次データを取得します。")
      all_data = []

      for i, url in enumerate(report_links, 1):
        status_text.text(f"データ取得中... ({i}/{total} ページ)")
        progress_bar.progress(i / total)

        rep_soup, _ = get_soup(url)
        if rep_soup:
          title = (
              rep_soup.find("h1").text.strip()
              if rep_soup.find("h1")
              else "不明"
          )
          for table in rep_soup.find_all("table"):
            for row in table.find_all("tr"):
              cols = [c.text.strip() for c in row.find_all(["td", "th"])]
              if len(cols) >= 4 and cols[0].isdigit():
                all_data.append({
                    "対象日・タイトル": title,
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
