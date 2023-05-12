#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
# 
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import os, re, sys, json, shutil, hashlib, subprocess, requests
from bs4 import BeautifulSoup


FILE_PATH = os.path.dirname(os.path.abspath(__file__))

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Referer': 'https://archive.synology.com/download/Os/DSM/',
    'Accept-Language': 'en-US,en;q=0.5'
}

def __fullversion(ver):
    out = ver
    arr = ver.split('-')
    if len(arr) > 0:
        a = arr[0].split('.')[0] if len(arr[0].split('.')) > 0 else '0'
        b = arr[0].split('.')[1] if len(arr[0].split('.')) > 1 else '0'
        c = arr[0].split('.')[2] if len(arr[0].split('.')) > 2 else '0'
        d = arr[1] if len(arr) > 1 else '00000'
        e = arr[2] if len(arr) > 2 else '0'
        out = '{}.{}.{}-{}-{}'.format(a,b,c,d,e)
    return out

def __sha256sum(file):
    sha256Obj = ''
    if os.path.isfile(file):
        with open(file, "rb") as f:
            sha256Obj = hashlib.sha256(f.read()).hexdigest()
    return sha256Obj

def __md5sum(file):
    md5Obj = ''
    if os.path.isfile(file):
        with open(file, "rb") as f:
            md5Obj = hashlib.md5(f.read()).hexdigest()
    return md5Obj


def getThisLoads():
    loads = {}
    configs = {}
    with open(os.path.join(FILE_PATH, 'config/configs.json'), mode="r", encoding='utf-8') as f:
        configs = json.loads(f.read())
    for model in configs.keys():
        loads[model] = list(configs[model]["platforms"].keys())
    return loads

def getDTmodels(isDT = True):
    dts = []
    configs = {}
    with open(os.path.join(FILE_PATH, 'config/configs.json'), mode="r", encoding='utf-8') as f:
        configs = json.loads(f.read())
    for model in configs.keys():
        if configs[model]["dt"] == isDT:
            dts.append(model)
    return dts

def getSynoModels():
    models=[]
    req = requests.get('https://kb.synology.com/en-us/DSM/tutorial/What_kind_of_CPU_does_my_NAS_have')
    req.encoding = 'utf-8'
    bs=BeautifulSoup(req.text, 'html.parser')
    p = re.compile(r"data: (.*?),$", re.MULTILINE | re.DOTALL)
    data = json.loads(p.search(bs.find('script', string=p).prettify()).group(1))
    model='(.*?)'  # (.*?): all, FS6400: one
    p = re.compile(r"\n\t\t\t<td>{}<\/td>\n\t\t\t<td>(.*?)<\/td>\n\t\t\t<td>(.*?)<\/td>\n\t\t\t<td>(.*?)<\/td>\n\t\t\t<td>(.*?)<\/td>\n\t\t\t<td>(.*?)<\/td>\n\t\t\t<td>(.*?)<\/td>\n\t\t".format(model), re.MULTILINE | re.DOTALL)
    it = p.finditer(data["preload"]["content"])
    for i in it:
        d = i.groups()
        if len(d) == 6: d = model + d
        models.append({"Model":d[0],"CPU Model":d[1],"Cores":d[2],"Threads":d[3],"FPU":d[4],"PackageArch":d[5].lower(),"RAM":d[6]})
    return models


def getSynoPATs():
    # 临时对策, RC 64551 目前并没有在 archive.synology.com 上线, beta 又为 64216, 临时用 64216 的地址进行替换.
    pats = {}
    req = requests.get('https://prerelease.synology.com/webapi/models?event=dsm72_beta', headers=headers)
    rels = json.loads(req.text)
    if "models" in rels and len(rels["models"]) > 0:
        for i in rels["models"]:
            if "name" not in i or "dsm" not in i: continue
            # if i["name"] not in models: continue
            if i["name"] not in pats.keys(): pats[i["name"]]={}
            pats[i["name"]][__fullversion(i["dsm"]["version"]).replace('64216','64551')] = i["dsm"]["url"].split('?')[0].replace('beta','release').replace('64216','64551')

    req = requests.get('https://archive.synology.com/download/Os/DSM', headers=headers)
    req.encoding = 'utf-8'
    bs=BeautifulSoup(req.text, 'html.parser')
    p = re.compile(r"(.*?)-(.*?)", re.MULTILINE | re.DOTALL)
    l = bs.find_all('a', string=p)
    for i in l:
        ver = i.attrs['href'].split('/')[-1]
        if not any([ver.startswith('6.2.4'), ver.startswith('7')]): continue
        req = requests.get('https://archive.synology.com{}'.format(i.attrs['href']), headers=headers)
        req.encoding = 'utf-8'
        bs=BeautifulSoup(req.text, 'html.parser')
        p = re.compile(r"^(.*?)_(.*?)_(.*?).pat$", re.MULTILINE | re.DOTALL)
        data = bs.find_all('a', string=p)
        for item in data:
            p = re.compile(r"DSM_(.*?)_(.*?).pat", re.MULTILINE | re.DOTALL)
            rels = p.search(item.attrs['href'])
            if rels != None:
                info = p.search(item.attrs['href']).groups()
                model = info[0].replace('%2B', '+')
                if model not in pats.keys(): pats[model]={}
                pats[model][__fullversion(ver)] = item.attrs['href']
    
    return pats


def getpaturl(model, version):
    pats = {}
    if os.path.exists(os.path.join(FILE_PATH, 'config/pats.json')):
        with open(os.path.join(FILE_PATH, 'config/pats.json'), 'r') as f:
            pats = json.load(f)
    else:
        pats = getSynoPATs()

    tmp = '0.0.0-00000-0'
    url = ''
    if model in pats.keys():
        for item in pats[model]:
            if version.split('-')[1] not in item: continue
            if item > tmp: tmp, url = item, pats[model][item]
    return url

def synoextractor(model, version, isclean = False):

    CACHE_PATH = os.path.join(FILE_PATH, 'cache')

    data={}
    kver=''

    synomodel = model.lower().replace('+','p')
    synoversion = version.split('-')[1]

    url = getpaturl(model, version)

    filename = '{}_{}.pat'.format(synomodel, synoversion)
    filepath = '{}_{}'.format(synomodel, synoversion)

    commands = ['sudo', 'rm', '-rf', os.path.join(CACHE_PATH, filepath), os.path.join(CACHE_PATH, filename)]
    result = subprocess.check_output(commands)
    
    #req = requests.get(url.replace(urlparse(url).netloc, 'cndl.synology.cn'))
    req = requests.get(url)

    with open(os.path.join(CACHE_PATH, filename), "wb") as f:
        f.write(req.content)
    filehash = __md5sum(os.path.join(CACHE_PATH, filename))

    # Get the first two bytes of the file and extract the third byte
    output = subprocess.check_output(["od", "-bcN2", os.path.join(CACHE_PATH, filename)])
    header = output.decode().splitlines()[0].split()[2]

    if header == '105':
        # print("Uncompressed tar")
        isencrypted = False
    elif header == '213':
        # print("Compressed tar")
        isencrypted = False
    elif header == '255':
        # print("Encrypted")
        isencrypted = True
    else:
        # print("error")
        return data

    os.makedirs(os.path.join(CACHE_PATH, filepath), exist_ok=True)

    if isencrypted is True:
        TOOL_PATH = os.path.join(FILE_PATH, 'ext/extractor')
        if os.path.exists(TOOL_PATH):
            commands = ["sudo", "LD_LIBRARY_PATH={}".format(TOOL_PATH), "{}/syno_extract_system_patch".format(TOOL_PATH), os.path.join(CACHE_PATH, filename), os.path.join(CACHE_PATH, filepath)] 
            result = subprocess.check_output(commands)
        else:
            if not os.path.exists("syno-extractor.sh"):
                req = requests.get('https://raw.githubusercontent.com/wjz304/redpill-load/main/ext/extractor/extractor.sh')
                with open("extractor.sh", "wb") as f: f.write(req.content)
            commands = ["sudo", "chmod", "+x", "extractor.sh"] 
            result = subprocess.check_output(commands)
            commands = ["sudo", "extractor.sh", os.path.join(CACHE_PATH, filename), os.path.join(CACHE_PATH, filepath)] 
            result = subprocess.check_output(commands)
        commands = ['sudo', 'rm', '-f', os.path.join(CACHE_PATH, filename)]
        result = subprocess.check_output(commands)
        commands = ['sudo', 'tar', '-czf', os.path.join(CACHE_PATH, filename), "-C", os.path.join(CACHE_PATH, filepath), ".", "--warning=no-file-changed"]
        result = subprocess.check_output(commands)
    else:
        commands = ['tar', '-xf', os.path.join(CACHE_PATH, filename), '-C', os.path.join(CACHE_PATH, filepath)]
        result = subprocess.check_output(commands)


    if os.path.exists(os.path.join(CACHE_PATH, filename)): 
        data["os"] = { "id": "{}_{}".format(synomodel, synoversion), "pat_url": url, "sha256": __sha256sum(os.path.join(CACHE_PATH, filename)), "hash": filehash }
        data["files"] = {"vmlinux": {"sha256": ""}}
        if os.path.exists(os.path.join(CACHE_PATH, filepath, "rd.gz")): 
            data["files"]["ramdisk"] = {"name": "rd.gz", "sha256": __sha256sum(os.path.join(CACHE_PATH, filepath, "rd.gz"))}
        if os.path.exists(os.path.join(CACHE_PATH, filepath, "zImage")): 
            data["files"]["zlinux"] = {"name": "zImage", "sha256": __sha256sum(os.path.join(CACHE_PATH, filepath, "zImage"))}
            
            commands = ['file', os.path.join(CACHE_PATH, filepath, "zImage")]
            result = subprocess.check_output(commands)
            kver = result.decode('utf-8').split()[8].replace('+','')

    commands = ['sudo', 'rm', '-rf', os.path.join(CACHE_PATH, filepath)]
    if isclean: commands.append(os.path.join(CACHE_PATH, filename))
    result = subprocess.check_output(commands)
    
    return data, kver

def makeConfig(model, version, junmode):
    config = {}
    
    configs = {}
    with open(os.path.join(FILE_PATH, 'config/configs.json'), mode="r", encoding='utf-8') as f:
        configs = json.loads(f.read())

    data, patkver = synoextractor(model, version)

    cmdline = {
        "console": "ttyS0,115200n8",
        "earlyprintk": "",
        "earlycon": "uart8250,io,0x3f8,115200n8",
        "root": "/dev/md0",
        "loglevel": 15,
        "log_buf_len": "32M"
    }

    bootp2_copy = {
        "@@@PAT@@@/GRUB_VER": "GRUB_VER",
        "@@@COMMON@@@/EFI": "EFI",
        "@@@PAT@@@/grub_cksum.syno": "grub_cksum.syno",
        "@@@PAT@@@/rd.gz": "rd.gz",
        "@@@PAT@@@/zImage": "zImage"
    }

    cfgkver = configs[model]["platforms"][version].split('-')[1]

    if junmode:
        headstr = 'Yet Another Jun`s Mod x '
        bootp2_copy = dict(**{"@@@COMMON@@@/bzImage": "bzImage"}, **bootp2_copy)
    else:
        headstr = ''
        bootp2_copy = dict(**{}, **bootp2_copy)

    def __options(junmode, startup):
        if junmode:
            return [
                    "savedefault",
                    "set root=(hd0,2)",
                    "set cmdline=\"@@@CMDLINE@@@\"",
                    "echo cmdline:",
                    "echo ${cmdline}",
                    "echo .",
                    "echo Loading Linux...",
                    "linux /bzImage ${cmdline}",
                    "echo Starting kernel with {} boot".format(startup),
                    "echo Access http://find.synology.com/ to connect the DSM via web."
                ]
        else:
            return [
                    "savedefault",
                    "set root=(hd0,1)",
                    "set cmdline=\"@@@CMDLINE@@@\"",
                    "echo cmdline:",
                    "echo ${cmdline}",
                    "echo .",
                    "echo Loading Linux...",
                    "linux /zImage ${cmdline}",
                    "echo Loading initramfs...",
                    "initrd /rd.gz /custom.gz",
                    "echo Starting kernel with {} boot".format(startup),
                    "echo Access http://find.synology.com/ to connect the DSM via web."
                ]   

    config["os"] = data["os"]
    config["files"] = data["files"]
    config["patches"] = {"zlinux": [], "ramdisk": configs[model]["ramdisk"][version]}
    config["synoinfo"] = configs[model]["synoinfo"]
    config["grub"] = {}
    config["grub"]["template"] = "@@@COMMON@@@/grub-template.conf"
    config["grub"]["base_cmdline"] = configs[model]["base_cmdline"]
    config["grub"]["menu_entries"] = {
            "{}RedPill {} v{} (USB, Verbose)".format(headstr, model, version): {
                "options": __options(junmode, 'USB'),
                "cmdline": cmdline
            },
            "{}RedPill {} v{} (SATA, Verbose)".format(headstr, model, version): {
                "options": __options(junmode, 'SATA'),
                "cmdline": dict(**{"synoboot_satadom": configs[model]["satadom"]}, **cmdline)
            }
        }
    config["extra"] = {
        "compress_rd": False,
        "ramdisk_copy": {
            "@@@EXT@@@/rp-lkm/redpill-linux-v{}+.ko".format(cfgkver): "usr/lib/modules/rp.ko",
            "@@@COMMON@@@/iosched-trampoline.sh": "usr/sbin/modprobe"
        },
        "bootp1_copy": {
            "@@@PAT@@@/GRUB_VER": "GRUB_VER",
            "@@@COMMON@@@/EFI/boot/SynoBootLoader.conf": "EFI/BOOT/",
            "@@@COMMON@@@/EFI/boot/SynoBootLoader.efi": "EFI/BOOT/"
        },
        "bootp2_copy": bootp2_copy
    }

    return config

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("eg: syno.py DS920+ 7.1.1-42962 1")
        exit(1)
    
    model = sys.argv[1]
    version = sys.argv[2]
    junmode = sys.argv[3]

    try:
        junmode = bool(int(junmode))
    except ValueError:
        junmode = bool(junmode)

    config = makeConfig(model, version, junmode)

    os.makedirs(os.path.join(FILE_PATH, 'config', model, version), exist_ok=True)
    with open(os.path.join(FILE_PATH, 'config', model, version, 'config.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(config, indent=4))
