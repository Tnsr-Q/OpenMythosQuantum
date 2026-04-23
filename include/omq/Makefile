CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Wpedantic \
            -I./include -I/usr/include/eigen3

BIN_DIR  := build
TEST_BIN := $(BIN_DIR)/phase_c_test

.PHONY: all test clean

all: $(TEST_BIN)

$(TEST_BIN): test/phase_c_test.cpp include/omq/*.hpp | $(BIN_DIR)
	$(CXX) $(CXXFLAGS) -o $@ test/phase_c_test.cpp

$(BIN_DIR):
	mkdir -p $@

test: $(TEST_BIN)
	./$(TEST_BIN)

clean:
	rm -rf $(BIN_DIR)
