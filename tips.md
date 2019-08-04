**问题**

```bash
cc -bundle -undefined dynamic_lookup -Wl,-F. build/temp.macosx-10.14-intel-2.7/_mysql.o -L/usr/local/Cellar/mysql-connector-c/6.1.11/lib -lmysqlclient -lssl -lcrypto -o build/lib.macosx-10.14-intel-2.7/_mysql.so
ld: library not found for -lssl
clang: error: linker command failed with exit code 1 (use -v to see invocation)
error: command 'cc' failed with exit status 1
```

解决方式:
```
brew info openssl
export LDFLAGS="-L/usr/local/opt/openssl/lib"
export CPPFLAGS="-I/usr/local/opt/openssl/include"
```