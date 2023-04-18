#
# Copyright (C) 2022 Ing <https://github.com/wjz304>
# 
# This is free software, licensed under the MIT License.
# See /LICENSE for more information.
#

import os, re, sys, json, shutil, hashlib, subprocess, requests
from bs4 import BeautifulSoup

FILE_PATH = os.path.dirname(os.path.abspath(__file__))

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
        loads[model] = list(configs[model]["ramdisk"].keys())
    return loads


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
    pats = {}
    req = requests.get('https://prerelease.synology.cn/webapi/models?event=dsm72_beta')
    rels = json.loads(req.text)
    if "models" in rels and len(rels["models"]) > 0:
        for i in rels["models"]:
            if "name" not in i or "dsm" not in i: continue
            if i["name"] not in pats.keys(): pats[i["name"]]={}
            pats[i["name"]][__fullversion(i["dsm"]["version"])] = i["dsm"]["url"].split('?')[0]
    req = requests.get('https://archive.synology.cn/download/Os/DSM')
    req.encoding = 'utf-8'
    bs=BeautifulSoup(req.text, 'html.parser')
    p = re.compile(r"(.*?)-(.*?)", re.MULTILINE | re.DOTALL)
    l = bs.find_all('a', string=p)
    for i in l:
        ver = i.attrs['href'].split('/')[-1]
        if not any([ver.startswith('6.2.4'), ver.startswith('7')]): continue
        req = requests.get('https://archive.synology.cn{}'.format(i.attrs['href']))
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

    os.makedirs(os.path.join(CACHE_PATH, filepath))

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
        data["os"] = { "id": "{}_{}".format(synomodel, synoversion), "pat_url": url, "sha256": __sha256sum(os.path.join(CACHE_PATH, filename))}
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

def makeConfig(model, version, platform, junmode):
    config = {}

    synoarch = platform.split('-')[0]
    synokver = platform.split('-')[1]
    
    data, kver = synoextractor(model, version)

    if junmode:
        headstr = 'Yet Another Jun`s Mod x '
        rootidx = 2
        linuxkp = '/bzImage'
    else:
        headstr = ''
        rootidx = 1
        linuxkp = '/zImage'

    configs = {}
    with open(os.path.join(FILE_PATH, 'config/configs.json'), mode="r", encoding='utf-8') as f:
        configs = json.loads(f.read())

    config["os"] = data["os"]
    config["files"] = data["files"]
    config["patches"] = {"zlinux": [], "ramdisk": configs[model]["ramdisk"][version]}
    config["synoinfo"] = configs[model]["synoinfo"]
    config["grub"] = {}
    config["grub"]["template"] = "@@@COMMON@@@/grub-template.conf"
    config["grub"]["base_cmdline"] = configs[model]["base_cmdline"]
    config["grub"]["menu_entries"] = {
            "{}RedPill {} v{} (USB, Verbose)".format(headstr, model, version): {
                "options": [
                    "savedefault",
                    "set root=(hd0,{})".format(rootidx),
                    "echo Loading Linux...",
                    "linux {} @@@CMDLINE@@@".format(linuxkp),
                    "echo Starting kernel with USB boot"
                ],
                "cmdline": {
                    "console": "ttyS0,115200n8",
                    "earlyprintk": "",
                    "earlycon": "uart8250,io,0x3f8,115200n8",
                    "root": "/dev/md0",
                    "loglevel": 15,
                    "log_buf_len": "32M"
                }
            },
            "{}RedPill {} v{} (SATA, Verbose)".format(headstr, model, version): {
                "options": [
                    "savedefault",
                    "set root=(hd0,{})".format(rootidx),
                    "echo Loading Linux...",
                    "linux {} @@@CMDLINE@@@".format(linuxkp),
                    "echo Starting kernel with SATA boot",
                    "echo WARNING: SATA boot support on this platform is experimental!"
                ],
                "cmdline": {
                    "synoboot_satadom": "{}".format(configs[model]["satadom"]),
                    "console": "ttyS0,115200n8",
                    "earlyprintk": "",
                    "earlycon": "uart8250,io,0x3f8,115200n8",
                    "root": "/dev/md0",
                    "loglevel": 15,
                    "log_buf_len": "32M"
                }
            }
        }
    config["extra"] = {
        "compress_rd": False,
        "ramdisk_copy": {
            "@@@EXT@@@/rp-lkm/redpill-linux-v{}+.ko".format(synokver): "usr/lib/modules/rp.ko",
            "@@@COMMON@@@/iosched-trampoline.sh": "usr/sbin/modprobe"
        },
        "bootp1_copy": {
            "@@@PAT@@@/GRUB_VER": "GRUB_VER",
            "@@@COMMON@@@/EFI/boot/SynoBootLoader.conf": "EFI/BOOT/",
            "@@@COMMON@@@/EFI/boot/SynoBootLoader.efi": "EFI/BOOT/"
        },
        "bootp2_copy": {
            "@@@COMMON@@@/bzImage": "bzImage",
            "@@@PAT@@@/GRUB_VER": "GRUB_VER",
            "@@@COMMON@@@/EFI": "EFI",
            "@@@PAT@@@/grub_cksum.syno": "grub_cksum.syno",
            "@@@PAT@@@/rd.gz": "rd.gz",
            "@@@PAT@@@/zImage": "zImage"
        }
    }

    return config

if __name__ == '__main__':
    if len(sys.argv) != 5:
        print("eg: syno.py DS920+ 7.1.1-42962 1 geminilake-4.4.180 1")
        exit(1)
    
    model = sys.argv[1]
    version = sys.argv[2]
    platform = sys.argv[3]
    junmode = sys.argv[4]
    try:
        junmode = bool(int(junmode))
    except ValueError:
        junmode = bool(junmode)

    config = makeConfig(model, version, platform, junmode)

    os.makedirs(os.path.join(FILE_PATH, model, version))
    with open(os.path.join(FILE_PATH, 'config', model, version, 'config.json'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(config, indent=4))
