# AthenaWrt — 京东云雅典娜 AX6600 定制固件

基于 **ImmortalWrt** 为 **京东云雅典娜 AX6600（JDCloud RE-CS-02）** 定制的路由器固件。

> 目标平台：Qualcomm **IPQ6010**（4×A53 @1.8GHz）· 1GB DDR4 · eMMC · 三频 Wi-Fi 6 · 1×2.5G + 4×1G

---

## 一、硬件规格（本固件适配机型）

| 项目 | 参数 |
|------|------|
| 商品名 | 京东云无线宝 AX6600 雅典娜 |
| 型号 | RE-CS-02 |
| SoC | Qualcomm IPQ6010（4 核 A53，1.8GHz） |
| 内存 | 1GB DDR4 |
| 存储 | eMMC（64G / 128G / 256G 均可） |
| 无线 | QCN9024（5.2G，HE160，4×4）+ QCN5052（5.8G，2×2）+ QCN5022（2.4G，2×2） |
| 网口 | 1× 2.5G（WAN）+ 4× 1G（LAN） |
| 交换 | QCA8075 / QCA8081 |
| USB | 1× USB 3.0 |
| OpenWrt 目标 | `qualcommax/ipq60xx`，设备 `jdcloud_re-cs-02` |

---

## 二、固件特性（开箱即用）

- **LuCI 中文界面** + Argon 现代主题 + 主题配置
- **PassWall2** 科学上网（Xray / Sing-Box / SS / SSR / Trojan / Hysteria 等）
- **AdGuard Home + SmartDNS** 去广告与 DNS 分流
- **Docker + Dockerman** 容器管理
- **AList** 网盘聚合挂载
- **Samba 文件共享** + 磁盘管理（128G eMMC / USB3.0 存储）
- **DDNS**（阿里云 / 腾讯云 DNSPod / Cloudflare 等）
- **WireGuard / OpenVPN / Tailscale** 组网与 VPN
- **MWAN3 多线负载 + SQM QoS** 流量整形
- **UPnP / 网络唤醒 / 带宽监控 / vnStat2**
- **BBR + fq_codel** 网络性能调优，针对 2.5G 口优化内核参数

### 默认账号密码

| 项目 | 默认值 |
|------|--------|
| 管理地址 | `192.168.10.1` |
| 用户名 | `root` |
| 密码 | `password`（**首次登录请立即修改**） |
| SSH | 22 端口（密码登录） |
| 2.4G SSID | `Athena-2.4G` |
| 5.2G SSID | `Athena-5G-Game`（QCN9074 游戏频段） |
| 5.8G SSID | `Athena-5G` |
| Wi-Fi 密码 | `12345678` |

---

## 三、目录结构

```
athena-openwrt/
├── configs/
│   ├── jdcloud_re-cs-02.seed    # 种子配置（目标平台 + 品牌）
│   └── packages.list            # 精选插件清单
├── files/                       # 固件覆盖层
│   └── etc/
│       ├── uci-defaults/99-athena-custom.sh   # 首启配置（主机名/时区/密码/无线）
│       └── sysctl.d/99-athena-tune.conf       # 内核网络调优
├── scripts/
│   ├── setup.sh                 # 初始化（clone + feeds + defconfig）
│   └── build.sh                 # 编译
└── docs/
    ├── 刷机教程.md
    └── 固件特性.md
```

---

## 四、如何编译

### 方式 A：本地 / 虚拟机编译（本工程即为此准备）

需要 Linux（推荐 Debian/Ubuntu 22.04），≥8GB 内存、≥40GB 磁盘、AMD64。

```bash
# 1. 安装编译依赖（Ubuntu/Debian）
sudo apt update
sudo apt install -y build-essential clang flex bison g++ gawk gcc-multilib \
  g++-multilib gettext git libncurses-dev libssl-dev python3-setuptools \
  rsync swig unzip zlib1g-dev file wget libelf-dev device-tree-compiler \
  zstd cpio xz-utils bzip2 zip time diffstat pkg-config autoconf automake \
  libtool help2man intltool python3-dev python3-pip libsqlite3-dev uuid-dev

# 2. 初始化（克隆 ImmortalWrt + feeds + 生成 .config）
bash scripts/setup.sh

# 3. 编译（2~4 小时）
bash scripts/build.sh
```

产物位于 `immortalwrt/bin/targets/qualcommax/ipq60xx/`：
- `...-factory.bin` — 用于 U-Boot Web 刷入
- `...-sysupgrade.bin` — 用于系统内升级

### 方式 B：GitHub Actions 云编译（免本地环境）

本工程可直接改造为云编译（见社区 `ones20250/Openwrt-AX6600` 等同类项目），将 `scripts/setup.sh`、`scripts/build.sh` 接入 workflow 即可。

---

## 五、刷机

**⚠️ 刷机有变砖风险，务必先备份原厂分区再操作。** 完整步骤见 [docs/刷机教程.md](docs/刷机教程.md)。

核心流程：**开 telnet/SSH → 备份 → 刷不死 U-Boot → 刷 GPT 大分区 → 刷 factory 固件**。

---

## 六、免责声明

本固件基于开源项目 [ImmortalWrt](https://github.com/immortalwrt/immortalwrt) 定制，仅供学习研究。刷机操作可能导致设备变砖，请自行承担风险，并遵守当地法律法规。
