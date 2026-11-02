# linumeRT - Plant, rdzen dynamiki (C11, bez zaleznosci poza libc/libm).
# Model-Author: Claude
#
#   make        - buduje build/libplant_core.a
#   make test   - buduje i uruchamia testy (build/test_axis, build/test_drive)
#   make tools  - buduje build/lrt_check_params (walidacja szablonow napedow)
#   make shared - buduje build/libplant_core.so (wiazanie ctypes, sesja 014)
#   make test-san - testy z ASan/UBSan w osobnym katalogu build-san (wymaga libasan/libubsan)
#   make clean
CC ?= cc
CFLAGS ?= -O2
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic -Werror
LDLIBS += -lm
CFLAGS += $(SAN)
LDLIBS += $(SAN)

BUILD := build
SRC := live.c axis.c drive.c machine.c
OBJ := $(SRC:%.c=$(BUILD)/%.o)
PIC_OBJ := $(SRC:%.c=$(BUILD)/pic/%.o)
TESTS := $(BUILD)/test_axis $(BUILD)/test_drive $(BUILD)/test_machine
TOOLS := $(BUILD)/lrt_check_params

.PHONY: all test test-san tools shared clean

all: $(BUILD)/libplant_core.a

# Narzedzie do sprawdzania szablonow napedow walidatorami C (uzywa stdio, poza rdzeniem RT).
tools: $(TOOLS)

$(BUILD)/lrt_check_params: tools/check_params.c live.h axis.h drive.h $(BUILD)/libplant_core.a
	$(CC) $(CFLAGS) tools/check_params.c $(BUILD)/libplant_core.a $(LDLIBS) -o $@

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: %.c live.h axis.h drive.h machine.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/libplant_core.a: $(OBJ)
	$(AR) rcs $@ $^

# Biblioteka wspoldzielona dla wiazania ctypes (plant/server/linumert_plant/core_binding.py).
shared: $(BUILD)/libplant_core.so

$(BUILD)/pic:
	mkdir -p $(BUILD)/pic

$(BUILD)/pic/%.o: %.c live.h axis.h drive.h machine.h | $(BUILD)/pic
	$(CC) $(CFLAGS) -fPIC -c $< -o $@

$(BUILD)/libplant_core.so: $(PIC_OBJ)
	$(CC) -shared $^ $(LDLIBS) -o $@

$(BUILD)/test_axis: tests/test_axis.c tests/lrt_test.h live.h axis.h $(BUILD)/libplant_core.a
	$(CC) $(CFLAGS) tests/test_axis.c $(BUILD)/libplant_core.a $(LDLIBS) -o $@

$(BUILD)/test_drive: tests/test_drive.c tests/lrt_test.h live.h axis.h drive.h $(BUILD)/libplant_core.a
	$(CC) $(CFLAGS) tests/test_drive.c $(BUILD)/libplant_core.a $(LDLIBS) -o $@

$(BUILD)/test_machine: tests/test_machine.c tests/lrt_test.h live.h axis.h drive.h machine.h $(BUILD)/libplant_core.a
	$(CC) $(CFLAGS) tests/test_machine.c $(BUILD)/libplant_core.a $(LDLIBS) -o $@

test: $(TESTS)
	@set -e; for t in $(TESTS); do ./$$t; done

# Te same testy z sanitizerami; osobny katalog, by nie mieszac obiektow z build/.
test-san:
	$(MAKE) BUILD=build-san SAN="-g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer" test

clean:
	rm -rf $(BUILD) build-san
