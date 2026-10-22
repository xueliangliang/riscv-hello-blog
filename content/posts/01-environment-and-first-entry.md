+++
title = "一条命令背后：搭建 RISC-V 实验环境，并进入第一条指令"
date = 2026-10-22T00:00:00+08:00
description = "用 Ubuntu 交叉工具链和 QEMU virt，从 ELF 入口进入 RISC-V M-mode，并输出第一行 UART。"
slug = "environment-and-first-entry"
tags = ["RISC-V", "QEMU", "裸机"]
+++

> 本篇对应代码：`xueliangliang/riscv-hello` 的 `lesson-01` 标签。复现时请检出该标签，而不是盲目跟随后续变化的 `main`。

## 这篇要得到什么

我们先不写操作系统，也不假装已经有 `main`、C 运行库或 shell。本篇只完成一个很小但可验证的闭环：

1. 在 x86-64 Ubuntu 主机上用交叉工具链构建 64 位 RISC-V [可执行与可链接格式（Executable and Linkable Format，ELF）](/terms/#elf)文件；
2. 从 ELF 头和程序段里确认目标架构、入口地址与加载地址；
3. 用 [QEMU（Quick Emulator，快速仿真器）](/terms/#qemu) 的 RISC-V `virt` 虚拟板加载这个 ELF；
4. 从 `_start` 轮询[通用异步收发器（Universal Asynchronous Receiver-Transmitter，UART）](/terms/#uart)，输出一行文字，再让 QEMU 正常结束。

预期串口输出：

```text
Lesson 01: RISC-V entry reached.
PASS: RISC-V ELF entry and UART output verified.
```

最后一行由宿主测试脚本输出；第一行才是 guest 里执行的汇编写到 UART 的内容。

本课的结论只覆盖 `lesson-01` ELF 在当前 QEMU virt 配置下的入口和串口验收。整个系列的进度与硬件验证范围统一见[系列总览](/series/)。

## 实验环境

本篇实测环境记录如下：

| 项目 | 实测版本/配置 |
|---|---|
| 主机 | x86-64，Ubuntu 26.04.1 [LTS（Long-Term Support，长期支持）](/terms/#lts)（Resolute Raccoon） |
| Linux kernel | 7.0.0-38-generic |
| RISC-V GNU [Compiler Collection（GCC）](/terms/#gcc) cross compiler | 15.2.0 (`gcc-riscv64-linux-gnu` 4:15.2.0-5ubuntu1) |
| RISC-V GNU binutils | 2.46 (`binutils-riscv64-linux-gnu` 2.46-3ubuntu2) |
| GNU Make | 4.4.1 (`make` 4.4.1-3) |
| QEMU system emulator | 10.2.1 (`qemu-system-misc` 1:10.2.1+ds-1ubuntu3.2) |
| GDB | [GNU 调试器（GNU Debugger，GDB）](/terms/#gdb) 17.1（可选） |
| 虚拟机 | QEMU `virt`，单 hart，128 MiB [随机存取存储器（Random-Access Memory，RAM）](/terms/#ram)，[机器模式（Machine mode，M-mode）](/terms/#m-mode) 入口 |
| 目标 [指令集架构（Instruction Set Architecture，ISA）](/terms/#isa) / [应用二进制接口（Application Binary Interface，ABI）](/terms/#abi) | `rv64imac_zicsr_zifencei` / `lp64`；不用浮点扩展 |

版本记录的目的，是让读者和读者的 coding agent 能区分“本篇实际验证过的环境”与“理论上也许可用的环境”。本机使用 `python3` 是可选的辅助工具，本篇 Makefile 和 QEMU 测试不依赖 Python。

## 安装软件

以下是本篇实测机器使用的最小 Ubuntu 包集合。`qemu-system-misc` 提供 RISC-V system emulator；cross GCC 和 binutils 负责生成、链接和检查目标文件；`make` 驱动构建，`bash/coreutils/grep` 被自动化测试脚本使用。这个汇编实验不需要宿主机的 native GCC 或 libc development headers，因而 `build-essential` 不是必需依赖。

```sh
sudo apt update
sudo apt install \
  make \
  bash \
  coreutils \
  grep \
  gcc-riscv64-linux-gnu \
  binutils-riscv64-linux-gnu \
  qemu-system-misc

# 可选：只有想在第一课用 GDB 单步时才需要
sudo apt install gdb-multiarch

# 仅当后续章节需要在宿主机编译普通 C 工具时才需要
sudo apt install build-essential
```

检查必需程序是否在 PATH：

```sh
riscv64-linux-gnu-gcc --version
riscv64-linux-gnu-ld --version
riscv64-linux-gnu-objcopy --version
riscv64-linux-gnu-readelf --version
qemu-system-riscv64 --version
```

可选 GDB：

```sh
gdb-multiarch --version
```

记录 Ubuntu 包的完整修订号（方便 agent 区分同一 upstream 版本的发行版补丁）：

```sh
uname -srmo
dpkg-query -W -f='${binary:Package} ${Version}\n' \
  make gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu qemu-system-misc
```

Ubuntu 的包版本会随发行版更新。不要把上面的本机版本号抄成所有 Ubuntu 版本都必然安装相同版本的承诺；文章记录的是作者实际测试基线。本文测试过的是 Ubuntu 26.04.1 LTS；其他发行版/版本应重新执行下面的构建和 QEMU 测试，不能只根据包名推断已验证。

Ubuntu 官方包目录可核对本文用到的 [`gcc-riscv64-linux-gnu`](https://packages.ubuntu.com/resolute/gcc-riscv64-linux-gnu)、[`binutils-riscv64-linux-gnu`](https://packages.ubuntu.com/resolute/binutils-riscv64-linux-gnu)、[`qemu-system-misc`](https://packages.ubuntu.com/resolute/qemu-system-misc)、[`gdb-multiarch`](https://packages.ubuntu.com/resolute/gdb-multiarch) 和可选的 [`build-essential`](https://packages.ubuntu.com/resolute/build-essential)。QEMU 官方 RISC-V system 文档说明 64 位模拟器命令为 `qemu-system-riscv64`，并将 `virt` 描述为通用虚拟平台，而不是某一块实体板。

## 取得对应代码

代码和文章分仓库。新代码仓库从空历史开始，逐步加入每课所需文件；旧原型仓库只作为查阅资料，不复制其复杂实现来冒充第一课。

若从 GitHub 获取：

```sh
git clone https://github.com/xueliangliang/riscv-hello.git
cd riscv-hello
git checkout lesson-01
```

本篇对应代码标签是 `lesson-01`，固定在提交 `2dd2519298a68c6ca55bf87193505f2cea870c3b`。后续课程会继续累积在 `main`；这个标签不随 `main` 前进而改变。检出标签时 Git 会提示进入 detached HEAD，这是只读复现实验的正常状态；若要在此基础上修改，先运行 `git switch -c my-lesson-01-experiment`。作者本机的代码目录是 `~/riscv-hello-clean`；读者应使用前面的 clone 命令和仓库内相对路径，不需要复用作者的本地目录名。

## 构建：宿主机 GCC 与目标 GCC 不是一回事

本课 Makefile 使用：

```text
riscv64-linux-gnu-gcc
```

而不是宿主机的 `gcc`。目标三元组表示生成的 ELF 面向 RISC-V 64 位 Linux ABI 工具链；本课又显式使用 `-nostdlib`，所以不会链接 Linux libc 或启动文件。生成物是一个非常小的裸机程序，不是 Linux 用户进程。

执行：

```sh
make clean all
```

关键目标参数：

```text
-march=rv64imac_zicsr_zifencei
-mabi=lp64
-mcmodel=medany
-ffreestanding -fno-builtin -fno-pic
-nostdlib -static
```

大意是：目标为 RV64IMAC（加 Zicsr/Zifencei），采用整数 LP64 ABI，代码使用适合该链接地址的 medany 模型，不假设有 hosted C 库；最终不链接标准启动代码或 libc。本课源文件是汇编，`gcc` 主要用来调用匹配的 assembler/linker driver。

## 读 ELF，不要只看“命令成功”

```sh
make inspect
```

重点检查：

- `Machine` 应该是 RISC-V；
- Entry point 应为 `0x80000000`；
- 有可加载的 ELF 程序段类型 [`PT_LOAD`](/terms/#pt_load)，地址从 `0x80000000` 开始；
- `.text.init` 中 `_start` 是第一段要执行的代码；
- `.rodata` 里有串口输出字符串；
- ELF 带符号和调试信息，适合 `readelf`/`objdump`/GDB 检查。

Makefile 也生成 `build/lesson01.bin`：

```sh
riscv64-linux-gnu-objcopy -O binary build/lesson01.elf build/lesson01.bin
```

ELF 有机器架构、入口地址和程序段等元数据；raw binary 基本只是按规则抽出的字节，不自带这些信息。本篇把 ELF 交给 QEMU `-kernel`，保留可检查的入口/段信息。raw binary 暂时只用来展示格式区别，不拿它直接启动，以免引入额外 loader 地址参数。

## 运行：QEMU `virt` 不是一块实体开发板

```sh
make test
```

本课执行的核心命令等价于：

```sh
qemu-system-riscv64 \
  -machine virt -smp 1 -m 128M \
  -display none -serial stdio -monitor none \
  -bios none \
  -kernel build/lesson01.elf \
  -no-reboot
```

`virt` 是 QEMU 提供的虚拟硬件模型，不是某一款真实板卡。QEMU 官方说明 `-bios none` 不加载外置固件；机器仍有内建 reset [只读存储器（Read-Only Memory，ROM）](/terms/#rom)。QEMU v10.2.1 的 RISC-V reset stub 在 `0x1000` 取出启动地址并跳转；本配置的[动态随机存取存储器（Dynamic Random-Access Memory，DRAM）](/terms/#dram)起始地址和 ELF 入口均为 `0x80000000`。我们用 GDB 实测在 `_start` 命中[程序计数器（Program Counter，PC）](/terms/#pc)值 `0x80000000`。这个 stub 属于模拟器启动机制，不是本课自己写的固件。代码从 M-mode `_start` 执行，不代表它已能从任意芯片 reset vector 启动。QEMU `virt` 提供兼容 16550 的 UART 和 SiFive test device；本课直接用它们做最小输出和自动退出。参考 v10.2.1 的 [`virt.c` 内存映射](https://github.com/qemu/qemu/blob/v10.2.1/hw/riscv/virt.c)、[reset stub](https://github.com/qemu/qemu/blob/v10.2.1/hw/riscv/boot.c) 和 [SiFive test device](https://github.com/qemu/qemu/blob/v10.2.1/hw/misc/sifive_test.c)。

Makefile 自动化测试会确认 ELF 架构/入口、捕获 UART 文本、检查 guest test-device 正常退出。执行 `make test` 后应看到：

```text
Lesson 01: RISC-V entry reached.
PASS: RISC-V ELF entry and UART output verified.
```

如果 QEMU 缺失或输出/退出状态不对，测试会失败，不会把“编译通过”算作实验通过。

## 代码逐步做了什么

`start.S` 的 `_start` 使用 PC-relative `la` 找到字符串，用 `0x10000000` 作为本课固定的 QEMU virt UART0 地址，然后轮询 UART 的[线路状态寄存器（Line Status Register，LSR）](/terms/#lsr)中的 transmit-holding-register-empty 位。只有发送器可接收时才写[发送保持寄存器（Transmit Holding Register，THR）](/terms/#thr)；写完整个字符串后，把通过码写到 `0x00100000` 的 QEMU test device，使自动化测试能够正常结束。

`linker.ld` 把 ELF 的单个 RX `PT_LOAD` 程序段放到 `0x80000000`，并把入口符号设为 `_start`。本课只包含汇编入口和串口输出；下一课会加入栈/[BSS（Block Started by Symbol，零初始化数据区）](/terms/#bss)初始化、分离的 ELF 段和 C `main`。

这些地址和 UART 寄存器行为来自 QEMU `virt` 平台，不是 RISC-V ISA 对所有开发板规定的通用地址。后续换真实板时必须重新核对该板的内存映射、UART 类型、时钟与 pinmux，不能把 `0x10000000` 写死为 RISC-V 通用常量。

## 可选：用 GDB 在入口停下

另开终端启动暂停的 QEMU：

```sh
qemu-system-riscv64 \
  -machine virt -smp 1 -m 128M \
  -display none -serial stdio -monitor none \
  -bios none -kernel build/lesson01.elf \
  -S -gdb tcp::1234
```

再开一个终端：

```sh
gdb-multiarch build/lesson01.elf
```

GDB 中输入：

```gdb
target remote :1234
break _start
continue
x/8i $pc
info registers pc a0 a1
```

此时可以看到[中央处理器（Central Processing Unit，CPU）](/terms/#cpu)到达 `_start` 的 ELF 地址。退出 GDB 后用 Ctrl-C 结束被暂停的 QEMU。

## 本课验收

完成条件：

- 所需工具都能报告版本；
- 从干净构建 `make clean all` 成功；
- `readelf` 确认 RISC-V ELF、入口 `0x80000000` 和从同一地址开始的可加载段；
- `make test` 捕获到 guest 串口输出并正常退出；
- 知道输出来自 guest 汇编，而不是宿主脚本伪造的文字。

下一课在这个入口上设置栈、清零 BSS 并进入 C `main`：[第 02 课](/posts/c-runtime-uart-hello/)。

## 代码版本

- 代码仓库：`https://github.com/xueliangliang/riscv-hello`
- 对应标签：`lesson-01`
- 对应提交：`2dd2519298a68c6ca55bf87193505f2cea870c3b`

## 官方参考

- [Ubuntu Resolute `gcc-riscv64-linux-gnu` 包](https://packages.ubuntu.com/resolute/gcc-riscv64-linux-gnu)
- [Ubuntu Resolute `binutils-riscv64-linux-gnu` 包](https://packages.ubuntu.com/resolute/binutils-riscv64-linux-gnu)
- [Ubuntu Resolute `qemu-system-misc` 包](https://packages.ubuntu.com/resolute/qemu-system-misc)
- [Ubuntu Resolute `gdb-multiarch` 包](https://packages.ubuntu.com/resolute/gdb-multiarch)
- [QEMU v10.2.1 RISC-V system emulator documentation source](https://github.com/qemu/qemu/blob/v10.2.1/docs/system/target-riscv.rst)
- [QEMU v10.2.1 `virt.c` memory map](https://github.com/qemu/qemu/blob/v10.2.1/hw/riscv/virt.c)
- [QEMU v10.2.1 generated RISC-V reset vector](https://github.com/qemu/qemu/blob/v10.2.1/hw/riscv/boot.c)
- [QEMU v10.2.1 SiFive test-device behavior](https://github.com/qemu/qemu/blob/v10.2.1/hw/misc/sifive_test.c)
