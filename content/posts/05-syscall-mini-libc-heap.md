+++
title = "05. 给应用一套最小接口：syscall、mini-libc 与 heap"
date = 2026-10-22T23:01:00+08:00
description = "让用户 C 程序通过明确的系统调用 ABI 输出和退出，实现必要的字符串/内存函数，再验证一个 16 KiB 有界堆的对齐、溢出和耗尽。"
slug = "syscall-mini-libc-heap"
tags = ["RISC-V", "QEMU", "syscall", "C 运行时"]
+++

> 本篇对应代码：`xueliangliang/riscv-hello` 的 `lesson-05` 标签，固定提交 `587cbe7656bca52b569e86c7eabc8aac95e91e12`。上一课是[特权级切换与异常往返](/posts/machine-supervisor-user-traps/)。

## 从“能够返回”到“能够请求服务”

上一课已经让用户代码经异常进入内核，再回到用户态。但那还只是约定好的几次探针：第一个调用检查寄存器，第二个故意触发非法指令，最后一个结束实验。

现在把它改成一套可调用、可拒绝、可测试的接口：[系统调用（system call，syscall）](/terms/#syscall)。[用户模式（User mode，U-mode）](/terms/#u-mode)中的 C 程序不再直接调用串口驱动，而是把请求号与参数放入寄存器，用 `ecall` 进入[监管者模式（Supervisor mode，S-mode）](/terms/#s-mode)。内核检查请求、执行服务、返回结果。

本篇同时补上两个容易混淆的东西：

- mini-libc：在用户态运行的少量字符串、内存操作和 syscall 包装；
- [堆（heap）与 bump allocator](/terms/#heap)：用户镜像内部一块 16 KiB 的顺序分配区。

不是每个 C 函数都要进入内核，分配一小块已经属于自己的内存，也不一定需要系统调用。

## 固定版本，复现整个路径

环境仍是 Ubuntu x86-64、[GNU 编译器集合（GNU Compiler Collection，GCC）](/terms/#gcc)15.2.0、binutils 2.46、[QEMU（Quick Emulator，快速仿真器）](/terms/#qemu)10.2.1 和 Python 3.14.7。可选的 [GNU 调试器（GNU Debugger，GDB）](/terms/#gdb)17.1 用于检查寄存器。工具安装见[第 01 篇](/posts/environment-and-first-entry/)；继续使用同一交叉目标 `rv64imac_zicsr_zifencei` / `lp64`，不开启浮点扩展。

```sh
git clone https://github.com/xueliangliang/riscv-hello.git
cd riscv-hello
git checkout lesson-05
git rev-parse HEAD
# 应为 587cbe7656bca52b569e86c7eabc8aac95e91e12
make clean all
make inspect-lesson05
make test-lesson05
```

如果已经有前课仓库，先确认没有本地改动，再 `git fetch --tags` 和检出 `lesson-05` 即可。

bootloader 和磁盘格式仍复用第 03 课，M/S 切换与 trap 汇编复用第 04 课。本课没有把用户程序偷偷重新链接进内核：`build/lesson05/kernel.bin` 和 `user.bin` 分别进入磁盘的两个 payload 槽，装载到 `0x80200000` 和 `0x80400000`。

代码阅读顺序：

| 文件 | 要回答的问题 |
|---|---|
| `lessons/05/abi.h` | 请求号、错误码和长度上限是什么？ |
| `lessons/05/user-start.S` | 谁清用户 BSS？C 调用参数怎样变成 syscall 参数？ |
| `lessons/05/kernel.c` | 谁验证请求？怎样返回结果？ |
| `lessons/05/libc.c` / `libc.h` | 哪些工作留在用户态？堆怎样检查边界？ |
| `lessons/05/user.c` | 怎样从用户侧验证返回值、拒绝路径和分配语义？ |

[BSS（Block Started by Symbol，零初始化数据区）](/terms/#bss)不在 raw 镜像里占满零字节；本课用户启动代码显式清理它，再调用 `user_main`。宿主的标准 C 库没有被链接进 guest。

## 先把 ABI 写下来，别让两边各猜各的

[应用二进制接口（Application Binary Interface，ABI）](/terms/#abi)不只包括普通 C 函数调用，也包括我们在用户程序和内核之间约定的寄存器格式。这里定义的是本课程自己的 syscall ABI，不兼容 Linux，也不是监管者二进制接口（Supervisor Binary Interface，SBI）。

约定如下：

| 寄存器 | 含义 |
|---|---|
| `a7` | 系统调用编号 |
| `a0..a5` | 参数，本篇只使用前两个 |
| 返回时的 `a0` | 有符号 64 位结果 |

| 编号 | 操作 | 输入 | 输出 |
|---|---|---|---|
| 1 | console write | `a0=地址, a1=字节数` | 写入长度；非法地址 `-14`，长度过大 `-22` |
| 2 | exit | `a0=状态` | 不返回 |
| 其他 | 未支持的请求 | 忽略 | `-38` |

这些数值虽然使用常见错误码含义，本课并没有实现全局 `errno` 或完整的标准库错误处理。

`syscall(number, arg0, arg1)` 本身先按普通 C ABI 收到 `a0/a1/a2`，因此汇编包装要先搬到 `a7/a0/a1`，再执行 `ecall`。若漏了这一步，内核看到的请求号和参数就会错位。

所有正常调用共用 `0x8040001c` 这一条 32 位 `ecall`。S handler 每次都检查异常原因码 8、来源标志 Supervisor Previous Privilege（SPP）为零和这个确切的 `sepc` 地址，再分发请求；返回时把结果写入 trap frame 中的 `a0`，将 `sepc` 前进 4 字节，由共享汇编恢复寄存器并 `sret`。

固定 PC 检查是本课的探针约束，帮助发现错误跳转；不是“一个成熟内核只能允许某个地址发 syscall”。后续若允许多个调用点，需要调整这个策略，不能机械保留单点白名单。

## 内核为什么不能直接相信一个指针

`write` 的字节来自用户地址。直接把寄存器值强转成 `char *` 并逐字节读取，会把“用户给了任意数值”变成“内核替它访问这个地址”。

本课先定义一份简单、明确的合同，再实现检查：

1. 长度超过 256 字节，返回 `-22`，不访问数据；
2. 地址必须位于闭区间 `[0x80400000, 0x80410000]`；
3. 地址检查通过后，再比较 `length <= end - pointer`，避免 `pointer + length` 溢出；
4. 全部验证完成之后才开始输出，失败不输出前半截。

零长度也要定义，而不能留给偶然实现决定：本课允许范围内地址及尾端地址的零长度写入，但 `NULL, 0` 仍返回非法地址。尾端地址搭配非零长度也被拒绝。

用户测试覆盖：空指针、起点之前、尾端非零读取、跨越尾端、接近整数最大值的地址、257 字节和最大长度、两个端点的零长度，以及未知调用号。

不过，这只是接口边界检查，不是内存安全隔离。本课使用平坦内存，物理内存保护（Physical Memory Protection，PMP）仍是全地址放行；恶意 U-mode 代码可以绕过 syscall，直接读写内核或设备。本课也没有实现遇到缺页时可恢复的用户数据复制。范围验证的教学价值是先把服务合同讲清楚，而不是宣布沙箱已经安全。

## mini-libc：哪些函数不需要 trap

本篇实现三个普通用户态函数：

- `strlen`：找到结尾零字节，返回此前的字节数；
- `memcpy`：复制指定字节数，要求源和目标不重叠；
- `memset`：用参数的低 8 位填充目标范围。

这些函数只操作用户程序已经持有的内存，不需要内核参与。`mini_write` 则是系统调用包装，`mini_exit` 是不返回的退出包装；如果 `user_main` 正常返回，启动代码会把返回值交给 `mini_exit`。

“mini-libc”不是“把宿主 libc 拷过去”。这里没有完整 `printf`、文件流、区域设置或标准 `malloc/free` 合同，也不声称完整实现 ISO C 库。尤其 `memcpy` 不是 `memmove`：重叠复制不属于它的使用合同。

## 堆先做最小，但失败语义不能含糊

链接脚本预留：

```text
0x80408000 ── heap start
             16 KiB 用户堆
0x8040c000 ── heap end / stack bottom
             16 KiB 用户栈，向低地址增长
0x80410000 ── stack top
```

`mini_alloc(size)` 只是移动用户态的 `heap_next`，不发 syscall，也不扩展物理内存：

- 返回地址按 16 字节对齐；请求 1 字节实际消耗 16，请求 17 消耗 32；
- 请求零字节返回空指针，不消耗空间；
- 先检查 `size > SIZE_MAX - 15`，再向上对齐，防止加法回绕；
- 对齐后的大小不能超过 `heap_end - heap_next`；
- 失败返回空指针，不移动当前分配位置；分配成功的内容不保证初始化。

为了把语义限制在本课能解释和验证的范围内，它没有 `free`、合并空洞、`realloc` 或向内核申请新页。空间一旦发出，本次运行期间不回收；新一轮启动清理用户 BSS 后重新开始。

测试不只检查返回值非空。它先发送零大小、回绕和超容量请求，再确认第一次有效分配仍位于堆起点；接着检查精确地址、对齐和分配之间的哨兵，最后恰好吃完剩余空间，要求后续请求稳定失败。这能发现“失败时偷偷推进了指针”一类问题。

堆的容量和栈的容量是两个独立预算。把二者画在链接图中，不代表硬件会阻止栈越界；本课没有栈保护页。

## 完整输出，以及故意失败的两次启动

正常启动前面仍有 bootloader 的三行输出，之后应看到：

```text
Lesson 05: supervisor ready for syscall ABI.
trap: scause=0x0000000000000008 sepc=0x000000008040001c SPP=0
user: hello via syscall.
user: write bounds and unknown syscall rejected.
user: libc, aligned heap, overflow and exhaustion verified.
user: exiting.
PASS: user exit(0) recovered to supervisor.
```

这里第一行 trap 只打印一次，但原因、来源和 PC 检查会在每次系统调用时执行，不是只检查首次进入。

`make test-lesson05` 还会启动两个真实负向镜像：

| 镜像 | 做什么 | 预期 |
|---|---|---|
| `disk-bad-exit.img` | 完成用户自检后返回 7 | `FAIL: user exit status`，退出码 1 |
| `disk-bad-trap.img` | 第一次 syscall 前尝试读取 `sstatus` | cause=2、`sepc=0x80400030`，`FAIL: unexpected scause`，退出码 1 |

内核不能把非零退出伪装成成功，也不能把一次非法指令误当作服务请求。宿主比较整个输出序列和状态，10 秒超时无论发生在哪种用例都算失败。逐次输出在 `build/lesson05/*.img.log`，完整回归用：

```sh
make test
script -q -e -c 'make test' build/pty.log
```

本次工作区和从两个课程标签分别取出的干净副本，都执行了构建、回归、检查与伪终端测试。

## 沿 GDB 看一次 write 和一次分配

按[第 04 篇的 GDB 启动命令](/posts/machine-supervisor-user-traps/#用-gdb-看实际-privilege而不只看文字)启动 QEMU，只把磁盘替换为 `build/lesson05/disk.img`。第二个终端运行 `gdb-multiarch build/lesson05/kernel.elf`：

```gdb
target remote :1234
add-symbol-file build/lesson05/user.elf
hbreak *0x8040001c
continue
info registers a7 a0 a1 sp
p/x $priv
hbreak supervisor_trap
continue
info registers scause sepc sstatus sscratch sp
p/x $priv
disable 1 2
hbreak mini_alloc
continue
p/x &__heap_start
p/x &__heap_end
p/x &__user_stack_top
```

本次实测 syscall 前 `priv=0, a7=1`；进入 handler 后 `priv=1, scause=8, sepc=0x8040001c, SPP=0`。分配器边界分别为 `0x80408000`、`0x8040c000` 和栈顶 `0x80410000`。先禁用前两个断点，是为了继续运行时不会被后续几十次 syscall 反复截住。

如果想看内核如何修改返回值，可以在 `trap_dispatch` 设置硬件断点，检查 `frame->x[10]` 与 `frame->epc`；它们会被汇编入口恢复成用户看到的 `a0` 和继续地址。不要把 trap frame 地址与其中保存的原用户 `sp` 混为一谈。

## 下一步：多个程序为什么不能只靠“多调用几次 main”

现在程序能够通过明确入口请求输出、分配自己的内存、报告失败并退出。这里的退出仍是整个实验结束：内核写入 QEMU finisher，不是进程槽回收、等待或重新运行另一任务。

下一课再引入定时器、上下文切换和进程生命周期，回答“一个程序不主动退出时，另一个程序怎样获得执行机会”。进度仍统一放在[系列总览](/series/)。

## 参考资料

- [RISC-V Supervisor-Level ISA：异常原因与特权返回](https://docs.riscv.org/reference/isa/v20260120/priv/supervisor.html)
- [RISC-V Machine-Level ISA：异常委托与 PMP](https://docs.riscv.org/reference/isa/v20260120/priv/machine.html)
- [RISC-V ELF psABI：函数参数、寄存器保存与栈对齐](https://github.com/riscv-non-isa/riscv-elf-psabi-doc/blob/master/riscv-cc.adoc)
- [Wikipedia：System call](https://en.wikipedia.org/wiki/System_call)
- [cppreference：memcpy](https://en.cppreference.com/w/c/string/byte/memcpy.html)
