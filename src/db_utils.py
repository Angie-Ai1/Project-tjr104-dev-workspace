import os                       # 讀取作業系統的環境變數 (如 .env 裡的設定)
import time                     # 讓程式暫停幾秒 (等待連線建立)
import socket                   # 檢查網路 Port 是否有通 (像打電話確認有沒有人接)
import subprocess               # 在背景執行外部指令 (這裡是執行 gcloud 指令)
import atexit                   # 註冊「程式結束時」要執行的收尾動作
from sqlalchemy import create_engine  # 用於建立資料庫連線物件 (Engine)
from sqlalchemy.engine import make_url # 用於解析資料庫連線字串 (把 URL 拆解成 user, host, port...)
from dotenv import load_dotenv  # 載入 .env 檔案


# 定義一個全域變數, 用來存放 SSH Tunnel 的處理程序
# 這樣才能在程式結束時找到它, 並將其關閉
load_dotenv()
_tunnel_process = None

def is_port_open(host, port):
    # 建立一個 socket 物件 (像是一支電話)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)  # 設定超時時間為 1 秒, 如果 1 秒沒連上就算失敗, 避免卡住
    
    try:
        # 嘗試連線到指定的 host 和 port
        s.connect((host, int(port)))
        s.shutdown(2) # 連線成功, 馬上斷開(連線確定用)
        return True   # 連線成功
    except:
        return False  # 連線失敗
    finally:
        s.close()     # 確保釋放資源

def start_ssh_tunnel(local_port):
    """
    自動執行 gcloud 指令, 建立 SSH Tunnel (地道)
    local_port: 希望在本機開在哪個 Port (例如 3307)
    """
    global _tunnel_process # 宣告修改外面的全域變數
    
    # 從.env讀取 VM 的連線資訊
    vm_name = os.getenv("VM_NAME")       # 例如: test_db
    zone = os.getenv("VM_ZONE")          # 例如: asia-east1-c
    project = os.getenv("PROJECT_ID")    # 例如: watchful-net-xxxxx
    
    if is_port_open("127.0.0.1", local_port):
        # print(f"SSH 通道已存在 (Port {local_port}), 直接使用現有通道")
        return

    print(f"偵測到 Port {local_port} 未開啟, 正在建立 SSH Tunnel 連線到 {vm_name}...")
    
    # 組合 gcloud 指令 (拆成 List 格式)
    # 格式: gcloud compute ssh [VM] --zone [ZONE] --project [ID] --tunnel-through-iap -- -N -L [LOCAL]:localhost:3306
    cmd = [
        "gcloud", "compute", "ssh", vm_name,
        "--zone", zone,
        "--project", project,
        "--tunnel-through-iap", # 使用 IAP 穿透防火牆 (Google 的黑科技, 不用開 VM 的 public IP)
        "--", 
        "-N",  # 關鍵參數：告訴 SSH "不要執行遠端指令, 也不要開 Shell", 只做轉發這樣程式才不會卡住
        "-L", f"{local_port}:localhost:3306" # 建立地道：把本機的 local_port 對應到 VM 的 3306
    ]

    # 設定隱藏視窗的旗標 (Flag)
    # 如果是在 Windows 系統 (os.name == 'nt'), 設定 CREATE_NO_WINDOW 來隱藏黑視窗
    # 如果是 Mac/Linux, 則設為 0 (不特別設定)
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    
    # 使用 subprocess.Popen 在背景啟動指令
    _tunnel_process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE,       # 把標準輸出導向 PIPE (不顯示在螢幕上)
        stderr=subprocess.PIPE,       # 把錯誤輸出導向 PIPE
        creationflags=creation_flags  # 套用剛剛設定的隱藏視窗設定
    )

    print("⏳ 等待連線建立中 (約 5 秒)...")
    time.sleep(5) # 強制等待 5 秒, 讓 gcloud 有時間完成連線握手
    
    # 再次檢查 Port, 確認連線是否成功
    if is_port_open("127.0.0.1", local_port):
        print("SSH Tunnel 建立成功！資料庫連線準備就緒")
    else:
        print("SSH Tunnel 建立失敗！請檢查網路或 gcloud login 狀態")

# 負責關閉 gcloud 背景程式, 如果不關掉, Port 會一直被佔用, 下次執行會報錯
def cleanup_tunnel():
    global _tunnel_process
    if _tunnel_process:
        print("正在關閉 SSH Tunnel...")
        _tunnel_process.terminate() # 強制終止程序
        _tunnel_process = None

# 使用 atexit 註冊：當 Python 程式結束(無論正常結束或當機)時, 自動執行 cleanup_tunnel
atexit.register(cleanup_tunnel)

def get_db_engine():
    """
    主函式：取得資料庫連線引擎 (Engine)
    它會自動處理 URL 解析、通道建立、以及連線物件生成
    """

    # 如果沒設定 URL, 印出錯誤並回傳 None
    db_url = os.getenv("MYSQLSQL_URL") 
    if not db_url: 
        print("錯誤: .env 檔案中找不到 MYSQL_URL 設定")
        return None
    try:
        url_obj = make_url(db_url)
        target_port = url_obj.port
        if not target_port:
            target_port = 3307
            print(f"⚠️ URL 未指定 Port, 預設使用 {target_port}")
        start_ssh_tunnel(target_port)
        engine = create_engine(db_url, pool_recycle=3600) # pool_recycle=3600 每小時回收連線一次)
        return engine
        
    except Exception as e:
        print(f"資料庫連線初始化失敗: {e}")
        return None