# author: chaosz
import logging
import time
import subprocess
import sys

import requests
from lxml import html

from auth import NAME, PASSWORD

class InfoFilter(logging.Filter):
    def filter(self, record):
        # 只允许 levelno 小于 30 (即 INFO=20 和 DEBUG=10) 的记录通过。
        return record.levelno < logging.WARNING

logger = logging.getLogger("USTC_CampusNetwork_Fallback")
logger.setLevel(logging.DEBUG)

# file_handler = logging.FileHandler('USTC_Network_Fallback.log', encoding='utf-8')
# file_handler.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.addFilter(InfoFilter())
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# file_handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
stderr_handler.setFormatter(formatter)

# logger.addHandler(file_handler)
logger.addHandler(stdout_handler)
logger.addHandler(stderr_handler)

# 网络出口配置
EXPORT_PORTS = ["1", "2", "3", "4", "5", "6", "7", "8"]
EXPORT_PORTS_INFO = {
    "1": "2电信网出口(国际,到教育网走教育网)",
    "2": "3联通网出口(国际,到教育网走教育网)",
    "3": "4电信网出口2(国际,到教育网免费地址走教育网)",
    "4": "5联通网出口2(国际,到教育网免费地址走教育网)",
    "5": "6电信网出口3(国际,默认电信,其他分流)",
    "6": "7联通网出口3(国际,默认联通,其他分流)",
    "7": "8教育网出口2(国际,默认教育网,其他分流)",
    "8": "9移动网出口(国际,无P2P或带宽限制)"
}
current_port_index = 0  # 当前使用的端口索引

def check_network():
    # 弃用
    try:
        resp = requests.get("https://www.baidu.com", timeout=10)
        if resp.status_code == 200:
            logger.info("网络正常")
            return True
        else:
            logger.info(f"网络错误，状态码：{resp.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        logger.info(f"网络错误：{e}")
        return False
def _check_network(retries=5):
    target_ip = "8.8.8.8" 
    command = ["ping", "-c", "1", "-W", "10", target_ip]
    
    for i in range(retries):
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)        # 隐藏输出

        if result.returncode == 0:
            logger.info(f"网络正常")
            return True
        logger.info(f"网络错误 (ping {target_ip} 失败), 重试({i}/{5})")
        time.sleep(30)

    logger.info(f"网络错误 (ping {target_ip} 失败，返回值: {result.returncode})")
    return False
    

def check_status(status):
    display_port_info = status[1][3:].strip()
    expect_port_info = EXPORT_PORTS_INFO[get_current_port()].split("(")[0]
    if display_port_info == expect_port_info:
        return True
    else:
        logger.warning(f"网络设置失败，期望端口：{expect_port_info}，实际端口：{display_port_info}")
        return False

def switch_to_next_port():
    global current_port_index
    current_port_index = (current_port_index + 1) % len(EXPORT_PORTS)

def get_current_port():
    return EXPORT_PORTS[current_port_index]

def get_current_port_info():
    return EXPORT_PORTS_INFO[get_current_port()]

def reset_to_first_port():
    global current_port_index
    current_port_index = 0


def fallback(max_retries=5):
    current_export = get_current_port()
    logger.info(f"尝试使用端口 {get_current_port_info()} 连接网络...")
    
    headers_getip = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "DNT": "1",
        "Host": "wlt.ustc.edu.cn",
        "Referer": "http://wlt.ustc.edu.cn/",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    }
    headers_login = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "Content-Length": "101",
        "Content-Type": "application/x-www-form-urlencoded",
        "DNT": "1",
        "Host": "wlt.ustc.edu.cn",
        "Origin": "http://wlt.ustc.edu.cn",
        "Referer": "http://wlt.ustc.edu.cn/cgi-bin/ip",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    }
    session = requests.Session()
    
    # 获取IP
    ip = ""
    while ip == "" and max_retries > 0:
        try:
            resp = session.get("http://wlt.ustc.edu.cn/cgi-bin/ip", headers=headers_getip)
            if resp.status_code == 200:
                resp.encoding = "gb2312"
                tree = html.fromstring(resp.text)
                ip = tree.xpath("//input[@name='ip']/@value")
                if ip:
                    ip = ip[0]
                    logger.info(f"IP地址：{ip}")
                else:
                    logger.warning(f"未能解析IP地址，重试 {6 - max_retries}/5")
                    time.sleep(1)
            else:
                logger.warning(f"网络错误，状态码：{resp.status_code}, 重试 {6 - max_retries}/5")
                time.sleep(1)
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"网络错误：{e}, 重试 {6 - max_retries}/5")
            time.sleep(1)
        except Exception as e:
            logger.error(f"发生错误：{e}, 重试 {6 - max_retries}/5")
            time.sleep(1)
        finally:
            max_retries -= 1
    if ip:
        # 登录
        resp = session.post(
            "http://wlt.ustc.edu.cn/cgi-bin/ip",
            {
                "cmd": "login",
                "url": "URL",
                "ip": ip,
                "name": NAME,
                "password": PASSWORD,
                "go": "%B5%C7%C2%BC%D5%CA%BB%A7"
            },
            headers=headers_login
        )
        resp.encoding = "gb2312"
        tree = html.fromstring(resp.text)
        user_data = tree.xpath("//p[contains(text(), '拥有的权限')]")
        if user_data:
            user = user_data[0].text_content().removeprefix("\n用户").removesuffix("拥有的权限")
            logger.info(f"成功作为 {user} 登录")
        else:
            logger.warning("登录失败，请检查用户名和密码")
            logger.warning(resp.text)
            return False

        # 设置出口和租期
        session.get(f"http://wlt.ustc.edu.cn/cgi-bin/ip?cmd=set&url=URL&type={current_export}&exp=0&go=+%BF%AA%CD%A8%CD%F8%C2%E7+")
        # 获取网络配置
        resp = session.get("http://wlt.ustc.edu.cn/cgi-bin/ip?cmd=disp")
        resp.encoding = "gb2312"
        
        tree = html.fromstring(resp.text)
        status = tree.xpath("//td[contains(text(), '当前IP地址')]")[0].text_content().strip().split("\n")
        
        if not check_status(status):
            return False
        else:
            logger.info("网络设置成功，开始检测连通性...")
            # 检测连通性
            if not _check_network():
                return False
            else:
                return True
    else:
        logger.warning("未能获取IP地址，登录失败")
        return False

if __name__ == "__main__":    
    while True:
        network_status = _check_network()
        if not network_status:
            logger.info("检测到网络异常，开始尝试登录...")
            # 尝试所有端口
            success = False
            attempted_ports = 0
            
            while not success and attempted_ports < len(EXPORT_PORTS):
                success = fallback()
                
                if not success:
                    attempted_ports += 1
                    if attempted_ports < len(EXPORT_PORTS):
                        logger.warning(f"端口 {get_current_port_info()} 连接失败")
                        switch_to_next_port()
                        logger.info(f"准备尝试下一个端口...({attempted_ports}/{len(EXPORT_PORTS)})")
                        time.sleep(5)
            
            if not success:
                logger.warning("所有端口都尝试失败，等待60秒后重试...")
                # 重置到第一个端口
                reset_to_first_port()
            else:
                logger.info(f"成功连接，当前使用端口：{get_current_port_info()}")

        time.sleep(60)