# linumeRT - natywne przyspieszenia rdzenia i symulacji (C11, bez zaleznosci poza libc/libm).
# Model-Author: Claude · 2026-11-05
#
#   make shared   - buduje build/liblinumert_native.so (wiazanie ctypes: core/linumert/native.py)
#   make test     - testy C (build/test_native)
#   make test-san - te same testy z ASan/UBSan w build-san (bez losowania adresow, gdy mozna)
#   make clean
#
# -ffp-contract=off: bez fuzji mnozenia z dodawaniem (FMA), zeby kolejnosc i zaokraglenia byly
# takie jak w numpy (sciezka referencyjna w Pythonie).
CC ?= cc
CFLAGS ?= -O2
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic -Werror -ffp-contract=off
LDLIBS += -lm
CFLAGS += $(SAN)
LDLIBS += $(SAN)

BUILD := build
SRC := relief.c zmap.c
OBJ := $(SRC:%.c=$(BUILD)/%.o)
PIC_OBJ := $(SRC:%.c=$(BUILD)/pic/%.o)

.PHONY: all shared test test-san clean

all: shared

shared: $(BUILD)/liblinumert_native.so

$(BUILD) $(BUILD)/pic:
	mkdir -p $@

$(BUILD)/%.o: %.c lrt_native.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/pic/%.o: %.c lrt_native.h | $(BUILD)/pic
	$(CC) $(CFLAGS) -fPIC -c $< -o $@

$(BUILD)/liblinumert_native.a: $(OBJ)
	$(AR) rcs $@ $^

$(BUILD)/liblinumert_native.so: $(PIC_OBJ)
	$(CC) -shared $^ $(LDLIBS) -o $@

$(BUILD)/test_native: tests/test_native.c lrt_native.h ../../plant/core/tests/lrt_test.h \
		$(BUILD)/liblinumert_native.a
	$(CC) $(CFLAGS) -I. -I../../plant/core/tests tests/test_native.c \
		$(BUILD)/liblinumert_native.a $(LDLIBS) -o $@

test: $(BUILD)/test_native
	$(RUN) ./$(BUILD)/test_native

# ASan z GCC 12 na jadrach z wysokim vm.mmap_rnd_bits (np. WSL 6.x) potrafi zapetlic sie przy
# starcie na "AddressSanitizer:DEADLYSIGNAL" (ok. 1/3 uruchomien w WSL linumeRT-Debian12,
# 2026-11-05). Bez losowania adresow (setarch -R) blad nie wystepuje; gdy setarch nie dziala,
# test uruchamia sie zwyczajnie.
SAN_RUN = $(shell setarch $$(uname -m) -R true >/dev/null 2>&1 && echo "setarch $$(uname -m) -R")

test-san:
	$(MAKE) BUILD=build-san RUN="$(SAN_RUN)" SAN="-g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer" test

clean:
	rm -rf $(BUILD) build-san
