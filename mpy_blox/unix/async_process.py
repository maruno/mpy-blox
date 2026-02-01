# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import ffi
import select
import struct
import uctypes
from asyncio import sleep_ms

# Open libc
libc = ffi.open("libc.so.6")

# Load FFI C functions
# int posix_spawnp(pid_t *restrict pid, const char *restrict path, const posix_spawn_file_actions_t *restrict file_actions, const posix_spawnattr_t *restrict attrp, char *const argv[restrict], char *const envp[restrict]);
posix_spawnp = libc.func("i", "posix_spawnp", "pppppp")
# int posix_spawn_file_actions_init(posix_spawn_file_actions_t *file_actions); 
posix_spawn_file_actions_init = libc.func("i", "posix_spawn_file_actions_init", "p")
# int posix_spawn_file_actions_destroy(posix_spawn_file_actions_t *file_actions);
posix_spawn_file_actions_destroy = libc.func("i", "posix_spawn_file_actions_destroy", "p")
# int posix_spawn_file_actions_adddup2(posix_spawn_file_actions_t *file_actions, int fildes, int newfildes);
posix_spawn_file_actions_adddup2 = libc.func("i", "posix_spawn_file_actions_adddup2", "pii")
# int posix_spawn_file_actions_addclose(posix_spawn_file_actions_t *file_actions, int fildes);
posix_spawn_file_actions_addclose = libc.func("i", "posix_spawn_file_actions_addclose", "pi")
# int pipe(int fildes[2]);
pipe = libc.func("i", "pipe", "p")
# int close(int fildes);
close = libc.func("i", "close", "i")
# pid_t wait(int *stat_loc);
waitpid = libc.func("i", "waitpid", "ipi")
# ssize_t read(int fd, void buf[.count], size_t count)
read = libc.func("i", "read", "ipi")


def _build_argv(program: str, *args: str) -> tuple[bytearray, list[bytes]]:
    """Builds char** argv array for FFI.

       Beware: keep both return values alive!
    """
    # Encode all arguments as null-terminated C strings
    args_array = [program.encode('utf-8') + b'\0']
    args_array.extend(arg.encode('utf-8') + b'\0' for arg in args)

    # Create array of pointers (NULL-terminated)
    ptr_size = struct.calcsize('P')
    argv = bytearray((len(args_array) + 1) * ptr_size)
    for i, s in enumerate(args_array):
        ptr = uctypes.addressof(s)
        struct.pack_into('P', argv, i * ptr_size, ptr)

    return argv, args_array


class AsyncFDStream:
    mode_mask = 0
    def __init__(self, fd: int, check_ms = 10):
        self.fd = fd
        self.check_ms = check_ms

        self.poller = poller = select.poll() 
        poller.register(self.fd, self.mode_mask)

    async def wait(self):
        poll = self.poller.poll
        check_ms = self.check_ms
        while poll(0):
            await sleep_ms(check_ms)

class AsyncFDStreamReader(AsyncFDStream):
    mode_mask = select.POLLIN

    async def read(self, size=8192):
        await self.wait()
        buf = bytearray(size)
        n = read(self.fd, buf, size)

        if n <= 0:
            return b''

        return bytes(buf[:n])

    def close(self):
        close(self.fd)

class AsyncProcess:
    def __init__(self, program: str, *args: str) -> None:
        self.exit_code: int | None = None

        file_actions: bytearray | None = None
        try:
            # Create pipes for communication
            pipe_fds = bytearray(8) # int[2]
            file_actions = bytearray(80)  # posix_spawn_file_actions_t
            posix_spawn_file_actions_init(file_actions)

            # stdout
            if pipe(pipe_fds) == -1:
                raise OSError("pipe failed (stdout)")
            stdout_read_pipe, stdout_write_pipe = struct.unpack('ii', pipe_fds)
            posix_spawn_file_actions_adddup2(file_actions, stdout_write_pipe, 1)
            posix_spawn_file_actions_addclose(file_actions, stdout_read_pipe)
            posix_spawn_file_actions_addclose(file_actions, stdout_write_pipe)

            # stderr
            if pipe(pipe_fds) == -1:
                raise OSError("pipe failed (stderr)")
            stderr_read_pipe, stderr_write_pipe = struct.unpack('ii', pipe_fds)
            posix_spawn_file_actions_adddup2(file_actions, stderr_write_pipe, 2)
            posix_spawn_file_actions_addclose(file_actions, stderr_read_pipe)
            posix_spawn_file_actions_addclose(file_actions, stderr_write_pipe)

            self.argv, self.args = _build_argv(program, *args)

            # Register streams
            self.stdout = AsyncFDStreamReader(stdout_read_pipe)
            self.stderr = AsyncFDStreamReader(stderr_read_pipe)

            # Spawn process
            pid_buf = bytearray(4)
            result = posix_spawnp(
                pid_buf,  # pid output
                self.args[0],  # path to executable
                file_actions,  # file actions
                0,  # spawn attributes (NULL)
                self.argv,  # argv array
                0  # envp (NULL = inherit)
            )
            if result != 0:
                raise OSError(f"posix_spawn failed: {result}")

            self.pid = struct.unpack('i', pid_buf)[0]
        finally:
            if file_actions:
                posix_spawn_file_actions_destroy(file_actions)

        # Only keep read ends of stdout/stderr
        close(stdout_write_pipe)
        close(stderr_write_pipe)

    def close(self):
        if self.exit_code:
            return None

        self.stdout.close()
        self.stderr.close()

        status = bytearray(4)
        waitpid(self.pid, status, 0)

        exit_code = struct.unpack('i', status)[0]
        self.exit_code = exit_code

        return (exit_code >> 8) & 0xFF

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        if not self.exit_code:
            self.close()
