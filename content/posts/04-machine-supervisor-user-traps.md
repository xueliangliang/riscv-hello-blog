+++
title = "04. 从 M-mode 到 S-mode，再到 U-mode：让一次异常证明权限边界"
date = 2026-10-22T23:00:00+08:00
description = "延续磁盘启动链，用 mret/sret 进入用户态，通过 ecall、非法 CSR 访问、trap 上下文和 GDB 证明实际特权级。"
slug = "machine-supervisor-user-traps"
tags = ["RISC-V", "QEMU", "特权级", "trap"]
+++

> 本篇对应代码：`xueliangliang/riscv-hello` 的 `lesson-04` 标签，固定提交 `971f6126f0a1e324b1e3208dc53a9aa7392a935a`。前一课是[从磁盘加载 kernel 和 payload](/posts/virtio-bootloader-from-disk/)。

## 在屏幕上写“用户态”，不等于进入了用户态

前一课已经把 kernel 和第二个 payload 从磁盘搬到内存，但它们仍然运行在[机器模式（Machine mode，M-mode）](/terms/#m-mode)。如果只把函数改名为 `user_main`，或打印一行“entered user mode”，权限没有任何变化。

本篇让控制流实际经过[监管者模式（Supervisor mode，S-mode）](/terms/#s-mode)，再进入[用户模式（User mode，U-mode）](/terms/#u-mode)。但我们不只相信启动代码，而是设计三个能观察到的事件：

1. U-mode 执行 `ecall`，S-mode 收到来自用户态的环境调用异常，原因码为 8；
2. U-mode 故意读取 `sstatus`，收到非法指令异常，原因码为 2；
3. 处理异常后回到 U-mode，检查寄存器仍然正确，最后再通过 `ecall` 回到 S-mode 结束实验。

这里的[异常入口（trap）](/terms/#trap)不是普通函数调用。处理器会记录来源、原因和指令位置，再把执行权交给配置好的入口；保存通用寄存器和选择处理栈仍然是软件的责任。

## 复现：仍然从磁盘启动

环境沿用前课：Ubuntu x86-64、[GNU 编译器集合（GNU Compiler Collection，GCC）](/terms/#gcc)15.2.0、binutils 2.46、[QEMU（Quick Emulator，快速仿真器）](/terms/#qemu)10.2.1、Python 3.14.7，以及可选的 [GNU 调试器（GNU Debugger，GDB）](/terms/#gdb)17.1。交叉目标仍是 `rv64imac_zicsr_zifencei` / `lp64`；它们分别指定[指令集架构（Instruction Set Architecture，ISA）](/terms/#isa)和[应用二进制接口（Application Binary Interface，ABI）](/terms/#abi)。

首次安装可按[第 01 篇](/posts/environment-and-first-entry/)准备工具，生成磁盘镜像还需要 `python3`。从新目录获取代码：

```sh
git clone https://github.com/xueliangliang/riscv-hello.git
cd riscv-hello
git checkout lesson-04
git rev-parse HEAD
# 应为 971f6126f0a1e324b1e3208dc53a9aa7392a935a
make clean all
make inspect-lesson04
make test-lesson04
```

不要把本篇误读成“放弃了 bootloader，又用模拟器直接启动内核”。启动链仍然是：

```text
QEMU -kernel build/lesson03/bootloader.elf
    → 从 build/lesson04/disk.img 读启动记录
    → kernel 装到 0x80200000
    → user payload 装到 0x80400000
    → kernel 的 M 入口 → S-mode → U-mode
```

磁盘记录仍把第二个镜像叫作 `shell`，只是本课用这个槽位装 `user.bin`；它不是交互式 shell。磁盘位置仍由[逻辑块寻址（Logical Block Addressing，LBA）](/terms/#lba)表示。旧课代码、旧标签和磁盘格式都没有改。

## 先分清三种地址和两套栈

| 范围 | 本课用途 |
|---|---|
| `0x80000000` 起 | 旧 bootloader |
| `0x80200000` 起 | 新 kernel、启动代码、S-mode 栈及应急 M-mode 栈 |
| `[0x80400000, 0x80408000)` | 用户代码、只读数据、可写数据与 BSS 的链接范围 |
| `[0x80408000, 0x8040c000)` | 预留用户堆，第 05 课使用 |
| `[0x8040c000, 0x80410000)` | 16 KiB 用户栈，向低地址增长 |

[BSS（Block Started by Symbol，零初始化数据区）](/terms/#bss)和栈不需要把整片零字节存进磁盘。启动代码负责清理实际 BSS；链接脚本负责保留地址和检查边界。[可执行与可链接格式（Executable and Linkable Format，ELF）](/terms/#elf)的文件大小，与它运行时占用的内存范围不是一回事。

关键实现可以按顺序读：

- `lessons/04/start.S`：准备 M-mode 环境、下放异常、进入 S/U；
- `lessons/04/trap.S`：切换栈、保存与恢复上下文；
- `lessons/04/runtime.h`：C 与汇编共享的 trap frame 布局；
- `lessons/04/kernel.c`：按阶段验证原因、地址和寄存器；
- `lessons/04/user.S`：正常调用、非法访问和返回后的自检；
- `lessons/04/user.ld`：用户镜像与堆栈布局。

## M-mode 怎样把权限交给 S-mode

[控制与状态寄存器（Control and Status Register，CSR）](/terms/#csr)保存特权控制信息。`mepc` 决定 `mret` 返回到哪里；`mstatus.MPP`（Machine Previous Privilege）决定返回到哪个权限级。它不是把某个 C 函数的地址强转后调用，而是明确准备状态，再执行架构定义的特权返回。

本课 M 入口依次做以下事情：

1. 设置栈并清零 kernel BSS，安装应急 M trap 入口；
2. 配置[物理内存保护（Physical Memory Protection，PMP）](/terms/#pmp)，允许 S/U 访问当前实验使用的地址；
3. 将 `medeleg` 的第 2、8 位设为 1，即 `0x104`，把非法指令和 U-mode `ecall` 异常委托给 S-mode；
4. 关闭中断，令 `satp=0`，使用不经过页表转换的 Bare 地址模式；
5. 设置 `mepc=supervisor_main`、MPP=S，执行 `mret`。

“委托”不表示把所有异常都交给 S。比如 S-mode 的 `ecall` 原因码是 9，本课没有委托它；未委托异常仍会进入 M-mode 的应急处理路径。

也不能仅凭“关了 SIE”就认为用户态不会被中断。更低权限运行时，中断使能的规则不同；本课还把 `sie` 清零，并且不配置定时器，从而把观察范围限定为同步异常。

## S-mode 再把执行权交给 U-mode

进入 S-mode 后，先把 `stvec` 设置为 `supervisor_trap`，采用直接入口；再准备：

- `sepc=0x80400000`：用户入口；
- `sstatus.SPP=0`（Supervisor Previous Privilege）：`sret` 的目标是 U-mode；
- `sp=0x80410000`：用户[栈指针（stack pointer，sp）](/terms/#sp)；
- `sscratch`：进入异常时可取回的 S-mode 栈顶。

然后执行 `sret`。至此用户代码真正以 U-mode 开始执行。

注意 `sepc` 只是目标地址，不是权限。把它设成用户函数地址但保留 SPP=1，运行的仍然会是 S-mode。

## trap 发生时，硬件没有替我们压好整个现场

异常到来时，硬件把原因放进 `scause`，把发生异常的指令地址放进 `sepc`，并在 `sstatus.SPP` 记录之前的权限级。它不会自动把所有整数寄存器压栈，也不会自动替用户换成可信的内核栈。

本课入口的关键动作是用 `csrrw sp, sscratch, sp` 交换栈指针：来自 U-mode 时，换到事先保存的 S 栈，同时保留原 U 栈指针。随后建立 288 字节、16 字节对齐的 trap frame，保存 31 个可写整数寄存器和 `sepc/sstatus/scause/stval`，再把 frame 地址传给 C handler。

为什么连临时寄存器也要保存？普通 C 调用约定允许被调用函数破坏一些寄存器，但异常可以发生在用户指令序列中间；用户没有主动同意把这些值交给另一个 C 函数覆盖。处理程序必须先保存现场，才能自由调用 C。

本课还约定：运行在 S-mode 的 handler 内时，`sscratch=0`。如果此时发生同步 S-mode 异常，入口不把零当成栈使用，C handler 会根据 SPP 拒绝这个非预期来源。这是有明确失败路径的单 hart 实验入口，不是支持任意嵌套的通用异常运行时。

## 用一次不能执行的指令证明权限

用户程序第一次 `ecall` 前在 `t0/t1/s1/a3` 放入哨兵值。S handler 检查它们，并把返回值 `a0` 改为 42。返回后，用户代码检查 `a0` 和其余哨兵。

接着它执行 `csrr t0, sstatus`。这个 CSR 要求 S 级或更高权限；U-mode 读取应产生非法指令异常。收到 cause=2、SPP=0，并核对 `sepc` 正是这条指令，比打印一句“现在是用户态”更有说服力。

本课有意让这几条探针指令都使用 `.option norvc`，每条占 4 字节，所以已确认的异常可用 `sepc += 4` 跳过，再执行 `sret`。不能把这个写法照搬成“任意异常统一加 4”：RISC-V 可有压缩指令，未知异常也不应一律忽略。

正常 guest 的关键输出是：

```text
Lesson 04: supervisor entered after mret.
trap: scause=0x0000000000000008 sepc=0x0000000080400010 SPP=0
trap: scause=0x0000000000000002 sepc=0x0000000080400020 SPP=0
trap: scause=0x0000000000000008 sepc=0x0000000080400030 SPP=0
PASS: M -> S -> U, ecall, CSR fault, context, S recovery.
```

前面还会有旧 bootloader 的三行装载输出。最后一次 `ecall` 在 S-mode 结束实验，并不是让用户代码执行关机用的特权指令。

## 不只测成功：原因错和位置错都应该失败

`make test-lesson04` 实际启动三次 QEMU：

| 镜像 | 变化 | 预期 |
|---|---|---|
| `disk.img` | 正常探针 | 完整输出匹配，退出码 0 |
| `disk-bad-cause.img` | 把 CSR 读取改成 `ecall` | cause 变成 8，报告 `FAIL: unexpected scause`，退出码 1 |
| `disk-bad-pc.img` | 在 CSR 读取前插入 `nop` | 地址变为 `0x80400024`，报告 `FAIL: unexpected sepc`，退出码 1 |

这些 `FAIL` 是负向用例期待的 guest 输出，不表示宿主测试失败。宿主 `tests/run-privilege.py` 核对整段有序文本和退出码；缺行、多行、输出被截断或 10 秒超时都不能算通过。每次运行的原始输出保存在 `build/lesson04/*.img.log`。

也可以回归全部已完成课程，并检查[伪终端（Pseudoterminal，PTY）](/terms/#pty)环境：

```sh
make test
script -q -e -c 'make test' build/pty.log
```

## 用 GDB 看实际 privilege，而不只看文字

第一个终端从仓库根目录启动：

```sh
qemu-system-riscv64 \
  -machine virt -global virtio-mmio.force-legacy=false \
  -smp 1 -m 128M -display none -serial stdio -monitor none \
  -bios none -kernel build/lesson03/bootloader.elf \
  -drive file=build/lesson04/disk.img,if=none,format=raw,id=disk,readonly=on \
  -device virtio-blk-device,drive=disk -S -gdb tcp::1234
```

另一个终端运行 `gdb-multiarch build/lesson04/kernel.elf`，输入：

```gdb
target remote :1234
add-symbol-file build/lesson04/user.elf
hbreak supervisor_main
continue
p/x $priv
hbreak *0x80400010
continue
p/x $priv
hbreak supervisor_trap
continue
info registers scause sepc sstatus sscratch sp
p/x $priv
continue
```

本次实测依次看到 `priv=1`、`priv=0`、trap 入口的 `priv=1`；前两次 trap 分别是 `cause=8, epc=0x80400010` 和 `cause=2, epc=0x80400020`，SPP 都为零。`$priv` 的可见性依赖 QEMU/GDB；原因码、SPP 和非法 CSR 访问行为才是架构层面的证据。

用 `hbreak` 是因为初始连接时后续镜像尚未从磁盘装进内存，软件断点可能被后来的装载覆盖。进入 handler 的第一条指令前，`sscratch` 还是 S 栈顶；执行交换之后才变成原用户 `sp`，检查时别把两个时刻混起来。

## 本课真正建立的是指令权限，不是内存隔离

这点直接影响如何理解实验：本课 PMP 故意允许全地址读、写、执行，没有页表。用户态不能合法读 `sstatus`，但恶意用户代码仍可能直接改内核内存，或访问通用异步收发器（Universal Asynchronous Receiver-Transmitter，UART）的[内存映射 I/O（Memory-Mapped I/O，MMIO）](/terms/#mmio)。因此它证明了特权指令边界和异常往返，不是安全沙箱。

下一篇在这个入口上建立真正可调用的接口：[syscall、mini-libc 与最小堆](/posts/syscall-mini-libc-heap/)。整个系列进度见[总览](/series/)。

## 参考资料

- [RISC-V Machine-Level ISA：特权返回、委托与 PMP](https://docs.riscv.org/reference/isa/v20260120/priv/machine.html)
- [RISC-V Supervisor-Level ISA：SPP、sscratch、sepc、scause](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html)
- [RISC-V CSR 地址编码和访问权限](https://docs.riscv.org/reference/isa/v20260120/priv/priv-csrs.html)
- [RISC-V ELF psABI：调用约定与栈对齐](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)
