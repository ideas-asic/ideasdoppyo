
from memmap_nm2 import MMRST

MM_CONF = MMRST.copy()

MM_CONF.fields["seq_halt"].set_value(1)
MM_CONF.fields["seq_reset"].set_value(0)
MM_CONF.fields["sys_clk_enable"].set_value(1)
MM_CONF.fields["pll_enable"].set_value(1)
MM_CONF.fields["sysclk_dly"].set_value(2)
MM_CONF.fields["clk_div_mode"].set_value(2)

print(MM_CONF.register)

for regaddr, reg in MMRST.copy().registers.items():
    if reg.value != MM_CONF.registers[regaddr].value:
        print(regaddr, MM_CONF.registers[regaddr].value)
