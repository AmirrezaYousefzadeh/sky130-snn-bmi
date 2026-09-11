# RISC-V software baseline of the BMI SNN decoder for sky130_vex2_soc (reuses the skywater repo toolchain/crt0/linker)
SKY   := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../../skywater)
FW    := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
BUILD := $(FW)/build
TOOLCHAIN ?= $(SKY)/tools/riscv-none-elf-gcc/bin/riscv-none-elf
CC := $(TOOLCHAIN)-gcc
OBJDUMP := $(TOOLCHAIN)-objdump
SIZE := $(TOOLCHAIN)-size
ARCH := -march=rv32im_zicsr -mabi=ilp32
OPT ?= -O2
SRC ?= bmi_snn_sw.c
CFLAGS := $(ARCH) $(OPT) -g -ffreestanding -nostdlib -Wall -fno-builtin -fno-common -ffunction-sections -fdata-sections -I$(SKY)/firmware/common -I$(FW)
LDFLAGS := $(ARCH) -nostdlib -T$(SKY)/firmware/link.ld -Wl,--gc-sections -Wl,-Map=$(BUILD)/bmi_snn_sw.map
all: clean $(BUILD)/imem.hex
	$(SIZE) $(BUILD)/bmi_snn_sw.elf
$(BUILD):
	mkdir -p $(BUILD)
$(BUILD)/crt0.o: $(SKY)/firmware/crt0.S | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/bmi_snn_sw.o: $(FW)/$(SRC) $(FW)/bmi_weights.h | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@
$(BUILD)/bmi_snn_sw.elf: $(BUILD)/crt0.o $(BUILD)/bmi_snn_sw.o
	$(CC) $(LDFLAGS) $^ -o $@ -lgcc
	$(OBJDUMP) -d $@ > $(BUILD)/bmi_snn_sw.dis
$(BUILD)/imem.hex: $(BUILD)/bmi_snn_sw.elf
	python3 $(SKY)/firmware/scripts/elf2mem.py $< --imem $(BUILD)/imem.hex --dmem $(BUILD)/dmem.hex
clean:
	rm -rf $(BUILD)
