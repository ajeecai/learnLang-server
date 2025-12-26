import os
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import subprocess

load_dotenv()

# 设置代理（如有）
http_proxy = os.getenv("HTTP_PROXY", "")
if http_proxy:
    os.environ["HTTP_PROXY"] = http_proxy
    os.environ["HTTPS_PROXY"] = http_proxy

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def get_installed_cuda_version():
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        match = re.search(r"CUDA Version: (\d+\.\d+)", result.stdout)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"[Error] Failed to run nvidia-smi: {e}")
    return None

def fetch_pytorch_versions():
    # https://pytorch.org/get-started/locally/
    url = "https://pytorch.org/get-started/previous-versions/"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        print(f'soup: {soup}')
        table = soup.find("table")

        if not table:
            print("[Error] PyTorch versions table not found on page.")
            with open("pytorch_page_debug.html", "w") as f:
                f.write(response.text)
            return {}

        rows = table.find_all("tr")[1:]  # skip header

        version_map = {}
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 4:
                torch = cols[0].text.strip()
                torchvision = cols[1].text.strip()
                torchaudio = cols[2].text.strip()
                cuda = cols[3].text.strip()
                if "cu" in cuda:
                    version_map[cuda] = {
                        "torch": torch,
                        "torchvision": torchvision,
                        "torchaudio": torchaudio,
                    }
        return version_map
    except Exception as e:
        print(f"[Error] Failed to fetch PyTorch versions: {e}")
        return {}

def fetch_cudnn_links():
    cudnn_url = "https://developer.nvidia.com/rdp/cudnn-archive"
    try:
        response = requests.get(cudnn_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a", href=True)
        cudnn_links = {}
        for link in links:
            href = link["href"]
            text = link.get_text(strip=True)
            match = re.search(r"cuDNN (\d+(?:\.\d+)+) for CUDA (\d+\.\d+)", text)
            if match:
                version = match.group(1)
                cuda = match.group(2)
                cudnn_links[cuda] = {
                    "version": version,
                    "url": f"https://developer.nvidia.com{href}"
                }
        return cudnn_links
    except Exception as e:
        print(f"[Error] Failed to fetch cuDNN links: {e}")
        return {}

# 主执行逻辑
cuda_version = get_installed_cuda_version()
if not cuda_version:
    print("[Error] Could not detect CUDA version.")
    exit(1)

print(f"[Info] Detected CUDA version: {cuda_version}")

pytorch_versions = fetch_pytorch_versions()
cudnn_versions = fetch_cudnn_links()

cuda_key = f"cu{cuda_version.replace('.', '')}"
if cuda_key in pytorch_versions:
    versions = pytorch_versions[cuda_key]
    print(f"[PyTorch] torch=={versions['torch']}+{cuda_key}")
    print(f"[PyTorch] torchvision=={versions['torchvision']}+{cuda_key}")
    print(f"[PyTorch] torchaudio=={versions['torchaudio']}+{cuda_key}")
else:
    print("[Warning] No matching PyTorch versions found.")

if cuda_version in cudnn_versions:
    cudnn = cudnn_versions[cuda_version]
    print(f"[cuDNN] version: {cudnn['version']}")
    print(f"[cuDNN] download link: {cudnn['url']}")
else:
    print("[Warning] No cuDNN links found for this CUDA version.")
