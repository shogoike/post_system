"""
レースデータ自動取得・JSONbin.ioアップロードスクリプト
Windowsタスクスケジューラで定期実行用
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import os
import time

# =====================================================
# JSONbin.io設定
# =====================================================
JSONBIN_API_KEY = '$2a$10$PdTNFUnYM6.Xw2dRjRmlO.ecKLu4vw5B8HTWk4qWIB6b7N7fBpZGS'
JSONBIN_BIN_ID = '6989e55a43b1c97be971c359'

# 更新間隔（秒）
UPDATE_INTERVAL = 30 * 60  # 30分ごと

# ログファイル
LOG_FILE = os.path.join(os.path.dirname(__file__), 'auto_update.log')


def log(message):
    """ログ出力"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')


class GetKeirin:
    """競輪データ取得クラス"""

    def get_html(self, date):
        date_fmt = date.strftime('%Y/%m/%d/')
        url = f"https://keirin.kdreams.jp/harailist/{date_fmt}"
        try:
            date_str = url.split('/harailist/')[1].strip('/')
        except IndexError:
            date_str = date.strftime('%Y%m%d')
        response = requests.get(url, timeout=30)
        response.encoding = 'utf-8'
        return response, date_str

    def parse_html(self, res, date_str):
        soup = BeautifulSoup(res.content, 'html.parser')
        data = {}
        date_str_key = re.sub(r'/', '', date_str)
        section = soup.find('div', id='JS_KAKESHIKI_AREA_5')

        if section is None:
            return {}

        if date_str_key not in data:
            data[date_str_key] = {}

        for li in section.find_all('li', recursive=True):
            header = li.find('div', class_='header')
            if not header:
                continue

            velodrome = header.find('span', class_='velodrome')
            stadium_name = velodrome.get_text(strip=True) if velodrome else "不明"
            stadium_name = stadium_name.replace('競輪', '')

            if stadium_name not in data[date_str_key]:
                data[date_str_key][stadium_name] = {}

            table = li.find('table')
            if not table:
                continue

            rows = table.find_all('tr')[1:]
            last_valid_time = None

            for row in rows:
                race_td = row.find('td', class_='race')
                order_td = row.find('td', class_='order')

                if race_td and order_td:
                    race_num = race_td.get_text(strip=True)
                    order_text = order_td.get_text(strip=True)

                    current_value_to_save = None

                    if ':' in order_text:
                        current_value_to_save = order_text
                        last_valid_time = order_text
                    elif last_valid_time is not None:
                        current_value_to_save = last_valid_time

                    if current_value_to_save:
                        data[date_str_key][stadium_name][race_num] = {
                            'time': current_value_to_save
                        }

        return data

    def get_keirin(self, target_date):
        res, date_str = self.get_html(target_date)
        data = self.parse_html(res, date_str)
        return data


class GetKyotei:
    """競艇データ取得クラス"""

    def get_html(self, date_str):
        url = f'https://www.boatrace.jp/owpc/pc/race/pay?hd={date_str}'
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/114.0.0.0 Safari/537.36')
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response

    def parse_html(self, response, date_str):
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table', {'class': 'is-strited1 is-wAuto'})
        venue_to_strings = {}

        for table in tables:
            headers_img = table.find_all('img', alt=True)
            venue_names = [img['alt'].strip() for img in headers_img if img.get('alt')]
            last_valid_times_by_venue = {name: None for name in venue_names}

            rows = table.find_all('tr', {'class': 'is-p3-0'})
            for row in rows:
                th_r = row.find('th', {'class': 'is-thColor8'})
                if not th_r:
                    continue
                race_number = th_r.get_text(strip=True)

                tds = row.find_all('td')
                if not tds:
                    continue

                for vi, venue in enumerate(venue_names):
                    base = vi * 3
                    if base >= len(tds):
                        break

                    time_td = tds[base]
                    race_time = time_td.get_text(strip=True)
                    current_value_to_save = None

                    if ':' in race_time:
                        current_value_to_save = race_time
                        last_valid_times_by_venue[venue] = race_time
                    elif last_valid_times_by_venue[venue] is not None:
                        current_value_to_save = last_valid_times_by_venue[venue]

                    if current_value_to_save:
                        venue_to_strings.setdefault(date_str, {}).setdefault(venue, {})[race_number] = {
                            'time': current_value_to_save
                        }

        return venue_to_strings

    def get_kyotei(self, target_date):
        date_str = target_date.strftime('%Y%m%d')
        response = self.get_html(date_str)
        data = self.parse_html(response, date_str)
        return data


def upload_to_jsonbin(data):
    """JSONbin.ioにデータをアップロード"""
    if JSONBIN_BIN_ID.startswith('xxxx'):
        log("JSONbin.io未設定、スキップ")
        return False

    url = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"
    headers = {
        'Content-Type': 'application/json',
        'X-Master-Key': JSONBIN_API_KEY
    }

    try:
        response = requests.put(url, json=data, headers=headers, timeout=30)
        if response.status_code == 200:
            log("JSONbin.ioアップロード成功")
            return True
        else:
            log(f"JSONbin.ioアップロード失敗: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log(f"JSONbin.ioエラー: {e}")
        return False


def save_local_json(data, filename):
    """ローカルにJSONを保存"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"ローカル保存: {filename}")
    return filepath


def fetch_and_upload():
    """データ取得・アップロード処理"""
    log("=" * 50)
    log("データ取得開始")

    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    target_dates = [now, tomorrow]

    all_data = {
        'keirin': {},
        'kyotei': {},
        'updated_at': now.strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        for target_dt in target_dates:
            date_str = target_dt.strftime('%Y%m%d')
            log(f"【{target_dt.strftime('%Y/%m/%d')}】取得中...")

            # 競輪データ取得
            try:
                keirin = GetKeirin()
                keirin_data = keirin.get_keirin(target_dt)
                if keirin_data:
                    all_data['keirin'].update(keirin_data)
                    log(f"  競輪: {len(keirin_data.get(date_str, {}))}会場")
                else:
                    log("  競輪: データなし")
            except Exception as e:
                log(f"  競輪エラー: {e}")

            # 競艇データ取得
            try:
                kyotei = GetKyotei()
                kyotei_data = kyotei.get_kyotei(target_dt)
                if kyotei_data:
                    all_data['kyotei'].update(kyotei_data)
                    log(f"  競艇: {len(kyotei_data.get(date_str, {}))}会場")
                else:
                    log("  競艇: データなし")
            except Exception as e:
                log(f"  競艇エラー: {e}")

            # 少し待機（サーバー負荷軽減）
            time.sleep(1)

        # ローカルに保存
        save_local_json(all_data, 'race_data.json')

        # JSONbin.ioにアップロード
        upload_to_jsonbin(all_data)

        log("データ取得完了")
        return True

    except Exception as e:
        log(f"エラー発生: {e}")
        return False


def main():
    """常駐型メイン処理"""
    log("=" * 50)
    log("常駐モード開始")
    log(f"更新間隔: {UPDATE_INTERVAL // 60}分")
    log("終了するには Ctrl+C を押してください")
    log("=" * 50)

    while True:
        try:
            fetch_and_upload()

            next_update = datetime.now() + timedelta(seconds=UPDATE_INTERVAL)
            log(f"次回更新: {next_update.strftime('%H:%M:%S')}")
            log("-" * 30)

            time.sleep(UPDATE_INTERVAL)

        except KeyboardInterrupt:
            log("終了します")
            break
        except Exception as e:
            log(f"予期せぬエラー: {e}")
            log("60秒後に再試行...")
            time.sleep(60)


if __name__ == "__main__":
    main()
