# Stage-1 isolation regression: deliberately omits the real memory A/B.
# Add its simulation fixture explicitly; full production uses rtl_asic.f.
rtl/asic/asic_top.v
rtl/asic/btn_sync.v
rtl/asic/reset_ctrl.v
rtl/espino_core/espino_alu.v
rtl/espino_core/espino_controller.v
rtl/espino_core/espino_core.v
rtl/espino_core/espino_decoder.v
rtl/espino_core/espino_id_stage.v
rtl/espino_core/espino_if_stage.v
rtl/espino_core/espino_load_store_unit.v
rtl/espino_core/espino_register_file.v
rtl/pochoco_periph.v
rtl/pochoco_soc.v
rtl/pochoco_spi_slave.v
