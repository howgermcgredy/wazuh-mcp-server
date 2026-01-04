import os
import requests
import urllib3
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# 1. 初始化設定
load_dotenv() # 讀取 .env 裡的密碼
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning) # 忽略 SSL 警告

# 設定 MCP Server 名稱
mcp = FastMCP("Wazuh-Integrator")

# Wazuh 設定
WAZUH_URL = os.getenv("WAZUH_API_URL")
WAZUH_USER = os.getenv("WAZUH_USER")
WAZUH_PASS = os.getenv("WAZUH_PASSWORD")

# 2. 輔助函式：取得 Token
def get_token():
    """向 Wazuh 取得驗證 Token"""
    url = f"{WAZUH_URL}/security/user/authenticate?raw=true"
    try:
        response = requests.get(
            url, 
            auth=(WAZUH_USER, WAZUH_PASS), 
            verify=False # 因為是 localhost 自簽憑證，所以忽略驗證
        )
        if response.status_code == 200:
            return response.text # 回傳 Token 字串
        else:
            raise Exception(f"登入失敗: {response.text}")
    except Exception as e:
        raise Exception(f"連線錯誤: {str(e)}")

# 3. 定義 MCP 工具 (Tools) - 這就是 AI 會呼叫的功能

@mcp.tool()
def list_agents() -> str:
    """查詢目前 Wazuh 連接的所有 Agent 列表，包含 ID、名稱與連線狀態"""
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 呼叫 Wazuh API: GET /agents
        resp = requests.get(f"{WAZUH_URL}/agents", headers=headers, verify=False)
        data = resp.json()

        # 整理回傳給 AI 的訊息
        agents = data.get('data', {}).get('affected_items', [])
        if not agents:
            return "目前沒有發現任何 Agent。"

        result = "【Wazuh Agent 列表】\n"
        for agent in agents:
            status = "🟢 線上" if agent['status'] == 'active' else "🔴 離線"
            result += f"- ID: {agent['id']} | 名稱: {agent['name']} | IP: {agent.get('ip', 'N/A')} | 狀態: {status}\n"
        return result
    except Exception as e:
        return f"查詢錯誤: {str(e)}"

@mcp.tool()
def get_alerts() -> str:
    """查詢最近的 5 筆資安警報"""
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}

        # 呼叫 Wazuh API: GET /alerts
        params = {"limit": 5} 
        resp = requests.get(f"{WAZUH_URL}/alerts", headers=headers, params=params, verify=False)

        if resp.status_code != 200:
            return f"無法取得警報: {resp.text}"

        data = resp.json()
        alerts = data.get('data', {}).get('affected_items', [])

        if not alerts:
            return "最近沒有警報。"

        result = "【最近 5 筆警報】\n"
        for alert in alerts:
            rule = alert.get('rule', {})
            result += f"- 等級: {rule.get('level')} | 描述: {rule.get('description')}\n"
        return result
    except Exception as e:
        return f"查詢錯誤: {str(e)}"

# 4. 啟動伺服器
if __name__ == "__main__":
    print("🚀 Wazuh MCP Server 啟動中... (按 Ctrl+C 結束)")
    mcp.run()
