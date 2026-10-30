"""PID 1 контейнера: независимый wall-clock даже при аварии HTTP-брокера.

Недоверенный код работает дочерним процессом. При выходе namespace init ядро
убивает всех потомков, в том числе создавших собственную process group.
"""
import os
import ctypes
import subprocess


def main():
    # Запрещаем дочернему процессу читать/менять память таймера через /proc/1/mem
    # даже на хостах без Yama ptrace_scope. CAP_SYS_PTRACE у задачи отсутствует.
    if ctypes.CDLL(None, use_errno=True).prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_DUMPABLE
        os._exit(126)
    process = subprocess.Popen(['python', '-m', 'sandbox.worker'], start_new_session=True)
    try:
        status = process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        status = 124
    except BaseException:
        status = 125
    # Завершение PID 1 уничтожает весь PID namespace; пользовательский cleanup не запускается.
    os._exit(status if status >= 0 else 128 - status)


if __name__ == '__main__':
    main()
