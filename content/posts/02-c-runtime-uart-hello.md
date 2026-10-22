+++
title = "没有 main 之前：启动汇编、C 运行环境与串口 Hello World"
date = 2026-10-22T19:00:00+08:00
description = "从 QEMU virt 的 ELF 入口设置 gp、栈和 BSS，再进入 freestanding C main，通过 MMIO UART 输出。"
slug = "c-runtime-uart-hello"
tags = ["RISC-V", "QEMU", "裸机", "C 运行时"]
+++

> 本篇对应代码：`xueliangliang/riscv-hello` 的 `lesson-02` 标签，固定提交 `b9e44571cdf072dbbd35ecb56c3df048bc243b13`。请检出标签复现，不要用后来变化的 `main` 代替。

## 本篇要解决什么

第一课已经证明 QEMU 能进入我们链接在 `0x80000000` 的 `_start`，并且汇编可以直接写 UART。现在再回答一个问题：**C 函数开始运行之前，谁准备它依赖的环境？**

本篇只增加一层很薄的 freestanding C 运行环境：

1. 启动汇编设置 `gp` 和 `sp`；
2. 按 linker script 提供的范围清零 BSS；
3. 调用 C 的 `main`；
4. C 代码检查栈、BSS 和已初始化数据，再经轮询 UART 输出结果。

预期 guest 串口输出：

```text
Lesson 02: C main entered with a valid stack.
PASS: BSS was cleared and initialized data was preserved.
```

宿主测试脚本还会输出：

```text
PASS: C runtime, stack, BSS, initialized data, and UART verified.
```

这仍不是操作系统，也不是完整 libc。没有特权级切换、trap、中断、调度、文件系统或 `printf`；UART 驱动仍由 C 代码直接访问 QEMU 的 MMIO 地址。

## 实验环境

本篇沿用第一课实测的 Ubuntu 主机基线：

| 项目 | 实测版本/配置 |
|---|---|
| 主机 | x86-64，Ubuntu 26.04.1 LTS |
| Linux kernel | 7.0.0-38-generic |
| RISC-V GNU cross GCC | 15.2.0 |
| RISC-V GNU binutils | 2.46 |
| GNU Make | 4.4.1 |
| QEMU system emulator | 10.2.1 |
| GDB | 17.1（可选，本篇用来检查入口与 `main`） |
| 虚拟机 | QEMU `virt`，单 hart，128 MiB RAM，M-mode |
| 目标 ISA/ABI | `rv64imac_zicsr_zifencei` / `lp64`，不启用浮点扩展 |

安装与第一课相同的基础软件包：

```sh
sudo apt update
sudo apt install \
  make bash coreutils grep \
  gcc-riscv64-linux-gnu \
  binutils-riscv64-linux-gnu \
  qemu-system-misc

# 可选：使用 GDB 单步
sudo apt install gdb-multiarch
```

发行版包版本会随时间变化；表格记录的是本篇实际测试基线，不是对所有 Ubuntu 版本的承诺。第一课的环境和 ELF 背景见[上一篇](/posts/environment-and-first-entry/)。

## 取得这篇对应的代码

```sh
git clone https://github.com/xueliangliang/riscv-hello.git
cd riscv-hello
git checkout lesson-02
git rev-parse HEAD
```

最后一条命令应得到：

```text
b9e44571cdf072dbbd35ecb56c3df048bc243b13
```

这个仓库按课程累积实现。`lesson-02` 固定的是包含第一课和第二课的可运行状态；后续课程继续提交到 `main`，不会移动这个标签。

## 构建并检查 ELF

```sh
make clean all
make inspect
```

`make clean all` 会构建第一课和第二课。检查 `build/lesson02.elf` 时，重点看入口和三个 `PT_LOAD` 段：

```text
Entry point address: 0x80000000
LOAD  ... 0x0000000080000000 ... R E
LOAD  ... 0x0000000080001000 ... R
LOAD  ... 0x0000000080002000 ... RW
```

本次 GCC 15.2.0 构建中，最后一个段的 `FileSiz` 是 4 字节，而 `MemSiz` 是 `0x4020` 字节。前者包含已初始化数据；更大的内存范围还覆盖 BSS 和 16 KiB 栈。`.text`、只读数据和可写数据分开，ELF 没有把代码段标成 RWX。ELF 标志本身只是装载信息；这时还没有 PMP 或页表来强制运行时的 W^X 权限。

关键实现分布在：

- `lessons/02/start.S`：机器入口、`gp`/`sp` 初始化、BSS 清零和 `main` 调用；
- `lessons/02/linker.ld`：入口、段地址、BSS 范围和栈顶符号；
- `lessons/02/uart.c`：最小轮询 UART 驱动；
- `lessons/02/hello.c`：检查运行环境并打印验收行。

## 从 `_start` 到 `main`

QEMU `virt` 的 `-bios none` 并不表示 CPU 直接从我们写的 `_start` 开始；QEMU 仍通过内建的 reset stub 跳到 DRAM 中的 ELF 入口。第一课已用 GDB 验证入口是 `0x80000000`。第二课沿用这个入口，但入口函数现在要先满足 C ABI 的运行条件。

启动汇编的顺序是：

```text
_start
  ├─ gp = __global_pointer$
  ├─ sp = __stack_top
  ├─ [__bss_start, __bss_end) 写零
  └─ call main
```

`sp` 从 `__stack_top` 向低地址增长。BSS 里放的是未显式初始化的全局/静态对象；它们在 C 语义上应当从零开始。`start.S` 不依赖 ELF 装载器替我们完成这一约定，而是显式遍历 linker script 给出的范围。

`gp` 指向 linker script 中的 `__global_pointer$`。本课为简化代码生成使用 `-msmall-data-limit=0`，所以当前 C 代码不会依赖 small-data 区的 GP-relative 访问；仍在入口设置 `gp`，是为了把启动环境的职责讲清楚。`sp` 和 `gp` 是 ABI 约定的一部分，不是某个 C 编译器的临时偏好。

UART 驱动直接轮询 QEMU `virt` 的 16550-compatible UART0：基址 `0x10000000`，LSR 在偏移 5，`0x20` 表示发送保持寄存器可写，THR 在偏移 0。寄存器指针声明为 `volatile`，使每次状态读取和字符写入都保留为实际 MMIO 访问。换成真实板卡时，地址、UART 型号、时钟和 pinmux 都必须重新核实。

## 运行测试

```sh
make test-lesson02
```

测试除了检查 guest 输出，也会确认 ELF 是 RISC-V、入口与 `PT_LOAD` 地址正确，并等待 QEMU 经 test device 正常退出。运行在交互终端时，脚本用前台 timeout 并把 QEMU 的 stdin 接到 `/dev/null`，避免无输入测试被终端作业控制挂起。

第二课的 `main` 检查四件事：

- `bss_probe` 为零；
- 带初始值的全局变量仍等于 `0x4c4c3032`；
- C 函数的局部变量值正确；
- 读取到的 `sp` 位于 linker script 声明的栈范围内。

需要准确说明一个边界：QEMU 的 ELF 装载器也可能把 `PT_LOAD` 中 `MemSiz - FileSiz` 的部分初始化为零。因此，`bss_probe == 0` 单独不能证明零值一定来自 guest 的清零循环；循环本身在 `start.S` 中，GDB 可以直接检查它。这个测试验证整体启动后的可观察约定，不声称排除了模拟器装载器的参与。

## 用 GDB 看见运行环境建立的时刻

另开终端暂停 QEMU：

```sh
qemu-system-riscv64 \
  -machine virt -smp 1 -m 128M \
  -display none -serial null -monitor none \
  -bios none -kernel build/lesson02.elf \
  -S -gdb tcp::1234 -no-reboot
```

再连接：

```sh
gdb-multiarch build/lesson02.elf
```

在 GDB 中：

```gdb
target remote :1234
break _start
break main
continue
info registers pc sp gp
continue
info registers pc sp gp
```

本次实际断点观察到：

```text
_start: pc = 0x80000000, sp = 0, gp = 0
main:   pc = 0x80000116, sp = 0x80006000, gp = 0x80002800
```

第一个断点停在初始化之前，第二个断点停在 C 函数入口；此时 `sp` 和 `gp` 已由启动代码设置。结束后在 GDB 中 `detach`，再停止暂停的 QEMU。

## 验收与限制

通过条件：

- `readelf` 显示 RISC-V ELF、入口 `0x80000000` 和分离的 RX/R/RW 段；
- C `main` 检查栈、BSS、已初始化数据；
- `make test-lesson02` 捕获 guest UART 行并确认 QEMU 正常退出；
- GDB 能分别停在 `_start` 和 `main`，并观察到 `sp`/`gp` 的变化。

这里的 UART 地址只适用于 QEMU `virt`，不是 RISC-V 通用地址；系列总体范围与真机验证路线见[系列总览](/series/)。

## 代码版本

- 仓库：[`xueliangliang/riscv-hello`](https://github.com/xueliangliang/riscv-hello)
- 标签：`lesson-02`
- 提交：`b9e44571cdf072dbbd35ecb56c3df048bc243b13`

## 参考资料

- [RISC-V ELF psABI：整数寄存器与调用约定](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)
- [QEMU v10.2.1 RISC-V `virt` 机器文档](https://github.com/qemu/qemu/blob/v10.2.1/docs/system/riscv/virt.rst)
- [QEMU v10.2.1 `virt` 内存映射](https://github.com/qemu/qemu/blob/v10.2.1/hw/riscv/virt.c)
