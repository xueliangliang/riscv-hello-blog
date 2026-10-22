+++
title = "内核不必由模拟器直接装好：从 virtio 磁盘加载 kernel 和 shell"
date = 2026-10-22T19:10:00+08:00
description = "在 QEMU virt 上实现最小 modern virtio-mmio 块设备轮询，用启动记录把 kernel 与 shell payload 从 LBA 搬到 RAM，再验证跳转。"
slug = "virtio-bootloader-from-disk"
tags = ["RISC-V", "QEMU", "bootloader", "virtio"]
+++

> 本篇对应代码：`xueliangliang/riscv-hello` 的 `lesson-03` 标签，固定提交 `dec100abc65349d3806129671aea917c7c8613e2`。它包含前两课的累计代码；复现时请检出该标签。

## 为什么还要自己读盘

前两课把一个[可执行与可链接格式（Executable and Linkable Format，ELF）](/terms/#elf)文件交给[QEMU（Quick Emulator，快速仿真器）](/terms/#qemu) 的 `-kernel`，由模拟器把它加载到内存。实际系统的启动链通常还需要代码从某种存储设备找到后续镜像、搬到[随机存取存储器（Random-Access Memory，RAM）](/terms/#ram)，再把控制权交出去。

本篇让 QEMU 继续负责加载**第一阶段 bootloader ELF**，但 kernel 和 shell payload 不再由 `-kernel` 加载：它们被放进一张 raw 磁盘镜像，bootloader 通过 [Virtual I/O Device（VIRTIO，虚拟 I/O 设备接口）](/terms/#virtio)读取，再交给 kernel。磁盘位置用[逻辑块寻址（Logical Block Addressing，LBA）](/terms/#lba)编号。启动链变为：

```text
QEMU reset stub
    ↓
0x80000000 的 bootloader ELF
    ↓ 读取磁盘 LBA 0 的启动记录
    ↓ virtio-blk 读取 kernel 和 shell payload
RAM 0x80200000 / 0x80400000
    ↓
kernel entry → shell payload
```

这里的 “shell payload” 只是一个单独链接的 C 函数，用于证明第二个镜像也确实来自磁盘并能执行；它不是交互式命令行 shell。真正的 shell 留到后续课程。

## 环境与依赖

本篇实测基线与前两课相同，另外需要 Python 3 的标准库来生成磁盘镜像：

| 项目 | 实测版本/配置 |
|---|---|
| 主机 | x86-64，Ubuntu 26.04.1 [LTS（Long-Term Support，长期支持）](/terms/#lts) |
| Linux kernel | 7.0.0-38-generic |
| RISC-V GNU [Compiler Collection（GCC）](/terms/#gcc) cross compiler | 15.2.0 |
| RISC-V GNU binutils | 2.46 |
| GNU Make | 4.4.1 |
| QEMU system emulator | 10.2.1 |
| Python | 3.14.7，仅用标准库 |
| [GNU 调试器（GNU Debugger，GDB）](/terms/#gdb) | 17.1，可选，用于检查 LBA、RAM 地址和跳转 |
| 虚拟机 | QEMU `virt`，单 hart，128 MiB RAM，[机器模式（Machine mode，M-mode）](/terms/#m-mode) |
| [指令集架构（Instruction Set Architecture，ISA）](/terms/#isa) / [应用二进制接口（Application Binary Interface，ABI）](/terms/#abi) | `rv64imac_zicsr_zifencei` / `lp64`，不启用浮点扩展 |

安装依赖：

```sh
sudo apt update
sudo apt install \
  make bash coreutils grep python3 \
  gcc-riscv64-linux-gnu \
  binutils-riscv64-linux-gnu \
  qemu-system-misc

# 可选：跟踪 bootloader 和 kernel 之间的跳转
sudo apt install gdb-multiarch
```

这些是作者实测的版本基线，不代表其他 Ubuntu 版本一定带有相同发行版修订号。

## 取得对应代码并构建

```sh
git clone https://github.com/xueliangliang/riscv-hello.git
cd riscv-hello
git checkout lesson-03
git rev-parse HEAD
```

最后一条应得到：

```text
dec100abc65349d3806129671aea917c7c8613e2
```

构建并查看 ELF：

```sh
make clean all
make inspect
```

本次构建的入口地址为：

| 文件 | ELF entry | 用途 |
|---|---:|---|
| `build/lesson03/bootloader.elf` | `0x80000000` | QEMU `-kernel` 加载的第一阶段 |
| `build/lesson03/kernel.elf` | `0x80200000` | bootloader 从磁盘读入的 kernel |
| `build/lesson03/shell.elf` | `0x80400000` | 从磁盘读入、由 kernel 调用的 shell payload |

磁盘里放的是后两个 ELF 经 `objcopy -O binary` 得到的 raw 字节；raw binary 不带 ELF 入口和程序段元数据，所以启动记录会携带固定的加载地址和入口地址。

## 磁盘和 RAM 地图

镜像是一个专用 raw 文件，不包含分区表或文件系统：

| 磁盘范围 | 内容 | 本次构建的实测大小 |
|---|---|---:|
| LBA 0 | 80 字节启动记录，其余填零 | 512 字节扇区 |
| LBA 1–9 | kernel raw image | 4360 字节，9 个扇区 |
| LBA 10–18 | shell raw payload | 4312 字节，9 个扇区 |
| 合计 | 1 个记录扇区 + 18 个镜像扇区 | 9728 字节 |

RAM 中的三个固定位置：

```text
0x80000000  bootloader ELF，由 QEMU -kernel 装载
0x80200000  kernel，bootloader 从 LBA 1 装载
0x80400000  shell payload，bootloader 从 LBA 10 装载
```

镜像生成器 `tools/make-disk-image.py` 使用 little-endian 格式写启动记录。布局是 `8s + 2×u32 + 8×u64 = 80` 字节，包含 magic、版本、记录大小、kernel 的 LBA/字节数/加载地址/入口，以及 shell 的同一组字段。启动记录没有[循环冗余校验（Cyclic Redundancy Check，CRC）](/terms/#crc)；bootloader 会检查 magic、版本、字段范围、固定 RAM 地址、镜像扇区是否连续，以及这些扇区是否超出设备容量。

加载地址刻意固定在 kernel 和 shell 的链接地址。bootloader 读取每个镜像覆盖的完整扇区，最后一个扇区的 padding 不属于逻辑文件大小；kernel 自己的入口会清理 [BSS（Block Started by Symbol，零初始化数据区）](/terms/#bss)。

## 为什么需要选择 modern VirtIO transport

本课 driver 实现的是 VirtIO Version 2 transport。[内存映射 I/O（Memory-Mapped I/O，MMIO）](/terms/#mmio)把设备寄存器映射到地址空间；本课使用的 VirtIO MMIO transport 通常称为 virtio-mmio。driver 扫描 QEMU `virt` 的设备窗口，匹配 magic/version/block device ID，协商 `VIRTIO_F_VERSION_1`，配置一个 8-entry split virtqueue，然后轮询完成状态。

QEMU 的 virtio-mmio transport 在本地配置下默认会暴露 legacy Version 1。作者用 GDB 直接读取 MMIO 寄存器时，未加参数看到设备版本为 1，因此测试命令显式使用：

```sh
-global virtio-mmio.force-legacy=false
```

这让 QEMU 暴露现代 transport；省略它时，本课 driver 会按设计拒绝版本不匹配的设备，而不是继续用错误协议读盘。这个参数是本课 QEMU 虚拟平台的配置，不是所有硬件 bootloader 的通用选项。

每次读一个 512 字节 sector，driver 提交三段描述符：

1. 设备读取的请求头：`type = VIRTIO_BLK_T_IN` 和 sector 编号；
2. 设备写入 guest RAM 的 512 字节数据缓冲区；
3. 设备写回的请求状态字节。

[中央处理器（Central Processing Unit，CPU）](/terms/#cpu)把描述符链放入 available ring，执行内存 fence，更新 ring index 并通知 queue 0；之后轮询 used ring，检查完成项和状态码。没有中断，也没有并行队列。两张 payload 共 18 个 sector，超过 8 项 queue 的长度，因此这次运行也实际经过了队列 ring 回绕。

## 运行正常和错误路径

```sh
make test-lesson03
```

测试脚本生成正常镜像和一个只破坏 magic 的镜像。正常路径的关键输出：

```text
Lesson 03: M-mode bootloader started.
Boot record validated; loading kernel and shell from disk.
Bootloader: both images loaded; jumping to kernel at 0x80200000.
Kernel: entered from the virtio block image.
Shell payload: loaded from disk and called by the kernel.
PASS: boot record, kernel/shell reads, and handoff verified.
```

然后脚本用坏 magic 的镜像再次启动，预期看到：

```text
ERROR: boot record magic does not match.
PASS: disk boot handoff works and a bad boot record is rejected.
```

第一段 `PASS` 是 guest kernel 输出；最后一段由宿主脚本在确认坏镜像以预期原因被拒绝后输出。QEMU 以非零状态结束坏镜像运行是这个负向测试的预期结果。

直接 QEMU 命令等价于：

```sh
qemu-system-riscv64 \
  -machine virt \
  -global virtio-mmio.force-legacy=false \
  -smp 1 -m 128M \
  -display none -serial stdio -monitor none \
  -bios none \
  -kernel build/lesson03/bootloader.elf \
  -drive file=build/lesson03/disk.img,if=none,format=raw,id=lesson_disk,readonly=on \
  -device virtio-blk-device,drive=lesson_disk \
  -no-reboot
```

注意：QEMU 的 `-kernel` 只负责把 bootloader ELF 放到 RAM。kernel 和 shell 的输出证明 guest driver 从只读磁盘设备读取了它们，再由 kernel 调用了 shell payload；不是 QEMU 直接装载了这两个镜像。

## 用 GDB 对照 LBA、RAM 地址和控制流

暂停运行：

```sh
qemu-system-riscv64 \
  -machine virt -global virtio-mmio.force-legacy=false \
  -smp 1 -m 128M -display none -serial null -monitor none \
  -bios none -kernel build/lesson03/bootloader.elf \
  -drive file=build/lesson03/disk.img,if=none,format=raw,id=lesson_disk,readonly=on \
  -device virtio-blk-device,drive=lesson_disk \
  -S -gdb tcp::1234 -no-reboot
```

另开终端：

```sh
gdb-multiarch build/lesson03/bootloader.elf
```

用 `break load_image` 停在两次装载调用，再继续到 kernel 入口：

```gdb
target remote :1234
break load_image
break *0x80200000
continue
info registers a0 a1 a2
continue
info registers a0 a1 a2
continue
info registers pc
```

本次实测的三个断点分别显示；最后一行的[程序计数器（Program Counter，PC）](/terms/#pc)用于确认 kernel 收到控制权时的入口地址：

```text
kernel: a0/LBA=1,  a1/bytes=4360, a2/destination=0x80200000
shell:  a0/LBA=10, a1/bytes=4312, a2/destination=0x80400000
kernel entry: PC=0x80200000
```

这把启动记录中的字段、磁盘扇区、RAM 目标和最后的 PC 连成一条可检查的数据流。

## 验收与边界

本篇实际验证了：

- 第一阶段从 ELF 入口 `0x80000000` 启动；
- QEMU modern virtio-mmio 的版本/设备识别、`VIRTIO_F_VERSION_1` 协商、queue 配置和轮询读完成；
- 18 个 sector 的两张 payload 被分别放到 linker script 指定的 RAM 地址；
- kernel 接手后调用磁盘中的 shell payload；
- 损坏的启动记录 magic 被拒绝；
- [伪终端（Pseudoterminal，PTY）](/terms/#pty)下完整 `make test` 不挂起。

这不是生产级 bootloader：它只支持本课固定布局、固定地址和 QEMU virtio-mmio；没有分区表、文件系统、校验和、重定位、超时恢复或中断驱动，也没有进入[监管者模式（Supervisor mode，S-mode）](/terms/#s-mode)/[用户模式（User mode，U-mode）](/terms/#u-mode)。启动记录边界错误、virtio 初始化错误等拒绝分支存在于实现中，但本篇自动化负向测试只专门验证了坏 magic。

## 代码版本

- 仓库：[`xueliangliang/riscv-hello`](https://github.com/xueliangliang/riscv-hello)
- 标签：`lesson-03`
- 提交：`dec100abc65349d3806129671aea917c7c8613e2`

## 参考资料

- [QEMU v10.2.1 RISC-V `virt` 机器文档](https://github.com/qemu/qemu/blob/v10.2.1/docs/system/riscv/virt.rst)
- [QEMU v10.2.1 virtio-mmio transport 实现](https://github.com/qemu/qemu/blob/v10.2.1/hw/virtio/virtio-mmio.c)
- [QEMU v10.2.1 virtio-mmio 寄存器定义](https://github.com/qemu/qemu/blob/v10.2.1/include/standard-headers/linux/virtio_mmio.h)
- [OASIS Virtio Specification 1.2](https://docs.oasis-open.org/virtio/virtio/v1.2/virtio-v1.2.html)
- [RISC-V ELF psABI：整数寄存器与调用约定](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)
