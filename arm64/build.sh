as -arch arm64 -g -o hello.o hello.s
ld -o hello hello.o -lSystem -syslibroot `xcrun -sdk macosx --show-sdk-path` -e _start -arch arm64


