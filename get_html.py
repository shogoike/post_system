import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import tkinter as tk
from tkinter import ttk, messagebox

# --- 競輪クラス (値引き継ぎ機能あり) ---
class GetKeirin():
    def __init__(self):
        pass
            
    # デフォルトの日付判定（GUIからの指定がない場合用）
    def get_date(self): 
        now = datetime.now()
        if now.hour >= 20:
            return now + timedelta(days=1)
        else:
            return now

    def get_html(self, date):
        date_fmt = date.strftime('%Y/%m/%d/')
        url = f"https://keirin.kdreams.jp/harailist/{date_fmt}"
        try:
            date_str = url.split('/harailist/')[1].strip('/')
        except IndexError:
            date_str = date.strftime('%Y%m%d')

        response = requests.get(url)
        response.encoding = 'utf-8'
        return response, date_str

    def perse_html(self, res, date_str):
        soup = BeautifulSoup(res.content, 'html.parser')
        data = {}
        date_str_key = re.sub(r'/', '', date_str)
        section = soup.find('div', id='JS_KAKESHIKI_AREA_5')

        if section is None:
            return "", {}

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
            
            # 前の値を保持するための変数 (競輪場ごとにリセット)
            last_valid_time = None

            for row in rows:
                race_td = row.find('td', class_='race')
                order_td = row.find('td', class_='order')
                
                if race_td and order_td:
                    race_num = race_td.get_text(strip=True)
                    order_text = order_td.get_text(strip=True)
                    
                    if race_num not in data[date_str_key][stadium_name]:
                        data[date_str_key][stadium_name][race_num] = []
                    
                    current_value_to_save = None

                    # 1. 有効なデータがある場合
                    if ':' in order_text:
                        current_value_to_save = order_text
                        last_valid_time = order_text
                    # 2. データがなく、かつ前の値がある場合（引き継ぎ）
                    elif last_valid_time is not None:
                        current_value_to_save = last_valid_time
                    
                    if current_value_to_save:
                        data[date_str_key][stadium_name][race_num] = {
                            'time': current_value_to_save
                        }
        
        filename = f'keirin_data_{date_str_key}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return filename, data
    
    def get_keirin(self, target_date=None):
        if target_date is None:
            date = self.get_date()
        else:
            date = target_date

        res, date_str = self.get_html(date)
        filename, data = self.perse_html(res, date_str)
        return filename


# --- 競艇クラス (値引き継ぎ機能あり) ---
class GetKyotei():
    def __init__(self):
        pass
            
    def get_date(self):
        now = datetime.now()
        if now.hour >= 20:
            return (now + timedelta(days=1)).strftime('%Y%m%d')
        else:
            return now.strftime('%Y%m%d')
            
    def get_html(self, date_str):
        url = f'https://www.boatrace.jp/owpc/pc/race/pay?hd={date_str}'
        headers = {
            'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/114.0.0.0 Safari/537.36')
        }
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response
    
    def perse_html(self, response, date_str):
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table', {'class': 'is-strited1 is-wAuto'})
        venue_to_strings = {}

        for table in tables:
            headers_img = table.find_all('img', alt=True)
            venue_names = [img['alt'].strip() for img in headers_img if img.get('alt')]

            # 各会場ごとの「前の値」を保持する辞書
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

                    # 1. 有効なデータがある場合
                    if ':' in race_time:
                        current_value_to_save = race_time
                        last_valid_times_by_venue[venue] = race_time
                    # 2. データがなく、かつ前の値がある場合（引き継ぎ）
                    elif last_valid_times_by_venue[venue] is not None:
                        current_value_to_save = last_valid_times_by_venue[venue]

                    if current_value_to_save:
                        venue_to_strings.setdefault(date_str, {}).setdefault(venue, {})[race_number] = {
                            'time': current_value_to_save
                        }

        filename = f'kyotei_data_{date_str}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(venue_to_strings, f, ensure_ascii=False, indent=2)

        return filename, venue_to_strings
            
    def get_kyotei(self, target_date=None):
        if target_date is None:
            date_str = self.get_date()
        else:
            date_str = target_date.strftime('%Y%m%d')

        response = self.get_html(date_str)
        filename, data = self.perse_html(response, date_str)
        return filename


# --- Tkinter GUI アプリケーション ---
class RaceDataApp:
    def __init__(self, root):
        self.root = root
        self.root.title("公営競技データ一括取得ツール")
        self.root.geometry("450x300")

        # ★表示を変更
        lbl_desc = ttk.Label(root, text="「今日」と「明日」のデータをまとめて取得します。\n※データなしの場合は前の値を引き継ぎます。", padding=10)
        lbl_desc.pack()

        # ★ボタンのテキストを変更
        self.btn_run = ttk.Button(root, text="実行 (今日・明日のデータを取得)", command=self.run_scraping)
        self.btn_run.pack(pady=10, ipadx=10, ipady=5)

        frame_log = ttk.LabelFrame(root, text="実行ログ", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.log_text = tk.Text(frame_log, height=10, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(frame_log, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text['yscrollcommand'] = scrollbar.set

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")
        self.root.update_idletasks()

    def run_scraping(self):
        self.btn_run.config(state="disabled")
        
        # ★ここを変更: 今日と明日の日付リストを作成
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        target_dates = [now, tomorrow]
        
        self.log("=" * 40)
        self.log(f"処理開始: 全{len(target_dates)}日分")

        try:
            for target_dt in target_dates:
                date_str_log = target_dt.strftime('%Y/%m/%d')
                self.log("-" * 30)
                self.log(f"【{date_str_log}】のデータを取得中...")

                keirin = GetKeirin()
                k_file = keirin.get_keirin(target_date=target_dt)
                if k_file:
                    self.log(f"  [競輪] 保存完了: {k_file}")
                else:
                    self.log(f"  [競輪] データなし")

                kyotei = GetKyotei()
                b_file = kyotei.get_kyotei(target_date=target_dt)
                if b_file:
                    self.log(f"  [競艇] 保存完了: {b_file}")
                else:
                    self.log(f"  [競艇] データなし")

            self.log("-" * 30)
            self.log("全ての処理が完了しました。")
            messagebox.showinfo("成功", "データ取得・保存が完了しました。")

        except Exception as e:
            self.log(f"エラー発生: {e}")
            messagebox.showerror("エラー", f"処理中にエラーが発生しました\n{e}")
        
        finally:
            self.btn_run.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = RaceDataApp(root)
    root.mainloop()