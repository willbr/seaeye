.globl      _start
.align 4

_start:
    // Write "Hello, World!\n" to stdout
    mov     x0, #1                // File descriptor 1 (stdout)
    adr     x1, msg               // Pointer to the message
    mov     x2, len               // Message length
    mov    x16, #4
    svc     #0x80                      // Make system call

    // Exit the program
    mov     x0, #2                // Status 0
    mov    x16, #1
    svc     0                      // Make system call

msg:
    .string "Hello, World!\n"
len = . - msg
