import flet as ft
import requests
import threading
import time

# --- 全局配置变量 ---
app_config = {
    "base_url": "",
    "token": "",
    "running": True
}

# --- 实体 ID 配置 ---
ENTITY_ID = {
    "play_enhanced_execute": "text.xiaomi_l05c_37bc_execute_text_directive",
    "play_enhanced_play_text": "text.xiaomi_l05c_37bc_play_text",
    "pro_execute": "text.xiaomi_lx06_22f3_execute_text_directive",
    "pro_play_text": "text.xiaomi_lx06_22f3_play_text",
}

SENSOR_ENTITY_ID = {
    "floor11_temp": "sensor.miaomiaoce_t2_cb34_temperature",
    "floor11_humid": "sensor.miaomiaoce_t2_cb34_relative_humidity",
    "floor11_battery": "sensor.miaomiaoce_t2_cb34_battery_level",
    "floor5_temp": "sensor.miaomiaoce_t2_f771_temperature",
    "floor5_humid": "sensor.miaomiaoce_t2_f771_relative_humidity",
    "floor5_battery": "sensor.miaomiaoce_t2_f771_battery_level",
}

def main(page: ft.Page):
    page.title = "家庭中控 (安全版)"
    page.theme_mode = "light" # 改为字符串
    page.scroll = "adaptive"  # 改为字符串
    page.padding = 20

    # --- 核心功能函数 ---
    def get_ha_state(entity_id):
        if not app_config["base_url"] or not app_config["token"]:
            return "未配置", ""
            
        api_url = f"{app_config['base_url']}/api/states/{entity_id}"
        headers = {"Authorization": f"Bearer {app_config['token']}", "Content-Type": "application/json"}
        try:
            response = requests.get(api_url, headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                state = data.get("state", "N/A")
                unit = data.get("attributes", {}).get("unit_of_measurement", "")
                return state, unit
        except Exception:
            pass
        return "N/A", ""

    def call_ha_service(entity_id, text_command):
        if not text_command:
            page.snack_bar = ft.SnackBar(ft.Text("请输入指令！"))
            page.snack_bar.open = True
            page.update()
            return

        api_url = f"{app_config['base_url']}/api/services/text/set_value"
        headers = {"Authorization": f"Bearer {app_config['token']}", "Content-Type": "application/json"}
        payload = {"entity_id": entity_id, "value": text_command}
        
        try:
            requests.post(api_url, headers=headers, json=payload, timeout=5)
            page.snack_bar = ft.SnackBar(ft.Text(f"指令已发送"))
        except Exception as e:
            page.snack_bar = ft.SnackBar(ft.Text(f"发送失败: {e}"))
        
        page.snack_bar.open = True
        page.update()

    # --- 界面 1: 登录配置页 ---
    # 默认值留空或填入示例
    url_input = ft.TextField(label="HA 地址", hint_text="http://192.168.0.3:8123", value="http://192.168.0.3:8123")
    token_input = ft.TextField(label="长效 Token", password=True, can_reveal_password=True, multiline=True, min_lines=1, max_lines=5)
    
    def save_config(e):
        if not url_input.value or not token_input.value:
            page.snack_bar = ft.SnackBar(ft.Text("请填写完整信息"))
            page.snack_bar.open = True
            page.update()
            return
            
        # 保存到本地存储
        page.client_storage.set("ha_url", url_input.value)
        page.client_storage.set("ha_token", token_input.value)
        
        # 更新内存配置
        app_config["base_url"] = url_input.value
        app_config["token"] = token_input.value
        
        # 进入主页
        show_main_page()

    login_view = ft.Column([
        ft.Container(height=50),
        ft.Text("首次设置", size=30, weight="bold"),
        ft.Text("请输入您的 Home Assistant 信息，信息仅保存在本机。"),
        ft.Container(height=20),
        url_input,
        token_input,
        ft.Container(height=20),
        ft.ElevatedButton("保存并进入", on_click=save_config, height=50, width=200)
    ], horizontal_alignment="center")

    # --- 界面 2: 主控制台 ---
    def show_main_page():
        page.clean() 
        
        txt_command = ft.TextField(label="请输入指令文本", hint_text="例如：播放音乐", expand=True)

        def create_sensor_card(title, temp_id, humid_id, batt_id):
            txt_temp = ft.Text("温度: --", size=16, weight="bold")
            txt_humid = ft.Text("湿度: --", size=16)
            pb_batt = ft.ProgressBar(width=100, color="green", bgcolor="grey", value=0)
            txt_batt = ft.Text("电量: --%", size=12)

            def update_data():
                if not app_config["token"]: return

                s, u = get_ha_state(temp_id)
                txt_temp.value = f"温度: {s}{u}"
                s, u = get_ha_state(humid_id)
                txt_humid.value = f"湿度: {s}{u}"
                s, _ = get_ha_state(batt_id)
                try:
                    val = float(s) / 100.0
                    pb_batt.value = val
                    txt_batt.value = f"电量: {s}%"
                    pb_batt.color = "red" if val < 0.2 else "green"
                except:
                    pb_batt.value = 0
                    txt_batt.value = "电量: N/A"
                page.update()

            card = ft.Container(
                content=ft.Column([
                    ft.Text(title, size=20, weight="bold", color="blue"),
                    ft.Row([txt_temp, txt_humid], alignment="spaceBetween"),
                    ft.Row([ft.Text("电池:"), pb_batt, txt_batt], alignment="start")
                ]),
                padding=15,
                border_radius=10,
                bgcolor="bluegrey50",
                border=ft.border.all(1, "grey")
            )
            return card, update_data

        card_11, update_11 = create_sensor_card("11楼 传感器", SENSOR_ENTITY_ID["floor11_temp"], SENSOR_ENTITY_ID["floor11_humid"], SENSOR_ENTITY_ID["floor11_battery"])
        card_5, update_5 = create_sensor_card("5楼 传感器", SENSOR_ENTITY_ID["floor5_temp"], SENSOR_ENTITY_ID["floor5_humid"], SENSOR_ENTITY_ID["floor5_battery"])

        def run_refresh_loop():
            update_11()
            update_5()
            while app_config["running"]:
                time.sleep(300)
                if app_config["token"]:
                    update_11()
                    update_5()

        threading.Thread(target=run_refresh_loop, daemon=True).start()

        def logout(e):
            app_config["token"] = ""
            page.client_storage.clear()
            page.clean()
            page.add(login_view)
            page.update()

        page.add(
            ft.Row([
                ft.Text("智能家居控制台", size=24, weight="bold"),
                # --- 关键修改：这里把 ft.icons.LOGOUT 改成了字符串 "logout" ---
                ft.IconButton(icon="logout", tooltip="注销/清除配置", on_click=logout)
            ], alignment="spaceBetween"),
            
            ft.Divider(),
            card_11,
            ft.Container(height=10),
            card_5,
            
            ft.Divider(),
            ft.Text("音箱控制", size=20, weight="bold"),
            ft.Row([txt_command]),
            
            ft.Text("Play 增强版", color="grey"),
            ft.Row([
                ft.ElevatedButton("执行指令", on_click=lambda e: call_ha_service(ENTITY_ID["play_enhanced_execute"], txt_command.value), expand=True),
                ft.ElevatedButton("播放文本", on_click=lambda e: call_ha_service(ENTITY_ID["play_enhanced_play_text"], txt_command.value), expand=True),
            ]),
            ft.Row([
                ft.ElevatedButton("退下", color="red", on_click=lambda e: call_ha_service(ENTITY_ID["play_enhanced_execute"], "退下"), expand=True)
            ]),
            
            ft.Container(height=10),
            
            ft.Text("Pro 版", color="grey"),
            ft.Row([
                ft.ElevatedButton("执行指令", on_click=lambda e: call_ha_service(ENTITY_ID["pro_execute"], txt_command.value), expand=True),
                ft.ElevatedButton("播放文本", on_click=lambda e: call_ha_service(ENTITY_ID["pro_play_text"], txt_command.value), expand=True),
            ]),
            ft.Row([
                ft.ElevatedButton("退下", color="red", on_click=lambda e: call_ha_service(ENTITY_ID["pro_execute"], "退下"), expand=True)
            ]),
            
            ft.Divider(),
            # --- 这里已经是字符串 "refresh" 了，无需修改 ---
            ft.ElevatedButton("手动刷新传感器", icon="refresh", on_click=lambda e: [update_11(), update_5()])
        )
        page.update()

    # --- 3. 程序启动入口 ---
    stored_url = page.client_storage.get("ha_url")
    stored_token = page.client_storage.get("ha_token")

    if stored_url and stored_token:
        app_config["base_url"] = stored_url
        app_config["token"] = stored_token
        url_input.value = stored_url
        token_input.value = stored_token
        show_main_page()
    else:
        page.add(login_view)

ft.app(target=main)