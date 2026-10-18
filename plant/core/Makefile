# linumeRT - Plant, rdzen dynamiki (C11, bez zaleznosci poza libc/libm).
# Model-Author: Claude
#
#   make        - buduje build/libplant_core.a
#   make test   - buduje i uruchamia testy (build/test_axis)
#   make clean
CC ?= cc
CFLAGS ?= -O2
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic -Werror
LDLIBS += -lm

BUILD := build
SRC := axis.c
OBJ := $(SRC:%.c=$(BUILD)/%.o)
TESTS := $(BUILD)/test_axis

.PHONY: all test clean

all: $(BUILD)/libplant_core.a

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: %.c axis.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/libplant_core.a: $(OBJ)
	$(AR) rcs $@ $^

$(BUILD)/test_axis: tests/test_axis.c tests/lrt_test.h $(BUILD)/libplant_core.a
	$(CC) $(CFLAGS) tests/test_axis.c $(BUILD)/libplant_core.a $(LDLIBS) -o $@

test: $(TESTS)
	@set -e; for t in $(TESTS); do ./$$t; done

clean:
	rm -rf $(BUILD)
