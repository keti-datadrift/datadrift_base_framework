import subprocess
import time
import re

# 감지된 에지 장치가 호스트 파일에 이미 존재하는지 확인
def edge_exists(edge_ip):
    with open("hosts", "r") as f:
        hosts = f.read()
    return edge_ip in hosts

# 새로운 에지 장치를 호스트 파일에 추가
def add_edge_to_hosts(edge_ip, edge_name):
    print(f"Adding {edge_ip} to hosts")
    with open("hosts", "a") as f:
        f.write(f"{edge_ip} {edge_name}\n")

# 에지 장치를 감지하고 처리
def discover_edges():
    result = subprocess.run(
        ["avahi-browse", "-r", "_workstation._tcp", "--terminate"],
        capture_output=True,
        text=True
    )
    
    lines = result.stdout.splitlines()
    edge_info = {}
    edge_name = ''
    info = {}
    
    current_edge = None
    for line in lines:
        if "IPv4" in line:
            parts = line.split()
            #print(parts)
            if len(parts) > 3:
                current_edge = parts[3]  # 호스트 이름 추출
                #print('current_edge = ', current_edge)
                edge_info[current_edge] = {"name": current_edge}
        
        if "hostname" in line and current_edge:
            match = re.search(r"hostname = \[(.*?)\]", line)
            if match:
                #print('edge_info = ', edge_info)
                edge_info[current_edge]["hostname"] = match.group(1).split('.')[0]
        
        if "address" in line and current_edge:
            match = re.search(r"address = \[(.*?)\]", line)
            if match:
                #print('line = ', line)
                edge_info[current_edge]["ip"] = match.group(1)
    
    for edge_name, info in edge_info.items():
        edge_ip = ''
        print('info = ', info)
        if "ip" in info:
            edge_ip = info["ip"]
            #print('edge_ip = ', edge_ip)
            if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", edge_ip):
                if not edge_exists(edge_ip):
                    add_edge_to_hosts(edge_ip, info["hostname"])
                else:
                    print(f'[-] exist : {edge_name}, {edge_ip}')
            else:
                print(f"Invalid IP address: {edge_ip}")
        else:
            pass
            print(f"IP address for {edge_name} not found")

# 주기적으로 네트워크를 스캔합니다.
while True:
    print('-'*50)
    print('scanning now ...')
    print('-'*50)
    discover_edges()
    time.sleep(60)