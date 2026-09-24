"""Launch a program as SYSTEM in the interactive session, without PsExec.

The fan driver only responds to a SYSTEM-level process (Administrator is not
enough). PsExec -s -i does this by duplicating the access token of an existing
SYSTEM process and starting the target with it; this module does the same with
the Win32 API directly, so no third-party binary has to be shipped.

The calling process must already be elevated to Administrator (the UAC step in
elevation.py) and hold SeDebugPrivilege, which an elevated process can enable.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)


def _bind() -> None:
    # Set restype/argtypes explicitly: ctypes defaults every function to
    # returning c_int, which silently truncates 64-bit HANDLEs. Called at
    # import, after the structs it references are defined.
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.WTSGetActiveConsoleSessionId.restype = wintypes.DWORD
    kernel32.WTSGetActiveConsoleSessionId.argtypes = []
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.ProcessIdToSessionId.restype = wintypes.BOOL
    kernel32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

    advapi32.OpenProcessToken.restype = wintypes.BOOL
    advapi32.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi32.LookupPrivilegeValueW.restype = wintypes.BOOL
    advapi32.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.POINTER(LUID)]
    advapi32.AdjustTokenPrivileges.restype = wintypes.BOOL
    advapi32.AdjustTokenPrivileges.argtypes = [
        wintypes.HANDLE,
        wintypes.BOOL,
        ctypes.POINTER(TOKEN_PRIVILEGES),
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
    ]
    advapi32.DuplicateTokenEx.restype = wintypes.BOOL
    advapi32.DuplicateTokenEx.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(SECURITY_ATTRIBUTES),
        ctypes.c_int,
        ctypes.c_int,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    # CreateProcessWithTokenW, not CreateProcessAsUserW: the latter needs
    # SeAssignPrimaryTokenPrivilege, which an elevated Administrator process
    # does not hold. CreateProcessWithTokenW needs only SeImpersonatePrivilege,
    # which Administrators do hold.
    advapi32.CreateProcessWithTokenW.restype = wintypes.BOOL
    advapi32.CreateProcessWithTokenW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPCWSTR,
        ctypes.POINTER(STARTUPINFOW),
        ctypes.POINTER(PROCESS_INFORMATION),
    ]

TOKEN_DUPLICATE = 0x0002
TOKEN_QUERY = 0x0008
TOKEN_ASSIGN_PRIMARY = 0x0001
TOKEN_ADJUST_PRIVILEGES = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
SE_PRIVILEGE_ENABLED = 0x00000002
SECURITY_IMPERSONATION = 2  # SecurityImpersonation level
TOKEN_PRIMARY = 1
CREATE_NEW_CONSOLE = 0x00000010
CREATE_UNICODE_ENVIRONMENT = 0x00000400
NORMAL_PRIORITY_CLASS = 0x00000020
MAXIMUM_ALLOWED = 0x02000000
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
TH32CS_SNAPPROCESS = 0x00000002
SE_DEBUG_NAME = "SeDebugPrivilege"


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(wintypes.BYTE)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class SystemLaunchError(Exception):
    """Raised when the process could not be started as SYSTEM."""


def _win_error(call: str) -> SystemLaunchError:
    code = ctypes.get_last_error()
    return SystemLaunchError(f"{call} failed (error {code}): {ctypes.FormatError(code)}")


def _enable_se_debug() -> None:
    hproc = kernel32.GetCurrentProcess()
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(hproc, TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)):
        raise _win_error("OpenProcessToken(current)")
    try:
        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
            raise _win_error("LookupPrivilegeValueW")
        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
        if not advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None):
            raise _win_error("AdjustTokenPrivileges")
        # AdjustTokenPrivileges can return success while not granting the
        # privilege (ERROR_NOT_ALL_ASSIGNED); the caller isn't elevated then.
        if ctypes.get_last_error() != 0:
            raise _win_error("AdjustTokenPrivileges(not all assigned)")
    finally:
        kernel32.CloseHandle(token)


def _find_system_process_pid() -> int:
    """PID of winlogon.exe in the active console session (a SYSTEM process
    already living in the interactive session, so its token has the right
    session id for a process the logged-on user can see)."""
    session_id = kernel32.WTSGetActiveConsoleSessionId()
    if session_id == 0xFFFFFFFF:
        raise SystemLaunchError("No active console session")

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise _win_error("CreateToolhelp32Snapshot")
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            raise _win_error("Process32FirstW")
        while True:
            if entry.szExeFile.lower() == "winlogon.exe":
                proc_session = wintypes.DWORD()
                if kernel32.ProcessIdToSessionId(entry.th32ProcessID, ctypes.byref(proc_session)):
                    if proc_session.value == session_id:
                        return entry.th32ProcessID
            if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snapshot)
    raise SystemLaunchError("winlogon.exe not found in the active session")


def launch_as_system(command_line: str) -> None:
    """Start `command_line` as SYSTEM on the interactive desktop.

    Raises SystemLaunchError on any failure. The caller must be an elevated
    Administrator; otherwise enabling SeDebugPrivilege fails.
    """
    _enable_se_debug()
    pid = _find_system_process_pid()

    hproc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if not hproc:
        raise _win_error("OpenProcess(winlogon)")
    dup_token = wintypes.HANDLE()
    try:
        src_token = wintypes.HANDLE()
        # Only TOKEN_DUPLICATE on the source: the source token's DACL denies
        # the broader rights even with SeDebugPrivilege. MAXIMUM_ALLOWED on
        # the duplicate then grants every right the caller may hold, which is
        # what CreateProcessAsUser needs.
        if not advapi32.OpenProcessToken(hproc, TOKEN_DUPLICATE, ctypes.byref(src_token)):
            raise _win_error("OpenProcessToken(winlogon)")
        try:
            sa = SECURITY_ATTRIBUTES()
            sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
            if not advapi32.DuplicateTokenEx(
                src_token,
                MAXIMUM_ALLOWED,
                ctypes.byref(sa),
                SECURITY_IMPERSONATION,
                TOKEN_PRIMARY,
                ctypes.byref(dup_token),
            ):
                raise _win_error("DuplicateTokenEx")
        finally:
            kernel32.CloseHandle(src_token)

        startup = STARTUPINFOW()
        startup.cb = ctypes.sizeof(STARTUPINFOW)
        startup.lpDesktop = "winsta0\\default"  # the interactive desktop
        info = PROCESS_INFORMATION()
        cmd_buffer = ctypes.create_unicode_buffer(command_line)
        if not advapi32.CreateProcessWithTokenW(
            dup_token,
            0,
            None,
            cmd_buffer,
            CREATE_UNICODE_ENVIRONMENT | NORMAL_PRIORITY_CLASS,
            None,
            None,
            ctypes.byref(startup),
            ctypes.byref(info),
        ):
            raise _win_error("CreateProcessWithTokenW")
        kernel32.CloseHandle(info.hProcess)
        kernel32.CloseHandle(info.hThread)
    finally:
        if dup_token:
            kernel32.CloseHandle(dup_token)
        kernel32.CloseHandle(hproc)


_bind()
