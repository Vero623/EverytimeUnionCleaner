import tkinter as tk
from tkinter import scrolledtext
import threading
import requests
import time
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class EverytimeDeleterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("에브리타임 글/댓글 삭제기")
        self.root.geometry("750x500")

        self.x_et_device = None
        self.etsid = None
        self.comment_cnt = 0
        self.post_cnt = 0

        self.stop_flag = False
        self.pause_event = threading.Event()
        self.pause_event.set()

        left_frame = tk.Frame(root)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=15, pady=15)

        right_frame = tk.Frame(root)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.login_btn = tk.Button(left_frame, text="1. 에브리타임 로그인", command=self.start_login_thread, width=20, height=2)
        self.login_btn.pack(pady=5)

        self.delete_post_btn = tk.Button(left_frame, text="2. 내 글 모두 삭제", command=self.start_delete_post_thread, width=20, height=2, state=tk.DISABLED)
        self.delete_post_btn.pack(pady=5)

        self.delete_comment_btn = tk.Button(left_frame, text="3. 내 댓글 모두 삭제", command=self.start_delete_comment_thread, width=20, height=2, state=tk.DISABLED)
        self.delete_comment_btn.pack(pady=5)

        tk.Frame(left_frame, height=2, bg="gray").pack(fill=tk.X, pady=15)

        self.pause_btn = tk.Button(left_frame, text="일시정지", command=self.toggle_pause, width=20, height=2, state=tk.DISABLED)
        self.pause_btn.pack(pady=5)

        self.stop_btn = tk.Button(left_frame, text="중지", command=self.stop_task, width=20, height=2, state=tk.DISABLED)
        self.stop_btn.pack(pady=5)

        self.log_area = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        self.log("[SYSTEM] 시스템이 초기화되었습니다. 로그인을 진행해 주십시오.")

    def log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def update_ui_state(self, is_running):
        if is_running:
            self.login_btn.config(state=tk.DISABLED)
            self.delete_post_btn.config(state=tk.DISABLED)
            self.delete_comment_btn.config(state=tk.DISABLED)
            self.pause_btn.config(state=tk.NORMAL, text="일시정지")
            self.stop_btn.config(state=tk.NORMAL)
        else:
            self.login_btn.config(state=tk.NORMAL)
            if self.x_et_device and self.etsid:
                self.delete_post_btn.config(state=tk.NORMAL)
                self.delete_comment_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED, text="일시정지")
            self.stop_btn.config(state=tk.DISABLED)

    def toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.config(text="계속")
            self.log("[SYSTEM] 작업이 일시 중단되었습니다. (대기열의 잔여 1건은 처리될 수 있습니다)")
        else:
            self.pause_event.set()
            self.pause_btn.config(text="일시정지")
            self.log("[SYSTEM] 작업을 재개합니다.")

    def stop_task(self):
        self.stop_flag = True
        self.pause_event.set()
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("[SYSTEM] 작업 강제 종료를 요청했습니다. 안전한 종료를 위해 잠시 대기 중입니다...")

    def check_flow_control(self):
        self.pause_event.wait()
        return self.stop_flag

    def start_login_thread(self):
        self.update_ui_state(is_running=True)
        self.pause_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.login_process, daemon=True).start()

    def login_process(self):
        self.log("[INFO] 브라우저 인스턴스를 생성 중입니다. 로그인을 완료해 주십시오.")
        try:
            driver = webdriver.Chrome()
            driver.get('https://account.everytime.kr/login')
            WebDriverWait(driver, 99999).until(EC.url_to_be("https://everytime.kr/"))
            
            cookies = driver.get_cookies()
            cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
            
            self.x_et_device = cookie_dict.get('x-et-device')
            self.etsid = cookie_dict.get('etsid')
            
            if self.x_et_device and self.etsid:
                self.log("[SUCCESS] 인증 토큰 및 쿠키 획득이 완료되었습니다.")
            else:
                self.log("[ERROR] 인증 데이터 추출에 실패했습니다. 로그인 다시 시도해 주십시오.")
            driver.quit()
            self.update_ui_state(is_running=False)
        except Exception as e:
            self.log(f"[ERROR] 로그인 프로세스 중 오류가 발생했습니다: {e}")
            driver.quit() 
            self.update_ui_state(is_running=False)

    def start_delete_post_thread(self):
        self.stop_flag = False
        self.pause_event.set()
        self.update_ui_state(is_running=True)
        self.post_cnt = 0
        threading.Thread(target=self.load_and_delete_posts, daemon=True).start()

    def load_and_delete_posts(self):
        self.log("[INFO] 게시글 데이터 스캔 및 삭제를 시작합니다...")
        url = "https://api.everytime.kr/find/union-board/article/mine"
        headers = {
            "Cookie": f"x-et-device={self.x_et_device}; etsid={self.etsid}",
            "User-Agent": "everytimeApp; Android/8.3.4 (Android/16; SM-S931N)"
        }
        payload = {}
        
        try:
            while True:
                if self.check_flow_control(): break
                
                time.sleep(0.5)
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("result", {}).get("items", [])
                
                if not items:
                    break
                    
                for item in items:
                    if self.check_flow_control(): break
                    
                    delete_url = "https://api.everytime.kr/delete/union-board/article"
                    requests.post(delete_url, headers=headers, json={"articleId": item["id"]}).raise_for_status()
                    self.post_cnt += 1
                    self.log(f"[SUCCESS] 게시글 삭제 완료 (ID: {item['id']} | 누적 처리: {self.post_cnt}건)")
                    
                next_cursor = data.get("result", {}).get("nextCursor")
                if next_cursor is not None:
                    payload["cursor"] = next_cursor
                    payload["direction"] = "next"
                else:
                    break
                    
            if self.stop_flag:
                self.log(f"[SYSTEM] 사용자에 의해 중단되었습니다. ({self.post_cnt}건)")
            else:
                self.log(f"[SYSTEM] 게시글 삭제가 성공적으로 완료되었습니다. (총 {self.post_cnt}건)")
        except Exception as e:
            self.log(f"[ERROR] 오류 발생으로 인해 작업이 중지되었습니다: {e}")
        finally:
            self.update_ui_state(is_running=False)

    def start_delete_comment_thread(self):
        self.stop_flag = False
        self.pause_event.set()
        self.update_ui_state(is_running=True)
        self.comment_cnt = 0
        threading.Thread(target=self.load_and_delete_comments, daemon=True).start()

    def execute_delete_comment(self, comment_id):
        url = "https://api.everytime.kr/delete/union-board/comment"
        headers = {
            "Cookie": f"x-et-device={self.x_et_device}; etsid={self.etsid}",
            "User-Agent": "everytimeApp; Android/8.3.4 (Android/16; SM-G931N)"
        }
        requests.post(url, headers=headers, json={"commentId": comment_id}).raise_for_status()
        self.comment_cnt += 1
        self.log(f"[SUCCESS] 댓글 삭제 완료 (ID: {comment_id} | 누적 처리: {self.comment_cnt}건)")

    def find_and_delete_my_comments(self, article_id):
        url = "https://api.everytime.kr/find/union-board/comment/list"
        headers = {
            "Cookie": f"x-et-device={self.x_et_device}; etsid={self.etsid}",
            "User-Agent": "everytimeApp; Android/8.3.4 (Android/16; SM-G931N)",
            "X-Et-Device": str(self.x_et_device),
            "Content-Type": "application/json; charset=utf-8",
        }
        payload = {"articleId": article_id, "direction": "next"}
        
        while True:
            if self.check_flow_control(): return
            
            time.sleep(0.3)
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("result", {}).get("items", [])
            
            for item in items:
                if self.check_flow_control(): return
                if item.get("isMine"):
                    self.execute_delete_comment(item["id"])
                    
                for child in item.get("childComments", []):
                    if self.check_flow_control(): return
                    if child.get("isMine"):
                        self.execute_delete_comment(child["id"])
                    
            next_cursor = data.get("result", {}).get("nextCursor")
            if next_cursor is not None:
                payload["cursor"] = next_cursor
                payload["direction"] = "next"
            else:
                break

    def load_and_delete_comments(self):
        self.log("[INFO] 작성한 댓글 스캔 및 삭제를 시작합니다...")
        url = "https://api.everytime.kr/find/union-board/article/commented"
        headers = {
            "Cookie": f"x-et-device={self.x_et_device}; etsid={self.etsid}",
            "User-Agent": "everytimeApp; Android/8.3.4 (Android/16; SM-S931N)"
        }
        payload = {}
        
        try:
            while True:
                if self.check_flow_control(): break
                
                time.sleep(0.5)
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                items = data.get("result", {}).get("items", [])
                
                if not items:
                    break
                    
                for item in items:
                    if self.check_flow_control(): break
                    self.find_and_delete_my_comments(item["id"])
                    
                next_cursor = data.get("result", {}).get("nextCursor")
                if next_cursor is not None:
                    payload["cursor"] = next_cursor
                    payload["direction"] = "next"
                else:
                    break
                    
            if self.stop_flag:
                self.log(f"[SYSTEM] 사용자에 의해 중단되었습니다. ({self.comment_cnt}건)")
            else:
                self.log(f"[SYSTEM] 모든 댓글 삭제가 정상적으로 종료되었습니다. (총 {self.comment_cnt}건)")
        except Exception as e:
            self.log(f"[FATAL] 오류 발생으로 인해 작업이 중지되었습니다: {e}")
        finally:
            self.update_ui_state(is_running=False)

if __name__ == "__main__":
    root = tk.Tk()
    app = EverytimeDeleterApp(root)
    root.mainloop()
